import json
import logging
import time
from pathlib import Path

from app.db.firebase import FirestoreSession
from app.models.asset import Asset
from app.models.clip import ClipCandidate
from app.models.enums import JobStatus, RenderStatus
from app.models.job import Job
from app.models.render import Render
from app.models.transcript import TranscriptSegment, TranscriptWord
from app.services.audio_mix_service import AudioMixService
from app.services.background_music_service import BackgroundMusicService
from app.services.branding_service import BrandingService
from app.services.broll_service import BrollService
from app.services.caption_plan_service import CaptionPlanService
from app.services.elevenlabs_service import ElevenLabsService
from app.services.image_generation_service import ImageGenerationService
from app.services.media_probe_service import MediaProbeService
from app.services.narration_service import NarrationService
from app.services.output_enrichment_service import OutputEnrichmentService
from app.services.render_service import RenderService
from app.services.subtitle_service import SubtitleService
from app.services.transcript_intelligence_service import TranscriptIntelligenceService
from app.services.transcription_service import TranscriptionService
from app.services.video_preprocessing_service import VideoPreprocessingService
from app.services.visual_plan_service import VisualPlanService
from app.services.webhook_delivery_service import WebhookDeliveryService

logger = logging.getLogger(__name__)


def _platform(job) -> str:
    raw = job.requested_platforms_json[0] if job.requested_platforms_json else "9:16"
    if isinstance(raw, str) and raw.startswith("["):
        try:
            parsed = json.loads(raw)
            return parsed[0] if isinstance(parsed, list) and parsed else raw
        except (json.JSONDecodeError, IndexError):
            pass
    return raw


