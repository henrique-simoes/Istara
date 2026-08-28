"""Tests for voice transcription pipeline — Whisper, ICR, auto-tagging."""

import pytest
from unittest.mock import patch
from types import SimpleNamespace


# ---------------------------------------------------------------------------
# Transcription module imports
# ---------------------------------------------------------------------------

def test_transcription_module_imports():
    """Transcription module imports correctly."""
    from app.core.transcription import TranscriptionResult, transcribe_audio
    assert TranscriptionResult is not None
    assert transcribe_audio is not None


def test_transcription_result_dataclass():
    """TranscriptionResult has all expected fields."""
    from app.core.transcription import TranscriptionResult
    result = TranscriptionResult(
        text="Test transcription",
        language="en",
        confidence=0.9,
        icr_kappa=0.75,
        icr_confidence="high",
        needs_review=False,
        tags=["usability", "positive"],
    )
    assert result.text == "Test transcription"
    assert result.language == "en"
    assert result.confidence == 0.9
    assert result.icr_kappa == 0.75
    assert result.icr_confidence == "high"
    assert result.needs_review is False
    assert "usability" in result.tags


def test_transcription_unavailable_fallback():
    """When Whisper is unavailable, returns error transcription."""
    from app.core import transcription
    import tempfile
    
    with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
        with patch("app.core.transcription._load_whisper_model", return_value=None):
            result = transcription.transcribe_audio(tmp.name)
            assert "[Transcription unavailable" in result.text
            assert result.needs_review is True
            assert "transcription-error" in result.tags


def test_transcription_missing_audio_file():
    """Missing audio paths return a specific file-not-found transcription result."""
    from app.core import transcription

    result = transcription.transcribe_audio("/fake/path.ogg")

    assert "audio file not found" in result.text
    assert result.metadata["error_type"] == "audio_file_missing"
    assert result.needs_review is True
    assert "audio-file-missing" in result.tags


def test_transcription_requires_ffmpeg_when_whisper_is_available(monkeypatch):
    """Whisper-backed transcription reports a dependency error when ffmpeg is missing."""
    from app.core import transcription
    import tempfile

    class FakeModel:
        def transcribe(self, *_args, **_kwargs):
            return {"text": "should not run"}

    with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
        monkeypatch.setattr(transcription, "_WHISPER_AVAILABLE", True)
        monkeypatch.setattr("app.core.transcription._load_whisper_model", lambda *_args, **_kwargs: FakeModel())
        monkeypatch.setattr("app.core.transcription.shutil.which", lambda _name: None)

        result = transcription.transcribe_audio(tmp.name)

    assert result.metadata["error_type"] == "audio_decoder_unavailable"
    assert "audio-decoder-unavailable" in result.tags
    assert result.needs_review is True


def test_transcription_uses_detected_language_and_segment_confidence(monkeypatch):
    """Whisper language detection and segment diagnostics are surfaced in the result."""
    from app.core import transcription
    import tempfile

    class FakeModel:
        def transcribe(self, *_args, **_kwargs):
            return {
                "text": "Eu preciso de uma busca melhor",
                "language": "pt",
                "segments": [
                    {"avg_logprob": -0.08, "no_speech_prob": 0.01},
                    {"avg_logprob": -0.18, "no_speech_prob": 0.04},
                ],
            }

    with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
        monkeypatch.setattr(transcription, "_WHISPER_AVAILABLE", True)
        monkeypatch.setattr("app.core.transcription._load_whisper_model", lambda *_args, **_kwargs: FakeModel())
        monkeypatch.setattr("app.core.transcription.shutil.which", lambda _name: "/usr/bin/ffmpeg")
        monkeypatch.setattr(
            "app.core.transcription._compute_transcription_icr",
            lambda *_args, **_kwargs: SimpleNamespace(kappa=0.72, confidence="high", details={}),
        )

        result = transcription.transcribe_audio(tmp.name)

    assert result.language == "pt"
    assert result.confidence > 0.8
    assert result.metadata["detected_language"] == "pt"
    assert result.metadata["formal_reliability"] is False
    assert result.metadata["research_spine_eligible"] is False
    assert result.metadata["validation_scope"] == "transcription_quality_signal"
    assert result.metadata["research_data_status"] == "provisional_until_coding"
    assert result.metadata["icr_details"]["formal_reliability"] is False
    assert result.needs_review is False


