"""Voice Transcription Pipeline — local-first audio transcription.

Uses Whisper (via whisper.cpp or openai-whisper) for local transcription.
An optional alternate Whisper pass provides an operational agreement signal;
it is not the Research Spine's independent evidence-unit coding or formal
Fleiss' Kappa reliability gate. Low agreement triggers human review.

Integrates with:
- Interview audio file uploads
- Telegram/WhatsApp voice messages
- Chat voice input (mic icon)
- Atomic Research chain (transcriptions → nuggets → facts)

All transcriptions are auto-tagged with a clearly scoped transcription-quality
signal. Formal reliability is computed later by the Research Spine coding
plane over source evidence units.
"""

import logging
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionResult:
    """Result of audio transcription with legacy agreement metadata.

    ``icr_kappa`` and ``icr_confidence`` remain for API compatibility, but the
    values are heuristic transcription-quality signals, not formal Research
    Spine inter-coder reliability.
    """

    text: str
    language: str
    confidence: float  # 0-1, Whisper's own confidence
    icr_kappa: float  # Legacy compatibility field; heuristic agreement only
    icr_confidence: str  # high | medium | low | insufficient (heuristic)
    needs_review: bool  # True if the transcription signal is below threshold
    original_audio_path: str | None = None
    tags: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Whisper transcription
# ---------------------------------------------------------------------------

_WHISPER_AVAILABLE = False
_WHISPER_MODEL = None
_WHISPER_TINY_MODEL = None  # Cache for ICR

_TRANSCRIPTION_VALIDATION_SCOPE = "transcription_quality_signal"


def _quality_signal_metadata(**extra: object) -> dict:
    """Mark transcription agreement as provisional and non-research evidence.

    Keeping this boundary on every result prevents downstream document,
    channel, and telemetry consumers from mistaking the compatibility
    ``icr_*`` fields for the three-coder Research Spine reliability gate.
    """
    return {
        "formal_reliability": False,
        "research_spine_eligible": False,
        "validation_scope": _TRANSCRIPTION_VALIDATION_SCOPE,
        "research_data_status": "provisional_until_coding",
        **extra,
    }


def transcription_dependency_status() -> dict:
    """Return runtime dependency status for local audio transcription."""
    return {
        "whisper_available": _WHISPER_AVAILABLE,
        "ffmpeg_available": shutil.which("ffmpeg") is not None,
        "ffmpeg_path": shutil.which("ffmpeg"),
    }


def _transcription_dependency_error(audio_path: str) -> TranscriptionResult | None:
    """Return a typed dependency error if Whisper cannot decode audio locally."""
    if shutil.which("ffmpeg") is not None:
        return None

    return TranscriptionResult(
        text="[Transcription unavailable: ffmpeg is required for Whisper audio decoding. Install ffmpeg and retry transcription.]",
        language="unknown",
        confidence=0.0,
        icr_kappa=0.0,
        icr_confidence="insufficient",
        needs_review=True,
        original_audio_path=audio_path,
        tags=["transcription-error", "audio-decoder-unavailable"],
        metadata=_quality_signal_metadata(error_type="audio_decoder_unavailable"),
    )


def _estimate_whisper_confidence(result: dict) -> float:
    """Estimate confidence from Whisper segment diagnostics when available."""
    if isinstance(result.get("confidence"), (int, float)):
        return max(0.0, min(1.0, float(result["confidence"])))

    segments = result.get("segments") or []
    if not segments:
        return 0.5

    scored_segments = []
    for segment in segments:
        avg_logprob = segment.get("avg_logprob")
        no_speech_prob = segment.get("no_speech_prob")
        if not isinstance(avg_logprob, (int, float)):
            continue
        # Whisper avg_logprob is usually <= 0. Convert roughly into a bounded
        # probability-like score and penalize likely non-speech segments.
        logprob_score = max(0.0, min(1.0, 1.0 + float(avg_logprob)))
        speech_score = 1.0 - float(no_speech_prob or 0.0)
        scored_segments.append(max(0.0, min(1.0, logprob_score * speech_score)))

    if not scored_segments:
        return 0.5
    return round(sum(scored_segments) / len(scored_segments), 4)


