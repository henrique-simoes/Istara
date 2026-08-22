"""Governed, secret-free configuration for audio transcription providers.

Audio providers are deliberately separate from the text/Pi model catalog.  A
profile contains only routing metadata and an opaque credential reference;
callers bind the credential transiently when they actually dispatch audio.

Capability claims are grounded in the real runtime/dispatch layer: a provider
family advertises a capability only when a dispatch path for it actually
exists in this tree AND (for the local path) the runtime dependency is
present.  ``remote_whisper`` and ``gpt4_diarization`` are configuration-only
today — no adapter dispatches them yet — so they fail closed with no
capabilities until such an adapter lands.
"""

from dataclasses import dataclass

SUPPORTED_PROVIDERS = {"local_whisper", "remote_whisper", "gpt4_diarization"}

# Per-provider dispatch availability.  True only where a real runtime path
# exists in this tree today; everything else is configuration-only and must
# never advertise support it cannot serve (wave rule: no invented audio
# behavior).
_PROVIDER_DISPATCH_AVAILABLE = {
    "local_whisper": True,  # backend/app/core/transcription.py local path
    "remote_whisper": False,  # no remote adapter dispatch implemented
    "gpt4_diarization": False,  # no diarization adapter dispatch implemented
}


def _runtime_audio_available() -> bool:
    """Local transcription runtime status (Whisper runtime + ffmpeg decode)."""
    from app.core.transcription import transcription_dependency_status

    status = transcription_dependency_status()
    return bool(status.get("whisper_available")) and bool(status.get("ffmpeg_available"))


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
    def dispatch_available(self) -> bool:
        """True only when a real dispatch adapter exists for this provider."""
        return _PROVIDER_DISPATCH_AVAILABLE.get(self.provider, False)

    def _surface_supported(self) -> bool:
        """One honest capability answer for every audio surface.

        Capabilities derive from provider dispatch availability plus the
        local runtime state — never from configuration alone.
        """
        if not self.dispatch_available:
            return False
        if self.provider == "local_whisper":
            return _runtime_audio_available()
        return True

    @property
    def supports_interview_audio(self) -> bool:
        return self._surface_supported()

    @property
    def supports_microphone_chat(self) -> bool:
        return self._surface_supported()

    @property
    def supports_channel_audio(self) -> bool:
        return self._surface_supported()

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
            "dispatch_available": self.dispatch_available,
            "capabilities": {
                "interview_audio": self.supports_interview_audio,
                "microphone_chat": self.supports_microphone_chat,
                "channel_audio": self.supports_channel_audio,
            },
        }


def configured_audio_profile(settings) -> AudioModelProfile | None:
    """Build the configured profile, or fail closed when audio is unconfigured.

    Raises :class:`ValueError` for an unsupported provider or an invalid
    profile combination; callers (admin routes) map that to a typed
    fail-closed response — never a crash and never a silent text-model
    fallback.
    """
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


def audio_profile_error_reason(exc: ValueError) -> str:
    """Map a profile :class:`ValueError` to a stable, secret-free reason code."""
    message = str(exc)
    for fragment, reason in (
        ("unsupported audio provider", "unsupported_provider"),
        ("local_whisper must use local mode", "local_whisper_remote_mode"),
        ("requires diarization", "diarization_required"),
        ("audio mode must be local or remote", "invalid_mode"),
        ("are required", "missing_identity"),
        ("between 0 and 1", "invalid_threshold"),
    ):
        if fragment in message:
            return reason
    return "invalid_configuration"
