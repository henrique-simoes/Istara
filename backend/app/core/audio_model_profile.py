"""Governed, secret-free configuration for audio transcription providers.

Audio providers are deliberately separate from the text/Pi model catalog.  A
profile contains only routing metadata and an opaque credential reference;
callers bind the credential transiently when they actually dispatch audio.
"""

from dataclasses import dataclass

SUPPORTED_PROVIDERS = {"local_whisper", "remote_whisper", "gpt4_diarization"}


@dataclass(frozen=True)
class AudioModelProfile:
    provider: str
    model: str
    endpoint_id: str
    credential_ref: str | None = None
    mode: str = "local"
    languages: tuple[str, ...] = ()
    diarization: bool = False
    timestamps: bool = True
    speaker_count: str = "unknown"
    human_review_threshold: float = 0.7

    def __post_init__(self) -> None:
        if self.provider not in SUPPORTED_PROVIDERS:
            raise ValueError(f"unsupported audio provider: {self.provider}")
        if self.mode not in {"local", "remote"}:
            raise ValueError("audio mode must be local or remote")
        if not self.model.strip() or not self.endpoint_id.strip():
            raise ValueError("audio model and endpoint_id are required")
        if not 0 <= self.human_review_threshold <= 1:
            raise ValueError("human_review_threshold must be between 0 and 1")
        if self.provider == "local_whisper" and self.mode != "local":
            raise ValueError("local_whisper must use local mode")
        if self.provider == "gpt4_diarization" and not self.diarization:
            raise ValueError("gpt4_diarization requires diarization=true")

    @property
    def supports_interview_audio(self) -> bool:
        return True

    @property
    def supports_microphone_chat(self) -> bool:
        return True

    @property
    def supports_channel_audio(self) -> bool:
        return True

    def public_dict(self) -> dict:
        """Return an admin-safe projection; never expose credentials or URLs."""
        return {
            "provider": self.provider,
            "model": self.model,
            "endpoint_id": self.endpoint_id,
            "mode": self.mode,
            "languages": list(self.languages),
            "diarization": self.diarization,
            "timestamps": self.timestamps,
            "speaker_count": self.speaker_count,
            "human_review_threshold": self.human_review_threshold,
            "has_credential": bool(self.credential_ref),
            "capabilities": {
                "interview_audio": self.supports_interview_audio,
                "microphone_chat": self.supports_microphone_chat,
                "channel_audio": self.supports_channel_audio,
            },
        }


def configured_audio_profile(settings) -> AudioModelProfile | None:
    """Build the configured profile, or fail closed when audio is unconfigured."""
    provider = str(getattr(settings, "audio_model_provider", "") or "").strip()
    if not provider:
        return None
    return AudioModelProfile(
        provider=provider,
        model=str(getattr(settings, "audio_model", "whisper-base")),
        endpoint_id=str(getattr(settings, "audio_model_endpoint_id", "audio-default")),
        credential_ref=getattr(settings, "audio_model_credential_ref", None) or None,
        mode=str(getattr(settings, "audio_model_mode", "local")),
        languages=tuple(getattr(settings, "audio_model_languages", []) or []),
        diarization=bool(getattr(settings, "audio_model_diarization", False)),
        timestamps=bool(getattr(settings, "audio_model_timestamps", True)),
        speaker_count=str(getattr(settings, "audio_model_speaker_count", "unknown")),
        human_review_threshold=float(getattr(settings, "audio_model_review_threshold", 0.7)),
    )
