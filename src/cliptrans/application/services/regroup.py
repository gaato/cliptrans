"""SegmentRegrouper — group ASR segments into translation-ready utterances.

Rules (applied in priority order):
1. Sentence boundary — punctuation (。！？!?)
2. Silence gap — gap between consecutive segments exceeds *silence_threshold*
3. Speaker change — segment.speaker differs from the current accumulation
4. Max length — accumulated text exceeds *max_chars* (hard split)
"""

from __future__ import annotations

import re

from cliptrans.domain.models import Job, Segment, Timeline, Utterance
from cliptrans.timeline_io import write_timeline

_SENTENCE_END = re.compile(r"[。！？!?]$")


class RegroupService:
    def __init__(
        self,
        silence_threshold: float = 1.0,
        max_chars: int = 200,
    ) -> None:
        self._silence_threshold = silence_threshold
        self._max_chars = max_chars

    async def execute(self, job: Job, timeline: Timeline) -> Timeline:
        """Regroup timeline.segments into timeline.utterances and persist."""
        assert job.data_dir is not None
        timeline.utterances = self._regroup(timeline.segments)
        write_timeline(timeline, job.data_dir / "timeline.json")
        return timeline

    def _regroup(self, segments: list[Segment]) -> list[Utterance]:
        if not segments:
            return []

        utterances: list[Utterance] = []
        bucket: list[Segment] = []

        def flush() -> None:
            if not bucket:
                return
            utt = _make_utterance(bucket)
            utterances.append(utt)
            bucket.clear()

        for _i, seg in enumerate(segments):
            if bucket:
                prev = bucket[-1]
                gap = seg.start - prev.end
                speaker_change = (
                    seg.speaker is not None
                    and prev.speaker is not None
                    and seg.speaker != prev.speaker
                )
                accumulated_chars = sum(len(s.text) for s in bucket)
                would_exceed = accumulated_chars + len(seg.text) > self._max_chars

                if gap >= self._silence_threshold or speaker_change or would_exceed:
                    flush()

            bucket.append(seg)

            # Sentence boundary — flush *after* appending so the punctuated
            # segment belongs to the current utterance.
            if _SENTENCE_END.search(seg.text.strip()):
                flush()

        flush()
        return utterances


def _make_utterance(segments: list[Segment]) -> Utterance:
    return Utterance(
        segment_ids=[s.id for s in segments],
        start=segments[0].start,
        end=segments[-1].end,
        original="".join(s.text for s in segments).strip(),
        speaker=segments[0].speaker,
    )
