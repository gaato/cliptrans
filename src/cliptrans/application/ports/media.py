from pathlib import Path
from typing import Protocol

from cliptrans.domain.models import MediaInfo


class MediaProcessorPort(Protocol):
    async def extract_audio(
        self,
        video: Path,
        output: Path,
        *,
        sample_rate: int = 16000,
    ) -> Path: ...

    async def probe(self, file: Path) -> MediaInfo: ...

    async def make_proxy(self, video: Path, output: Path) -> Path: ...
