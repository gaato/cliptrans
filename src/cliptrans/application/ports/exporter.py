from pathlib import Path
from typing import Protocol

from cliptrans.domain.enums import ExportFormat
from cliptrans.domain.models import Timeline


class ExporterPort(Protocol):
    async def export(
        self,
        timeline: Timeline,
        output_dir: Path,
        format: ExportFormat,
    ) -> Path: ...
