"""ASS (Advanced SubStation Alpha) subtitle exporter."""

from __future__ import annotations

from pathlib import Path

from cliptrans.domain.models import Timeline

_ASS_STYLES_FORMAT = (
    "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour,"
    " BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle,"
    " BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding"
)
_ASS_STYLE_DEFAULT = (
    "Style: Default,Arial,48,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,"
    "0,0,0,0,100,100,0,0,1,2,2,2,10,10,10,1"
)
_ASS_STYLE_ORIGINAL = (
    "Style: Original,Arial,36,&H00AAAAAA,&H000000FF,&H00000000,&H80000000,"
    "0,0,0,0,100,100,0,0,1,1,1,8,10,10,10,1"
)
_ASS_HEADER = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes

[V4+ Styles]
{_ASS_STYLES_FORMAT}
{_ASS_STYLE_DEFAULT}
{_ASS_STYLE_ORIGINAL}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _fmt_ass(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


class ASSExporter:
    def __init__(self, bilingual: bool = False) -> None:
        self._bilingual = bilingual

    async def export(
        self, timeline: Timeline, output_dir: Path, *, filename: str = "subtitles.ass"
    ) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / filename
        lines: list[str] = [_ASS_HEADER]

        for utt in timeline.utterances:
            start = _fmt_ass(utt.start)
            end = _fmt_ass(utt.end)
            text = utt.translation or utt.original

            if self._bilingual and utt.translation:
                orig_line = (
                    f"Dialogue: 0,{start},{end},Original,,0,0,0,,{utt.original}"
                )
                lines.append(orig_line)

            lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")

        path.write_text("\n".join(lines), encoding="utf-8")
        return path
