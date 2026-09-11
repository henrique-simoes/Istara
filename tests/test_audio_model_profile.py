import pytest
from app.core.audio_model_profile import AudioModelProfile, configured_audio_profile


def test_audio_profile_public_projection_is_secret_free():
    profile = AudioModelProfile(
        provider="gpt4_diarization",
        model="gpt-4o-transcribe-diarize",
        endpoint_id="audio-gpt4",
        credential_ref="keychain://audio/gpt4",
        mode="remote",
        diarization=True,
        speaker_count="2-8",
    )
    public = profile.public_dict()
    assert public["has_credential"] is True
    assert "credential_ref" not in public
    # No diarization adapter exists in the tree: configuration alone must not
    # advertise support (fail closed until an adapter lands).
    assert public["dispatch_available"] is False
    assert public["capabilities"] == {
        "interview_audio": False,
        "microphone_chat": False,
        "channel_audio": False,
    }


def test_unconfigured_audio_fails_closed():
    class Empty:
        audio_model_provider = ""

    assert configured_audio_profile(Empty()) is None


def test_unsupported_provider_and_invalid_diarization_rejected():
    with pytest.raises(ValueError, match="unsupported audio provider"):
        AudioModelProfile("pi", "model", "endpoint")
    with pytest.raises(ValueError, match="requires diarization"):
        AudioModelProfile("gpt4_diarization", "model", "endpoint")


def test_remote_whisper_is_configuration_only_no_dispatch():
    """remote_whisper has no adapter dispatch anywhere: capabilities fail closed."""
    profile = AudioModelProfile(
        provider="remote_whisper",
        model="whisper-1",
        endpoint_id="audio-remote",
        mode="remote",
    )
    assert profile.dispatch_available is False
    assert profile.supports_interview_audio is False
    assert profile.supports_microphone_chat is False
    assert profile.supports_channel_audio is False


def test_local_whisper_capabilities_follow_runtime(monkeypatch):
    """local_whisper advertises support only when the local runtime is present."""
    monkeypatch.setattr(
        "app.core.transcription.transcription_dependency_status",
        lambda: {
            "whisper_available": False,
            "ffmpeg_available": True,
            "ffmpeg_path": "/usr/bin/ffmpeg",
        },
    )
    profile = AudioModelProfile(
        provider="local_whisper",
        model="whisper-base",
        endpoint_id="audio-local",
    )
    assert profile.dispatch_available is True
    assert profile.supports_interview_audio is False
    assert profile.supports_microphone_chat is False
    assert profile.supports_channel_audio is False

    monkeypatch.setattr(
        "app.core.transcription.transcription_dependency_status",
        lambda: {
            "whisper_available": True,
            "ffmpeg_available": True,
            "ffmpeg_path": "/usr/bin/ffmpeg",
        },
    )
    assert profile.supports_interview_audio is True
    assert profile.supports_microphone_chat is True
    assert profile.supports_channel_audio is True
    public = profile.public_dict()
    assert public["dispatch_available"] is True
    assert public["capabilities"] == {
        "interview_audio": True,
        "microphone_chat": True,
        "channel_audio": True,
    }


def test_audio_profile_error_reason_is_stable_and_secret_free():
    from app.core.audio_model_profile import audio_profile_error_reason

    cases = [
        ("unsupported audio provider: pi", "unsupported_provider"),
        ("local_whisper must use local mode", "local_whisper_remote_mode"),
        ("audio mode must be local or remote", "invalid_mode"),
        ("gpt4_diarization requires diarization=true", "diarization_required"),
        ("audio model and endpoint_id are required", "missing_identity"),
        ("human_review_threshold must be between 0 and 1", "invalid_threshold"),
        ("boom", "invalid_configuration"),
    ]
    for message, expected in cases:
        assert audio_profile_error_reason(ValueError(message)) == expected
