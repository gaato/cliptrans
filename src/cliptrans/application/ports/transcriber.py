from pathlib import Path
from typing import Protocol

from cliptrans.domain.models import Segment


class TranscriberPort(Protocol):
    async def transcribe(
        self,
        audio: Path,
        *,
        language: str,
        model: str = "large-v3",
    ) -> list[Segment]: ...