def _load_whisper_model(model_size: str = "base"):
    """Load Whisper model for transcription and cache it."""
    global _WHISPER_AVAILABLE, _WHISPER_MODEL, _WHISPER_TINY_MODEL

    # Return cached if already loaded
    if model_size == "tiny" and _WHISPER_TINY_MODEL is not None:
        return _WHISPER_TINY_MODEL
    if model_size != "tiny" and _WHISPER_MODEL is not None:
        # Note: if model_size changed, we currently keep the old one
        # to avoid memory bloat. Future: support multiple cached sizes?
        return _WHISPER_MODEL

    try:
        import whisper

        model = whisper.load_model(model_size)
        _WHISPER_AVAILABLE = True

        if model_size == "tiny":
            _WHISPER_TINY_MODEL = model
        else:
            _WHISPER_MODEL = model

        logger.info(f"Whisper model '{model_size}' loaded successfully")
        return model
    except ImportError:
        logger.warning(
            "openai-whisper not installed — transcription disabled. "
            "Install with: pip install openai-whisper"
        )
    except Exception as e:
        logger.warning(f"Failed to load Whisper model '{model_size}': {e}")

    return None


def transcribe_audio(
    audio_path: str,
    language: str | None = None,
    model_size: str = "base",
) -> TranscriptionResult:
    """Transcribe audio file using Whisper with ICR consensus.

    Args:
        audio_path: Path to audio file (wav, mp3, ogg, m4a, flac)
        language: Optional language code (e.g., "en", "pt", "es")
        model_size: Whisper model size (tiny, base, small, medium, large)

    Returns:
        TranscriptionResult with text, confidence, and ICR scores
    """
    path = Path(audio_path)
    if not path.exists():
        return TranscriptionResult(
            text=f"[Transcription failed: audio file not found at {audio_path}]",
            language="unknown",
            confidence=0.0,
            icr_kappa=0.0,
            icr_confidence="insufficient",
            needs_review=True,
            original_audio_path=audio_path,
            tags=["transcription-error", "audio-file-missing"],
            metadata=_quality_signal_metadata(error_type="audio_file_missing"),
        )

    model = _load_whisper_model(model_size)

    if not _WHISPER_AVAILABLE or model is None:
        return TranscriptionResult(
            text="[Transcription unavailable — Whisper not installed]",
            language="unknown",
            confidence=0.0,
            icr_kappa=0.0,
            icr_confidence="insufficient",
            needs_review=True,
            original_audio_path=audio_path,
            tags=["transcription-error"],
            metadata=_quality_signal_metadata(error_type="transcription_engine_unavailable"),
        )

    dependency_error = _transcription_dependency_error(audio_path)
    if dependency_error is not None:
        return dependency_error

    try:
        result = model.transcribe(
            audio_path,
            language=language,
            task="transcribe",
        )

        text = result.get("text", "").strip()
        detected_language = result.get("language", "unknown")
        confidence = _estimate_whisper_confidence(result)

        # Run ICR consensus check
        icr_result = _compute_transcription_icr(
            text,
            audio_path,
            language=detected_language if detected_language != "unknown" else language,
        )

        # Auto-generate tags based on content
        tags = _generate_transcription_tags(text)

        icr_details = dict(icr_result.details or {})
        icr_details.update(
            {
                "formal_reliability": False,
                "research_spine_eligible": False,
                "validation_scope": _TRANSCRIPTION_VALIDATION_SCOPE,
                "research_data_status": "provisional_until_coding",
            }
        )

        return TranscriptionResult(
            text=text,
            language=detected_language,
            confidence=confidence,
            icr_kappa=icr_result.kappa or 0.0,
            icr_confidence=icr_result.confidence,
            needs_review=icr_result.confidence in ("low", "insufficient"),
            original_audio_path=audio_path,
            tags=tags,
            metadata=_quality_signal_metadata(
                model_size=model_size,
                requested_language=language,
                detected_language=detected_language,
                icr_details=icr_details,
            ),
        )

    except Exception as e:
        logger.error(f"Transcription failed for {audio_path}: {e}")
        return TranscriptionResult(
            text=f"[Transcription failed: {str(e)[:200]}]",
            language="unknown",
            confidence=0.0,
            icr_kappa=0.0,
            icr_confidence="insufficient",
            needs_review=True,
            original_audio_path=audio_path,
            tags=["transcription-error"],
            metadata=_quality_signal_metadata(
                error_type="transcription_runtime_failure", error=str(e)[:500]
            ),
        )


# ---------------------------------------------------------------------------
# Inter-Coder Reliability for Transcriptions
# ---------------------------------------------------------------------------