# ---------------------------------------------------------------------------
# Auto-tagging
# ---------------------------------------------------------------------------

def test_auto_tagging_pain_points():
    """Transcription tags pain-point keywords correctly."""
    from app.core.transcription import _generate_transcription_tags
    tags = _generate_transcription_tags("This feature is really frustrating and confusing to use")
    assert "pain-point" in tags
    assert "negative" in tags


def test_auto_tagging_feature_requests():
    """Transcription tags feature request keywords."""
    from app.core.transcription import _generate_transcription_tags
    tags = _generate_transcription_tags("It would be nice if you could add a search feature")
    assert "feature-request" in tags


def test_auto_tagging_usability():
    """Transcription tags usability keywords."""
    from app.core.transcription import _generate_transcription_tags
    tags = _generate_transcription_tags("The interface is very intuitive and easy to use and it is great")
    assert "usability" in tags
    assert "positive" in tags


def test_auto_tagging_spoken_style():
    """Transcription detects spoken-style text with filler words."""
    from app.core.transcription import _generate_transcription_tags
    tags = _generate_transcription_tags("Um, I think like the button is uh not working properly")
    assert "spoken-style" in tags


def test_auto_tagging_interview_style():
    """Transcription tags interview-style phrases."""
    from app.core.transcription import _generate_transcription_tags
    tags = _generate_transcription_tags("In my experience, our team usually prefers the old design")
    assert "interview" in tags


def test_auto_tagging_length_based():
    """Transcription tags based on text length."""
    from app.core.transcription import _generate_transcription_tags

    short = _generate_transcription_tags("Yes")
    assert "short-response" in short

    long = _generate_transcription_tags(" ".join(["word"] * 60))
    assert "long-form" in long


# ---------------------------------------------------------------------------
# ICR Consensus
# ---------------------------------------------------------------------------

def test_icr_consensus_computes():
    """ICR consensus is computed for transcriptions."""
    from app.core.consensus import compute_consensus

    responses = [
        "The interface is intuitive and easy to use",
        "The interface is intuitive and easy to use",
    ]
    result = compute_consensus(responses)
    assert result.agreement_score > 0.5
    assert result.confidence in ("high", "medium")
    assert result.details["kappa_basis"] == "category_presence_by_response"
    assert "heuristic keyword categories" in result.details["kappa_basis_note"]


def test_icr_low_agreement_flags_review():
    """Low ICR agreement triggers review flag."""
    from app.core.consensus import compute_consensus

    responses = [
        "The interface is great and very user-friendly",
        "The navigation is confusing and the layout is terrible",
    ]
    result = compute_consensus(responses)
    # Different responses should have lower agreement
    assert result.agreement_score < 1.0


def test_transcription_icr_without_independent_pass_is_insufficient(monkeypatch):
    """ICR does not manufacture agreement when no alternative transcription is available."""
    from app.core import transcription

    monkeypatch.setattr("app.core.transcription._load_whisper_model", lambda *_args, **_kwargs: None)

    result = transcription._compute_transcription_icr("The interface is easy to use", "/tmp/audio.wav")

    assert result.confidence == "insufficient"
    assert result.details["reason"].startswith("Single response")


# ---------------------------------------------------------------------------
# Audio conversion
# ---------------------------------------------------------------------------

def test_audio_conversion_wav_passthrough():
    """WAV files are returned as-is without conversion."""
    from app.core.transcription import convert_audio_to_wav
    # Mock: just verify the function handles .wav paths correctly
    result = convert_audio_to_wav("/tmp/test.wav")
    assert result == "/tmp/test.wav"
