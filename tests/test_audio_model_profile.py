import pytest

from app.core.audio_model_profile import AudioModelProfile, configured_audio_profile


def test_audio_profile_public_projection_is_secret_free():
    profile = AudioModelProfile(
        provider="gpt4_diarization", model="gpt-4o-transcribe-diarize",
        endpoint_id="audio-gpt4", credential_ref="keychain://audio/gpt4",
        mode="remote", diarization=True, speaker_count="2-8",
    )
    public = profile.public_dict()
    assert public["has_credential"] is True
    assert "credential_ref" not in public
    assert public["capabilities"] == {"interview_audio": True, "microphone_chat": True, "channel_audio": True}


def test_unconfigured_audio_fails_closed():
    class Empty:
        audio_model_provider = ""

    assert configured_audio_profile(Empty()) is None


def test_unsupported_provider_and_invalid_diarization_rejected():
    with pytest.raises(ValueError, match="unsupported audio provider"):
        AudioModelProfile("pi", "model", "endpoint")
    with pytest.raises(ValueError, match="requires diarization"):
        AudioModelProfile("gpt4_diarization", "model", "endpoint")