def _compute_transcription_icr(text: str, audio_path: str, language: str | None = None):
    """Compute a compatibility agreement signal for transcription quality.

    Uses the heuristic consensus engine to check agreement between:
    1. Primary Whisper transcription
    2. Alternative model/temperature transcription
    3. Semantic similarity check

    Returns a ``ConsensusResult`` from ``core.consensus``. Its kappa is not a
    formal Research Spine reliability result because the responses are not
    independent coders rating the same evidence-unit matrix.
    """
    from app.core.consensus import compute_consensus

    # Generate alternative transcriptions for comparison.
    # If no independent alternative is available, report insufficient evidence
    # instead of manufacturing agreement from the primary text.
    responses = [text]  # Primary transcription

    # Try to get alternative transcription (different model size)
    try:
        alt_model = _load_whisper_model("tiny")
        if alt_model:
            alt_result = alt_model.transcribe(audio_path, language=language, task="transcribe")
            alt_text = alt_result.get("text", "").strip()
            if alt_text:
                responses.append(alt_text)
    except Exception:
        logger.debug("Alternative transcription pass unavailable", exc_info=True)

    # Compute heuristic agreement; formal coding happens downstream.
    return compute_consensus(responses, method="auto")


# ---------------------------------------------------------------------------
# Auto-Tagging for Transcriptions
# ---------------------------------------------------------------------------


def _generate_transcription_tags(text: str) -> list[str]:
    """Generate tags for transcribed content based on content analysis.

    Uses keyword matching for initial tagging — will be enhanced
    with LLM-based multi-model consensus tagging in future.
    """
    text_lower = text.lower()
    tags = []

    # Research-relevant categories
    category_keywords = {
        "pain-point": [
            "frustrating",
            "difficult",
            "confusing",
            "broken",
            "annoying",
            "hate",
            "terrible",
            "worst",
        ],
        "feature-request": [
            "would be nice",
            "wish",
            "could have",
            "should have",
            "need",
            "want",
            "add",
        ],
        "usability": ["easy", "intuitive", "simple", "clear", "straightforward", "user-friendly"],
        "positive": [
            "great",
            "excellent",
            "love",
            "amazing",
            "perfect",
            "wonderful",
            "fantastic",
            "good",
        ],
        "negative": [
            "bad",
            "poor",
            "terrible",
            "awful",
            "horrible",
            "disappointing",
            "frustrating",
            "confusing",
        ],
        "navigation": ["menu", "button", "click", "scroll", "page", "screen", "find"],
        "accessibility": ["screen reader", "font size", "color contrast", "keyboard", "alt text"],
        "performance": ["slow", "fast", "lag", "load", "crash", "freeze", "timeout"],
        "interview": ["I think", "in my experience", "personally", "we usually", "our team"],
        "survey-response": ["agree", "disagree", "sometimes", "always", "never", "often"],
    }

    for tag, keywords in category_keywords.items():
        if any(kw in text_lower for kw in keywords):
            tags.append(tag)

    # Language tag
    if len(text_lower.split()) > 50:
        tags.append("long-form")
    elif len(text_lower.split()) < 10:
        tags.append("short-response")

    # Voice message indicator
    if any(w in text_lower for w in ["um", "uh", "ah", "er", "like", "you know"]):
        tags.append("spoken-style")

    return tags


# ---------------------------------------------------------------------------
# Audio format conversion helpers
# ---------------------------------------------------------------------------


def convert_audio_to_wav(audio_path: str) -> str:
    """Convert audio file to WAV format for Whisper compatibility.

    Handles: ogg, mp3, m4a, flac, opus → wav
    """
    path = Path(audio_path)
    if path.suffix.lower() == ".wav":
        return audio_path

    try:
        import subprocess

        output_path = path.with_suffix(".wav")

        # Try ffmpeg first
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", str(path), "-ar", "16000", "-ac", "1", str(output_path)],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0 and output_path.exists():
            return str(output_path)

        # Fallback: pydub
        try:
            from pydub import AudioSegment

            audio = AudioSegment.from_file(str(path))
            audio = audio.set_frame_rate(16000).set_channels(1)
            audio.export(str(output_path), format="wav")
            return str(output_path)
        except ImportError:
            logger.error("Neither ffmpeg nor pydub available for audio conversion")
            return audio_path

    except FileNotFoundError:
        logger.warning("ffmpeg not installed, attempting raw audio processing")
        return audio_path
    except Exception as e:
        logger.error(f"Audio conversion failed: {e}")
        return audio_path


# ---------------------------------------------------------------------------
# Module initialization
# ---------------------------------------------------------------------------

# Load model on import (lazy)
_transcription_model_size = os.getenv("WHISPER_MODEL_SIZE", "base")
