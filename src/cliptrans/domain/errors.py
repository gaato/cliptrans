"""Domain exceptions for cliptrans pipeline stages."""


class CliptransError(Exception):
    """Base exception for all cliptrans errors."""


class IngestError(CliptransError):
    """Raised when video download fails."""


class PrepareError(CliptransError):
    """Raised when audio extraction or proxy generation fails."""


class TranscribeError(CliptransError):
    """Raised when ASR transcription fails."""


class RegroupError(CliptransError):
    """Raised when segment regrouping fails."""


class TranslateError(CliptransError):
    """Raised when translation fails."""


class ExportError(CliptransError):
    """Raised when subtitle/preview export fails."""


class JobNotFoundError(CliptransError):
    """Raised when a job cannot be found by ID."""


class TimelineError(CliptransError):
    """Raised for timeline read/write/validation errors."""


class HolodexError(CliptransError):
    """Raised when Holodex API request fails."""


class SubtitleFetchError(CliptransError):
    """Raised when subtitle fetching fails."""


class ClipFinderError(CliptransError):
    """Raised when LLM clip finding fails."""
