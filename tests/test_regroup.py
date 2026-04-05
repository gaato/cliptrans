"""Tests for RegroupService — segments → utterances grouping logic."""

from __future__ import annotations

import pytest

from cliptrans.application.services.regroup import RegroupService
from cliptrans.domain.models import Segment


def seg(start: float, end: float, text: str, speaker: str | None = None) -> Segment:
    return Segment(start=start, end=end, text=text, language="ja", speaker=speaker)


class TestRegroupBasic:
    def setup_method(self):
        self.svc = RegroupService(silence_threshold=1.0, max_chars=200)

    def test_empty(self):
        assert self.svc._regroup([]) == []

    def test_single_segment_becomes_utterance(self):
        utts = self.svc._regroup([seg(0, 1, "hello")])
        assert len(utts) == 1
        assert utts[0].original == "hello"

    def test_sentence_boundary_splits(self):
        """Punctuation (。) should flush the current utterance."""
        segs = [
            seg(0.0, 1.0, "こんにちは。"),
            seg(1.1, 2.0, "元気ですか？"),
        ]
        utts = self.svc._regroup(segs)
        assert len(utts) == 2
        assert utts[0].original == "こんにちは。"
        assert utts[1].original == "元気ですか？"

    def test_silence_gap_splits(self):
        """Gap ≥ silence_threshold should split utterances."""
        segs = [
            seg(0.0, 1.0, "part one"),
            seg(2.1, 3.0, "part two"),  # gap = 1.1 ≥ 1.0
        ]
        utts = self.svc._regroup(segs)
        assert len(utts) == 2

    def test_small_gap_does_not_split(self):
        """Gap < silence_threshold should merge segments."""
        segs = [
            seg(0.0, 1.0, "part"),
            seg(1.5, 2.5, "one"),  # gap = 0.5 < 1.0
        ]
        utts = self.svc._regroup(segs)
        assert len(utts) == 1
        assert "part" in utts[0].original

    def test_speaker_change_splits(self):
        segs = [
            seg(0.0, 1.0, "話者Aの発言", speaker="A"),
            seg(1.1, 2.0, "話者Bの発言", speaker="B"),
        ]
        utts = self.svc._regroup(segs)
        assert len(utts) == 2

    def test_same_speaker_merges(self):
        segs = [
            seg(0.0, 1.0, "続けて", speaker="A"),
            seg(1.1, 2.0, "話している", speaker="A"),
        ]
        utts = self.svc._regroup(segs)
        assert len(utts) == 1

    def test_max_chars_hard_split(self):
        svc = RegroupService(silence_threshold=10.0, max_chars=10)
        segs = [
            seg(0.0, 1.0, "AAAAA"),   # 5 chars
            seg(1.1, 2.0, "BBBBBB"),  # 6 chars → would exceed 10
        ]
        utts = svc._regroup(segs)
        assert len(utts) == 2

    def test_multi_segment_utterance_timing(self):
        segs = [
            seg(1.0, 2.0, "part"),
            seg(2.3, 3.5, "concat"),
        ]
        utts = self.svc._regroup(segs)
        assert len(utts) == 1
        assert utts[0].start == 1.0
        assert utts[0].end == 3.5

    def test_segment_ids_recorded(self):
        segs = [seg(0.0, 1.0, "a"), seg(1.1, 2.0, "b")]
        utts = self.svc._regroup(segs)
        utt = utts[0]
        assert segs[0].id in utt.segment_ids
        assert segs[1].id in utt.segment_ids

    def test_exclamation_and_question_marks(self):
        segs = [
            seg(0.0, 1.0, "いいね！"),
            seg(1.1, 2.0, "本当に？"),
        ]
        utts = self.svc._regroup(segs)
        assert len(utts) == 2

    def test_no_punctuation_long_silence_boundary(self):
        """No sentence-end punctuation but silence > threshold → still split."""
        segs = [
            seg(0.0, 1.0, "continued"),
            seg(3.0, 4.0, "after long pause"),
        ]
        utts = self.svc._regroup(segs)
        assert len(utts) == 2


class TestRegroupServiceExecute:
    async def test_execute_updates_timeline(self, job, timeline):
        svc = RegroupService()
        result = await svc.execute(job, timeline)
        assert len(result.utterances) > 0
        # timeline.json should have been written
        assert (job.data_dir / "timeline.json").exists()
