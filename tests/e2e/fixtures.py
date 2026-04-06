"""Shared constants and mock data for E2E tests."""

from __future__ import annotations

from datetime import UTC, datetime

from cliptrans.domain.models import ChannelInfo, StreamInfo

#: Takanashi Kiara's real channel ID (used as a stable test constant)
KIARA_CHANNEL_ID = "UCHsx4Hqa-1ORjQTh9TYDhww"

#: A real-looking (but safe for tests) video ID
TEST_VIDEO_ID = "CxFNBMoJQik"

KIARA_CHANNEL = ChannelInfo(
    id=KIARA_CHANNEL_ID,
    name="Takanashi Kiara Ch. hololive-EN",
    english_name="Takanashi Kiara",
    photo="",
    org="Hololive",
)

KIARA_STREAM = StreamInfo(
    video_id=TEST_VIDEO_ID,
    title="【Minecraft】Kiara Builds a Farm! #hololiveEN",
    channel_id=KIARA_CHANNEL_ID,
    channel_name="Takanashi Kiara Ch. hololive-EN",
    channel_english_name="Takanashi Kiara",
    channel_photo="",
    org="Hololive",
    duration=7_320,  # 2h 2m
    status="past",
    available_at=datetime(2024, 6, 1, 18, 0, 0, tzinfo=UTC),
)
