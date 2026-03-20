from app.services.video_preprocessing_service import VideoPreprocessingService


class MediaProbeService:
    def __init__(self) -> None:
        self._pre = VideoPreprocessingService()

    def probe(self, file_path: str) -> dict:
        return self._pre.probe(file_path)
