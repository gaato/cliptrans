"""faster-whisper adapter implementing TranscriberPort."""

from __future__ import annotations

import asyncio
import ctypes
import sysconfig
from pathlib import Path
from typing import TYPE_CHECKING

from cliptrans.domain.errors import TranscribeError
from cliptrans.domain.models import Segment, Word

if TYPE_CHECKING:
    from faster_whisper import WhisperModel as _WhisperModel


_CUDA_WHEEL_LIBS_LOADED = False


def _maybe_load_cuda_runtime_from_wheels(device: str) -> None:
    """Preload CUDA libraries installed from Python wheels for GPU inference."""
    global _CUDA_WHEEL_LIBS_LOADED

    if device.lower() != "cuda" or _CUDA_WHEEL_LIBS_LOADED:
        return

    purelib = Path(sysconfig.get_paths()["purelib"])
    cudnn_dir = purelib / "nvidia" / "cudnn" / "lib"
    candidate_libs = [
        purelib / "nvidia" / "cuda_runtime" / "lib" / "libcudart.so.12",
        purelib / "nvidia" / "cublas" / "lib" / "libcublasLt.so.12",
        purelib / "nvidia" / "cublas" / "lib" / "libcublas.so.12",
        *sorted(cudnn_dir.glob("libcudnn*.so*")),
    ]

    loaded_any = False
    for lib_path in candidate_libs:
        if not lib_path.exists():
            continue
        try:
            ctypes.CDLL(str(lib_path), mode=ctypes.RTLD_GLOBAL)
        except OSError as exc:
            raise TranscribeError(
                "Failed to load CUDA runtime libraries from Python wheels. "
                "Try reinstalling the GPU extras: uv sync --extra gpu"
            ) from exc
        loaded_any = True

    if loaded_any:
        _CUDA_WHEEL_LIBS_LOADED = True


class FasterWhisperTranscriber:
    def __init__(
        self,
        device: str = "cuda",
        compute_type: str = "float16",
    ) -> None:
        self._device = device
        self._compute_type = compute_type
        self._model: _WhisperModel | None = None
        self._model_name: str | None = None

    def _load_model(self, model: str) -> None:
        if self._model is not None and self._model_name == model:
            return
        _maybe_load_cuda_runtime_from_wheels(self._device)
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise TranscribeError(
                "faster-whisper is not installed. "
                "Run: uv pip install faster-whisper"
            ) from exc

        # Try loading from cache first (avoids HTTPS calls to HuggingFace).
        # Falls back to online download only if not cached.
        model_path = _resolve_model_path(model)
        self._model = WhisperModel(
            model_path,
            device=self._device,
            compute_type=self._compute_type,
            local_files_only=model_path != model,
        )
        self._model_name = model

    async def transcribe(
        self,
        audio: Path,
        *,
        language: str,
        model: str = "large-v3",
    ) -> list[Segment]:
        """Transcribe *audio* and return raw ASR segments.

        Runs GPU inference in a thread pool to avoid blocking the event loop.
        """
        if not audio.exists():
            raise TranscribeError(f"Audio file not found: {audio}")

        return await asyncio.to_thread(self._transcribe_sync, audio, language=language, model=model)

    def _transcribe_sync(
        self,
        audio: Path,
        *,
        language: str,
        model: str,
    ) -> list[Segment]:
        self._load_model(model)
        assert self._model is not None

        try:
            segments_iter, info = self._model.transcribe(
                str(audio),
                language=language,
                word_timestamps=True,
            )
        except Exception as exc:
            raise TranscribeError(f"faster-whisper transcription failed: {exc}") from exc

        detected_lang = info.language if hasattr(info, "language") else language
        results: list[Segment] = []
        for seg in segments_iter:
            words: list[Word] | None = None
            if seg.words:
                words = [
                    Word(
                        start=w.start,
                        end=w.end,
                        word=w.word,
                        confidence=getattr(w, "probability", None),
                    )
                    for w in seg.words
                ]
            results.append(
                Segment(
                    start=seg.start,
                    end=seg.end,
                    text=seg.text.strip(),
                    confidence=getattr(seg, "avg_logprob", None),
                    language=detected_lang,
                    words=words,
                )
            )
        return results


def _resolve_model_path(model: str) -> str:
    """Return the local snapshot path for *model* if cached, else the model name.

    faster-whisper stores models under:
      ~/.cache/huggingface/hub/models--Systran--faster-whisper-<name>/snapshots/<hash>/
    """
    from pathlib import Path

    hf_cache = Path.home() / ".cache" / "huggingface" / "hub"
    # Normalise: "large-v3" → "large-v3", "tiny" → "tiny"
    repo_dir = hf_cache / f"models--Systran--faster-whisper-{model}"
    snapshots_dir = repo_dir / "snapshots"
    if snapshots_dir.is_dir():
        snapshots = sorted(snapshots_dir.iterdir())
        if snapshots:
            return str(snapshots[-1])  # latest snapshot
    return model  # fall back to HF download
