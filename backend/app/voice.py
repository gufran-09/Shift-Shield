"""Amazon Polly speech synthesis for multilingual site heat alerts (Hindi & Indian English)."""
from __future__ import annotations

import io
import os
from typing import Any

import boto3
from aws_lambda_powertools import Logger

from .config import AWS_REGION, DEMO_MODE

logger = Logger(service="shiftshield-voice")

# Available Polly voices
VOICES = {
    "hi": {
        "voice_id": "Aditi",  # Standard bilingual voice (Hindi/English)
        "neural_voice_id": "Kajal",  # Neural Indian bilingual voice
        "language_code": "hi-IN",
        "engine": "standard",  # Fallback to standard for maximum region compatibility
    },
    "en": {
        "voice_id": "Raveena",  # Indian English standard
        "neural_voice_id": "Kajal",
        "language_code": "en-IN",
        "engine": "standard",
    },
}

BAND_NAMES_HI = {
    "normal": "सामान्य (Normal)",
    "caution": "सावधानी (Caution)",
    "extreme_caution": "अत्यधिक सावधानी (Extreme Caution)",
    "high": "उच्च जोखिम (High Danger)",
    "very_high": "अति उच्च जोखिम (Very High)",
}


def build_alert_speech_text(
    site_name: str,
    band: str,
    *,
    work_minutes: int | None = None,
    rest_minutes: int | None = None,
    language: str = "hi",
) -> str:
    """Construct a clear, spoken safety warning suited for noisy outdoor environments."""
    site_clean = site_name.strip() or "निर्माण स्थल (Site)"
    rest_val = rest_minutes if rest_minutes is not None else 15
    work_val = work_minutes if work_minutes is not None else 45

    if language.startswith("hi"):
        band_hi = BAND_NAMES_HI.get(band, band)
        return (
            f"ध्यान दें। {site_clean} पर गर्मी का स्तर {band_hi} है। "
            f"सभी कार्यकर्ता ध्यान दें: हर घंटे में {work_val} मिनट काम और {rest_val} मिनट का अनिवार्य विश्राम छाया में लें। "
            f"भरपूर पानी पिएं और चक्कर आने पर तुरंत सुपरवाइजर को बताएं।"
        )
    else:
        band_en = band.replace("_", " ").title()
        return (
            f"Attention please. Heat safety alert for {site_clean}. "
            f"Heat risk level is {band_en}. "
            f"All workers must observe {work_val} minutes of work and {rest_val} minutes of mandatory rest in the shade per hour. "
            f"Drink clean water and report any heat symptoms immediately."
        )


# Minimal silent/valid MP3 frame (384 bytes MPEG1 Layer III) for mock/demo fallback
_FALLBACK_MP3_FRAME = (
    b"\xff\xfb\x90\x64\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    * 12
)


def synthesize_speech(
    text: str,
    *,
    language: str = "hi",
    neural: bool = False,
) -> tuple[bytes, str]:
    """Synthesize speech using Amazon Polly with graceful fallback for offline/demo tests.
    
    Returns (audio_bytes, content_type).
    """
    voice_conf = VOICES.get("hi" if language.startswith("hi") else "en", VOICES["en"])
    voice_id = voice_conf["neural_voice_id"] if neural else voice_conf["voice_id"]
    engine = "neural" if neural else "standard"
    lang_code = voice_conf["language_code"]

    try:
        client = boto3.client("polly", region_name=AWS_REGION)
        kwargs: dict[str, Any] = {
            "Text": text,
            "OutputFormat": "mp3",
            "VoiceId": voice_id,
            "LanguageCode": lang_code,
        }
        if engine == "neural":
            kwargs["Engine"] = "neural"

        response = client.synthesize_speech(**kwargs)
        audio_stream = response.get("AudioStream")
        if audio_stream:
            return audio_stream.read(), "audio/mpeg"
    except Exception as exc:
        logger.warning("polly_synthesis_fallback", error=str(exc), language=language, voice_id=voice_id)

    # In demo mode or if Polly is unreachable in local environment without AWS credentials,
    # return deterministic fallback MP3 stream
    return _FALLBACK_MP3_FRAME, "audio/mpeg"