class JobOrchestratorService:
    def __init__(self, db: FirestoreSession) -> None:
        self.db = db
        self.audio_mix_service = AudioMixService()
        self.branding_service = BrandingService()
        self.broll_service = BrollService()
        self.elevenlabs_service = ElevenLabsService()
        self.caption_plan_service = CaptionPlanService()
        self.image_generation_service = ImageGenerationService()
        self.output_enrichment_service = OutputEnrichmentService()
        self.narration_service = NarrationService()
        self.webhook_delivery_service = WebhookDeliveryService()
        self.media_probe_service = MediaProbeService()
        self.transcription_service = TranscriptionService()
        self.transcript_intelligence_service = TranscriptIntelligenceService()
        self.visual_plan_service = VisualPlanService()
        self.render_service = RenderService()
        self.subtitle_service = SubtitleService()
        self.video_preprocessing_service = VideoPreprocessingService()
        self.background_music_service = BackgroundMusicService()
        self.storage_service = self.video_preprocessing_service.storage

    def process(self, job: Job, render_selected_immediately: bool = False, regenerate_transcript: bool = False) -> Job:
        _t0 = time.time()
        logger.info("[job=%s] ── process() START ─────────────────────────────", job.id)
        logger.info("[job=%s] input_video_url=%s", job.id, job.input_video_url)
        logger.info("[job=%s] storage base path: %s", job.id, self.storage_service.base_path)

        job.status = JobStatus.preprocessing.value
        job.current_step = "preprocess_media"
        job.progress_percent = 10
        self.db.add(job)
        self.db.commit()

        if not job.input_video_url:
            logger.error("[job=%s] No input_video_url — aborting", job.id)
            job.status = JobStatus.failed.value
            job.current_step = "preprocess_media"
            job.failure_reason = "input video must be uploaded before processing"
            self.db.add(job)
            self.db.commit()
            return job

        logger.info("[job=%s] STEP 1/7  probing media …", job.id)
        _t = time.time()
        probe = self.media_probe_service.probe(job.input_video_url)
        logger.info("[job=%s] probe done in %.1fs → %dx%d %.1fs@%dfps landscape=%s",
                    job.id, time.time() - _t,
                    probe["width"], probe["height"],
                    probe["duration_seconds"], probe["fps"],
                    probe.get("is_landscape", False))
        job.duration_seconds = int(probe["duration_seconds"])
        job.fps = int(probe["fps"])
        job.width = int(probe["width"])
        job.height = int(probe["height"])

        is_landscape = probe.get("is_landscape", False)

        if is_landscape:
            logger.info("[job=%s] STEP 2/7  converting landscape→vertical (ffmpeg blur-bg) …", job.id)
            _t = time.time()
            job.current_step = "preprocessing_video"
            self.db.add(job)
            self.db.commit()
            processed_path = self.video_preprocessing_service.make_vertical(job.input_video_url, job.id)
            if processed_path:
                logger.info("[job=%s] make_vertical done in %.1fs → %s", job.id, time.time() - _t, processed_path)
                self.db.add(Asset(
                    job_id=job.id, clip_id=None,
                    asset_type="processed_video",
                    provider="video_preprocessing_service",
                    prompt=None,
                    url=self.video_preprocessing_service.storage.public_url_for(Path(processed_path)),
                    metadata_json={"is_landscape": True, "source": job.input_video_url},
                ))
                self.db.commit()
            else:
                logger.warning("[job=%s] make_vertical returned None — will use original", job.id)
        else:
            logger.info("[job=%s] STEP 2/7  skipped (video is already portrait)", job.id)

        logger.info("[job=%s] STEP 3/7  transcribing audio (Whisper) …", job.id)
        _t = time.time()
        job.status = JobStatus.transcribing.value
        job.current_step = "transcribe"
        job.progress_percent = 30
        self.db.add(job)
        self.db.commit()

        existing_segments = self.db.query_by_job_id(TranscriptSegment, job.id)
        if regenerate_transcript and existing_segments:
            self.db.delete_transcript_for_job(job.id)
            existing_segments = []

        self.db.delete_by_job_id(Asset, job.id, asset_types=[
            "transcript_json", "subtitle_srt", "subtitle_vtt",
            "isolated_voice", "narration_audio", "narration_script",
        ])

        if existing_segments:
            logger.info("[job=%s] reusing %d cached transcript segments", job.id, len(existing_segments))
            transcript = [
                {
                    "speaker": s.speaker,
                    "start_time": s.start_time,
                    "end_time": s.end_time,
                    "text": s.text,
                    "confidence": s.confidence,
                    "words": [],
                }
                for s in existing_segments
            ]
        else:
            logger.info("[job=%s] running Whisper transcription (this can take 1-5 min for long videos) …", job.id)
            transcript = self.transcription_service.transcribe(job)
            logger.info("[job=%s] transcription done in %.1fs → %d segments", job.id, time.time() - _t, len(transcript))
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
                self.db.flush()  # ensures segment.id is persisted before words reference it
                for word in segment_payload.get("words", []):
                    self.db.add(TranscriptWord(
                        segment_id=segment.id,
                        word=word["word"],
                        start_time=word["start_time"],
                        end_time=word["end_time"],
                        confidence=word.get("confidence"),
                    ))
            self.db.commit()

        subtitle_assets = self.subtitle_service.build_assets(job, transcript)
        isolated_voice = self.elevenlabs_service.isolate_voice(
            job.id, job.input_audio_url or job.input_video_url, job.narration_enabled
        )
        self.db.add(Asset(
            job_id=job.id, clip_id=None,
            asset_type="transcript_json",
            provider="mock_transcription_provider",
            prompt=None,
            url=f"transcript://{job.id}",
            metadata_json={"segments": transcript},
        ))
        srt_path = self.render_service.storage.write_text_asset(
            self.render_service.storage.subtitles_dir(job.id) / "job.srt", subtitle_assets["srt"]
        )
        vtt_path = self.render_service.storage.write_text_asset(
            self.render_service.storage.subtitles_dir(job.id) / "job.vtt", subtitle_assets["vtt"]
        )
        self.db.add(Asset(
            job_id=job.id, clip_id=None,
            asset_type="subtitle_srt",
            provider="subtitle_service",
            prompt=None,
            url=self.render_service.storage.public_url_for(Path(srt_path)),
            metadata_json={"content": subtitle_assets["srt"]},
        ))
        self.db.add(Asset(
            job_id=job.id, clip_id=None,
            asset_type="subtitle_vtt",
            provider="subtitle_service",
            prompt=None,
            url=self.render_service.storage.public_url_for(Path(vtt_path)),
            metadata_json={"content": subtitle_assets["vtt"]},
        ))
        if isolated_voice:
            self.db.add(Asset(job_id=job.id, clip_id=None, **isolated_voice))
        self.db.commit()

        logger.info("[job=%s] STEP 4/7  building subtitle assets …", job.id)
        job.status = JobStatus.analyzing.value
        job.current_step = "analyze_transcript"
        job.progress_percent = 55
        self.db.add(job)
        self.db.commit()

        # Clear any stale plan assets / renders / clips from a previous run
        self.db.delete_by_job_id(Asset, job.id, asset_types=[
            "visual_plan", "caption_plan", "clip_candidate_json", "broll_plan",
            "audio_mix_plan", "branding_profile", "generated_image",
            "rendered_clip", "thumbnail", "social_caption", "webhook_event",
        ])
        self.db.delete_by_job_id(Render, job.id)
        self.db.delete_by_job_id(ClipCandidate, job.id)

        logger.info("[job=%s] STEP 5/7  extracting highlight B-roll clips (ffmpeg) …", job.id)
        _t = time.time()
        _emphasis = {"mistake", "wrong", "before", "biggest", "secret", "never", "strongest", "best", "worst", "avoid"}
        highlight_segs = [s for s in transcript if any(w in s.get("text", "").lower() for w in _emphasis)]
        if len(highlight_segs) < 2:
            highlight_segs = transcript[:min(5, len(transcript))]
        logger.info("[job=%s] extracting highlights from %d segments …", job.id, len(highlight_segs))
        highlight_assets = self.video_preprocessing_service.extract_highlights(
            job.input_video_url, job.id, is_landscape, highlight_segs
        )
        logger.info("[job=%s] highlight extraction done in %.1fs → %d clips", job.id, time.time() - _t, len(highlight_assets))
        for ha in highlight_assets:
            self.db.add(Asset(
                job_id=job.id, clip_id=None,
                asset_type="highlight_clip",
                provider="video_preprocessing_service",
                prompt=None,
                url=ha["url"],
                metadata_json={"start_time": ha["start_time"], "end_time": ha["end_time"]},
            ))
        if highlight_assets:
            self.db.commit()

        brand_profile = self.branding_service.build_brand_profile(job.project, job.style_preset)
        self.db.add(Asset(
            job_id=job.id, clip_id=None,
            asset_type="branding_profile",
            provider="branding_service",
            prompt=None,
            url=f"branding://{job.project_id}",
            metadata_json=brand_profile,
        ))
        self.db.commit()

        logger.info("[job=%s] STEP 6/7  selecting viral clip candidates via LLM …", job.id)
        _t = time.time()
        selected_clip_ids = {c.id for c in self.db.query_selected_clips(job.id)}
        candidates = self.transcript_intelligence_service.generate_candidates(job, transcript)
        logger.info("[job=%s] LLM candidate selection done in %.1fs → %d candidates", job.id, time.time() - _t, len(candidates))

        # Resolve vertical source video
        all_assets_now = self.db.query_by_job_id(Asset, job.id)
        processed_video_asset = next((a for a in all_assets_now if a.asset_type == "processed_video"), None)
        vertical_source = None
        if processed_video_asset:
            pv_url = processed_video_asset.url
            if pv_url.startswith("/storage/"):
                from app.core.config import settings as _cfg
                vertical_source = str(Path(_cfg.local_storage_path).resolve() / pv_url[len("/storage/"):])
            elif Path(pv_url).exists():
                vertical_source = pv_url
        if not vertical_source:
            vertical_source = job.input_video_url

        logger.info("[job=%s] STEP 7/7  merging segments + building assets for %d clips …", job.id, len(candidates))
        created_clips: list[ClipCandidate] = []
        for candidate_payload in candidates:
            candidate_words = candidate_payload.pop("_words", [])
            candidate_segments = candidate_payload.pop("_segments", [])
            clip = ClipCandidate(job_id=job.id, **candidate_payload)
            clip.selected = render_selected_immediately or bool(selected_clip_ids)
            self.db.add(clip)
            self.db.flush()
            created_clips.append(clip)

            logger.info("[job=%s]   clip %d/%d: '%s' — %d segment(s) to merge",
                        job.id, len(created_clips), len(candidates),
                        candidate_payload.get("title", "?")[:50],
                        len(candidate_segments))

            if candidate_segments and vertical_source:
                merged_path, merged_duration = self.video_preprocessing_service.merge_segments(
                    vertical_source, job.id, clip.id, candidate_segments
                )
                if merged_path:
                    merged_url = self.storage_service.public_url_for(Path(merged_path))
                    self.db.add(Asset(
                        job_id=job.id, clip_id=clip.id,
                        asset_type="clip_source_video",
                        provider="video_preprocessing_service",
                        prompt=None,
                        url=merged_url,
                        metadata_json={"segments": candidate_segments, "duration": merged_duration},
                    ))
                    clip.end_time = merged_duration
                    self.db.add(clip)

            if candidate_words:
                clip_words = candidate_words
            else:
                clip_words = []
                for segment_payload in transcript:
                    for word in segment_payload.get("words", []):
                        ws = word.get("start_time", word.get("start", 0.0))
                        we = word.get("end_time", word.get("end", 0.0))
                        if ws >= clip.start_time and we <= clip.end_time:
                            clip_words.append({
                                "word": word.get("word", word.get("text", "")),
                                "start_time": round(ws - clip.start_time, 3),
                                "end_time": round(we - clip.start_time, 3),
                                "confidence": word.get("confidence", 0.9),
                            })
            for w in clip_words:
                if "word" not in w and "text" in w:
                    w["word"] = w["text"]

            caption_plan = self.caption_plan_service.build_caption_plan(clip_words, clip.caption_style)
            broll_plan = self.broll_service.build_plan(clip.id, transcript, clip.broll_prompts_json)
            visual_plan = self.visual_plan_service.build(
                clip_id=clip.id,
                aspect_ratio=_platform(job),
                style=clip.caption_style,
                broll_prompts=clip.broll_prompts_json,
                cta_text=clip.cta_text,
                clip_duration=max(0.1, clip.end_time - clip.start_time),
            )
            self.db.add(Asset(job_id=job.id, clip_id=clip.id, asset_type="caption_plan", provider="caption_plan_service", prompt=None, url=f"caption-plan://{clip.id}", metadata_json=caption_plan))
            self.db.add(Asset(job_id=job.id, clip_id=clip.id, asset_type="broll_plan", provider="broll_service", prompt=None, url=f"broll-plan://{clip.id}", metadata_json=broll_plan))
            narration_script = self.narration_service.build_script(clip.title, clip.hook, clip.cta_text)
            self.db.add(Asset(job_id=job.id, clip_id=clip.id, asset_type="narration_script", provider="narration_service", prompt=None, url=f"narration-script://{clip.id}", metadata_json={"script": narration_script}))
            audio_mix_plan = self.audio_mix_service.build_mix_plan(clip.id, job.narration_enabled, job.narration_enabled)
            self.db.add(Asset(job_id=job.id, clip_id=clip.id, asset_type="audio_mix_plan", provider="audio_mix_service", prompt=None, url=f"audio-mix://{clip.id}", metadata_json=audio_mix_plan))
            narration_asset = self.elevenlabs_service.generate_narration(job.id, clip.id, narration_script, job.narration_enabled)
            if narration_asset:
                self.db.add(Asset(job_id=job.id, clip_id=clip.id, **narration_asset))
            generated_images = self.image_generation_service.generate_for_broll(job.id, clip.id, broll_plan, job.broll_enabled)
            for generated_image in generated_images:
                self.db.add(Asset(job_id=job.id, clip_id=clip.id, **generated_image))
            visual_plan["branding"] = brand_profile
            self.db.add(Asset(job_id=job.id, clip_id=clip.id, asset_type="visual_plan", provider="internal", prompt=None, url=f"visual-plan://{clip.id}", metadata_json=visual_plan))
            self.db.add(Asset(job_id=job.id, clip_id=clip.id, asset_type="clip_candidate_json", provider="transcript_intelligence_service", prompt=None, url=f"clip-candidate://{clip.id}", metadata_json=candidate_payload))
        self.db.commit()

        avg_duration = (
            sum(max(0.1, c.end_time - c.start_time) for c in created_clips) / max(1, len(created_clips))
            if created_clips else 15.0
        )
        music_asset = self.background_music_service.generate(job.id, job.style_preset, avg_duration)
        if music_asset:
            self.db.add(Asset(job_id=job.id, clip_id=None, **music_asset))
            self.db.commit()

        if render_selected_immediately:
            self.render_job(job, created_clips)

        self.db.add(Asset(
            job_id=job.id, clip_id=None,
            asset_type="webhook_event",
            provider="webhook_delivery_service",
            prompt=None,
            url=f"webhook://{job.id}/completed",
            metadata_json=self.webhook_delivery_service.build_event(job.id, "render.completed", "completed"),
        ))
        job.status = JobStatus.completed.value
        job.current_step = "completed"
        job.progress_percent = 100
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        logger.info("[job=%s] ── process() COMPLETE in %.1fs ─────────────────", job.id, time.time() - _t0)
        logger.info("[job=%s] output dir: %s", job.id, self.storage_service.job_dir(job.id))
        return job

    def render_job(self, job: Job, clips: list[ClipCandidate] | None = None) -> Job:
        from app.services.render_payload_builder import RenderPayloadBuilder

        logger.info("[job=%s] render_job() START", job.id)
        _t0 = time.time()
        builder = RenderPayloadBuilder()
        job.status = JobStatus.rendering.value
        job.current_step = "rendering"
        job.progress_percent = 80
        self.db.add(job)
        self.db.commit()

        target_clips = clips or self.db.query_selected_clips(job.id)
        if not target_clips:
            raise ValueError("No selected clips available to render")

        self.db.delete_by_job_id(Render, job.id)
        self.db.delete_by_job_id(Asset, job.id, asset_types=["rendered_clip", "thumbnail", "social_caption", "webhook_event"])

        all_assets = self.db.query_by_job_id(Asset, job.id)
        for i, clip in enumerate(target_clips, 1):
            logger.info("[job=%s] rendering clip %d/%d id=%s '%s' …",
                        job.id, i, len(target_clips), clip.id, (clip.title or "")[:50])
            _tc = time.time()
            props = builder.build(job, clip, all_assets)
            render_meta = self.render_service.create_render_metadata(clip.id, _platform(job))
            try:
                render_output = self.render_service.render_clip(job.id, clip.id, props)
                self.db.add(Render(
                    job_id=job.id, clip_id=clip.id,
                    output_format=_platform(job),
                    output_url=render_output["output_url"],
                    subtitle_url=render_output["subtitle_url"],
                    thumbnail_url=render_output["thumbnail_url"],
                    metadata_json={**render_meta, **render_output["metadata_json"]},
                    status=RenderStatus.completed.value,
                ))
                logger.info("[job=%s] clip %d render done in %.1fs → %s",
                            job.id, i, time.time() - _tc, render_output.get("output_url"))
                enrichment = self.output_enrichment_service.build_social_caption(clip.title, clip.hook, clip.cta_text)
                self.db.add(Asset(job_id=job.id, clip_id=clip.id, asset_type="rendered_clip", provider="render_service", prompt=None, url=render_output["output_url"], metadata_json={**render_output["metadata_json"], **enrichment}))
                self.db.add(Asset(job_id=job.id, clip_id=clip.id, asset_type="thumbnail", provider="render_service", prompt=None, url=render_output["thumbnail_url"], metadata_json={"clip_id": clip.id, "notes": enrichment["thumbnail_notes"]}))
                self.db.add(Asset(job_id=job.id, clip_id=clip.id, asset_type="social_caption", provider="output_enrichment_service", prompt=None, url=f"social-caption://{clip.id}", metadata_json=enrichment))
            except Exception as exc:
                logger.error("[job=%s] clip %d render FAILED in %.1fs: %s: %s",
                             job.id, i, time.time() - _tc, exc.__class__.__name__, exc)
                self.db.add(Render(
                    job_id=job.id, clip_id=clip.id,
                    output_format=_platform(job),
                    metadata_json={**render_meta, "error_type": exc.__class__.__name__},
                    status=RenderStatus.failed.value,
                    error_message=str(exc),
                ))
        self.db.add(Asset(
            job_id=job.id, clip_id=None,
            asset_type="webhook_event",
            provider="webhook_delivery_service",
            prompt=None,
            url=f"webhook://{job.id}/completed",
            metadata_json=self.webhook_delivery_service.build_event(job.id, "render.completed", "completed"),
        ))
        job.status = JobStatus.completed.value
        job.current_step = "completed"
        job.progress_percent = 100
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        logger.info("[job=%s] render_job() COMPLETE in %.1fs", job.id, time.time() - _t0)
        return job
