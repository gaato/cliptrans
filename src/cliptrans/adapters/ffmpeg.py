"""ffmpeg/ffprobe adapter implementing MediaProcessorPort."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from cliptrans.domain.errors import PrepareError
from cliptrans.domain.models import MediaInfo


class FfmpegMediaProcessor:
    async def extract_audio(
        self,
        video: Path,
        output: Path,
        *,
        sample_rate: int = 16000,
    ) -> Path:
        """Extract mono WAV at *sample_rate* Hz from *video* into *output*."""
        output.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video),
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", str(sample_rate),
            "-ac", "1",
            str(output),
        ]
        await _run(cmd, error_cls=PrepareError, context="audio extraction")
        return output

    async def probe(self, file: Path) -> MediaInfo:
        """Return basic media info for *file* using ffprobe."""
        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_streams", "-show_format",
            str(file),
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise PrepareError(
                f"ffprobe failed on {file}: {stderr.decode(errors='replace')}"
            )
        data = json.loads(stdout.decode())
        return _parse_mediainfo(data)

    async def make_proxy(self, video: Path, output: Path) -> Path:
        """Generate a low-res proxy for editing previews."""
        output.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video),
            "-vf", "scale=iw/4:ih/4",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "28",
            "-c:a", "aac",
            "-b:a", "64k",
            str(output),
        ]
        await _run(cmd, error_cls=PrepareError, context="proxy generation")
        return output


async def _run(cmd: list[str], *, error_cls: type[Exception], context: str) -> None:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise error_cls(
            f"ffmpeg {context} failed (exit {proc.returncode}): "
            f"{stderr.decode(errors='replace')}"
        )


def _parse_mediainfo(data: dict) -> MediaInfo:
    duration = float(data.get("format", {}).get("duration", 0))
    width = height = audio_sample_rate = audio_channels = None
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video":
            width = stream.get("width")
            height = stream.get("height")
        elif stream.get("codec_type") == "audio":
            audio_sample_rate = int(stream.get("sample_rate", 0)) or None
            audio_channels = stream.get("channels")
    return MediaInfo(
        duration=duration,
        width=width,
        height=height,
        audio_sample_rate=audio_sample_rate,
        audio_channels=audio_channels,
    )
