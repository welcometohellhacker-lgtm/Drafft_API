from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.clip import ClipCandidate
from app.models.enums import JobStatus, RenderStatus
from app.models.job import Job
from app.models.render import Render
from app.models.transcript import TranscriptSegment, TranscriptWord
from app.services.caption_plan_service import CaptionPlanService
from app.services.media_probe_service import MediaProbeService
from app.services.render_service import RenderService
from app.services.subtitle_service import SubtitleService
from app.services.transcript_intelligence_service import TranscriptIntelligenceService
from app.services.transcription_service import TranscriptionService
from app.services.visual_plan_service import VisualPlanService


class JobOrchestratorService:
    def __init__(self, db: Session):
        self.db = db
        self.caption_plan_service = CaptionPlanService()
        self.media_probe_service = MediaProbeService()
        self.transcription_service = TranscriptionService()
        self.transcript_intelligence_service = TranscriptIntelligenceService()
        self.visual_plan_service = VisualPlanService()
        self.render_service = RenderService()
        self.subtitle_service = SubtitleService()

    def process(self, job: Job, render_selected_immediately: bool = False, regenerate_transcript: bool = False) -> Job:
        job.status = JobStatus.preprocessing.value
        job.current_step = "preprocess_media"
        job.progress_percent = 10
        self.db.commit()

        if not job.input_video_url:
            job.status = JobStatus.failed.value
            job.current_step = "preprocess_media"
            job.failure_reason = "input video must be uploaded before processing"
            self.db.commit()
            self.db.refresh(job)
            return job

        probe = self.media_probe_service.probe(job.input_video_url)
        job.duration_seconds = int(probe["duration_seconds"])
        job.fps = int(probe["fps"])
        job.width = int(probe["width"])
        job.height = int(probe["height"])

        job.status = JobStatus.transcribing.value
        job.current_step = "transcribe"
        job.progress_percent = 30
        self.db.commit()

        existing_segments = self.db.query(TranscriptSegment).filter(TranscriptSegment.job_id == job.id).all()
        if regenerate_transcript and existing_segments:
            for segment in existing_segments:
                for word in list(segment.words):
                    self.db.delete(word)
                self.db.delete(segment)
            self.db.commit()
            existing_segments = []

        self.db.query(Asset).filter(
            Asset.job_id == job.id,
            Asset.asset_type.in_(["transcript_json", "subtitle_srt", "subtitle_vtt"]),
        ).delete(synchronize_session=False)
        self.db.commit()

        if existing_segments:
            transcript = [
                {
                    "speaker": segment.speaker,
                    "start_time": segment.start_time,
                    "end_time": segment.end_time,
                    "text": segment.text,
                    "confidence": segment.confidence,
                    "words": [],
                }
                for segment in existing_segments
            ]
        else:
            transcript = self.transcription_service.transcribe(job)
            for segment_payload in transcript:
                segment = TranscriptSegment(
                    job_id=job.id,
                    speaker=segment_payload.get("speaker"),
                    start_time=segment_payload["start_time"],
                    end_time=segment_payload["end_time"],
                    text=segment_payload["text"],
                    confidence=segment_payload.get("confidence"),
                )
                self.db.add(segment)
                self.db.flush()
                for word in segment_payload.get("words", []):
                    self.db.add(
                        TranscriptWord(
                            segment_id=segment.id,
                            word=word["word"],
                            start_time=word["start_time"],
                            end_time=word["end_time"],
                            confidence=word.get("confidence"),
                        )
                    )
            self.db.commit()

        subtitle_assets = self.subtitle_service.build_assets(job, transcript)
        self.db.add(
            Asset(
                job_id=job.id,
                clip_id=None,
                asset_type="transcript_json",
                provider="mock_transcription_provider",
                prompt=None,
                url=f"transcript://{job.id}",
                metadata_json={"segments": transcript},
            )
        )
        self.db.add(
            Asset(
                job_id=job.id,
                clip_id=None,
                asset_type="subtitle_srt",
                provider="subtitle_service",
                prompt=None,
                url=f"subtitle://{job.id}.srt",
                metadata_json={"content": subtitle_assets["srt"]},
            )
        )
        self.db.add(
            Asset(
                job_id=job.id,
                clip_id=None,
                asset_type="subtitle_vtt",
                provider="subtitle_service",
                prompt=None,
                url=f"subtitle://{job.id}.vtt",
                metadata_json={"content": subtitle_assets["vtt"]},
            )
        )
        self.db.commit()

        job.status = JobStatus.analyzing.value
        job.current_step = "analyze_transcript"
        job.progress_percent = 55
        self.db.commit()

        self.db.query(Asset).filter(Asset.job_id == job.id, Asset.asset_type.in_(["visual_plan", "caption_plan", "clip_candidate_json", "rendered_clip", "thumbnail"])).delete(synchronize_session=False)
        self.db.query(Render).filter(Render.job_id == job.id).delete(synchronize_session=False)
        self.db.query(ClipCandidate).filter(ClipCandidate.job_id == job.id).delete(synchronize_session=False)
        self.db.commit()

        selected_clip_ids = {
            clip.id for clip in self.db.query(ClipCandidate).filter(ClipCandidate.job_id == job.id, ClipCandidate.selected.is_(True)).all()
        }
        candidates = self.transcript_intelligence_service.generate_candidates(job, transcript)
        created_clips: list[ClipCandidate] = []
        for candidate_payload in candidates:
            clip = ClipCandidate(job_id=job.id, **candidate_payload)
            clip.selected = render_selected_immediately or bool(selected_clip_ids)
            self.db.add(clip)
            self.db.flush()
            created_clips.append(clip)
            caption_groups = self.caption_plan_service.build_caption_groups(transcript, clip.caption_style)
            visual_plan = self.visual_plan_service.build(
                clip_id=clip.id,
                aspect_ratio=(job.requested_platforms_json[0] if job.requested_platforms_json else "9:16"),
                style=clip.caption_style,
                broll_prompts=clip.broll_prompts_json,
            )
            self.db.add(Asset(job_id=job.id, clip_id=clip.id, asset_type="caption_plan", provider="caption_plan_service", prompt=None, url=f"caption-plan://{clip.id}", metadata_json={"groups": caption_groups, "style": clip.caption_style}))
            self.db.add(Asset(job_id=job.id, clip_id=clip.id, asset_type="visual_plan", provider="internal", prompt=None, url=f"visual-plan://{clip.id}", metadata_json=visual_plan))
            self.db.add(Asset(job_id=job.id, clip_id=clip.id, asset_type="clip_candidate_json", provider="transcript_intelligence_service", prompt=None, url=f"clip-candidate://{clip.id}", metadata_json=candidate_payload))
        self.db.commit()

        should_render = render_selected_immediately
        if should_render:
            job.status = JobStatus.rendering.value
            job.current_step = "rendering"
            job.progress_percent = 80
            self.db.commit()
            for clip in created_clips:
                render_meta = self.render_service.create_render_metadata(clip.id, job.requested_platforms_json[0] if job.requested_platforms_json else "9:16")
                render_output = self.render_service.build_render_output(
                    job.id,
                    clip.id,
                    job.requested_platforms_json[0] if job.requested_platforms_json else "9:16",
                    clip.caption_style,
                )
                self.db.add(
                    Render(
                        job_id=job.id,
                        clip_id=clip.id,
                        output_format=job.requested_platforms_json[0] if job.requested_platforms_json else "9:16",
                        output_url=render_output["output_url"],
                        subtitle_url=render_output["subtitle_url"],
                        thumbnail_url=render_output["thumbnail_url"],
                        metadata_json={**render_meta, **render_output["metadata_json"]},
                        status=RenderStatus.completed.value,
                    )
                )
                self.db.add(Asset(job_id=job.id, clip_id=clip.id, asset_type="rendered_clip", provider="render_service", prompt=None, url=render_output["output_url"], metadata_json=render_output["metadata_json"]))
                self.db.add(Asset(job_id=job.id, clip_id=clip.id, asset_type="thumbnail", provider="render_service", prompt=None, url=render_output["thumbnail_url"], metadata_json={"clip_id": clip.id}))
            self.db.commit()

        job.status = JobStatus.completed.value
        job.current_step = "completed"
        job.progress_percent = 100
        self.db.commit()
        self.db.refresh(job)
        return job
