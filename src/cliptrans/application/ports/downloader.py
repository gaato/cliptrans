from pathlib import Path
from typing import Protocol

from cliptrans.domain.models import SourceMeta


class DownloaderPort(Protocol):
    async def download(
        self,
        url: str,
        output_dir: Path,
        *,
        start: float | None = None,
        end: float | None = None,
    ) -> tuple[Path, SourceMeta]: ...
