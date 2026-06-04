import base64
import binascii
import logging
import re

logger = logging.getLogger(__name__)

_B64_LIKE = re.compile(r"[A-Za-z0-9+/=]{30,}")


def decode_base64_segments(text: str) -> str:
    segments = _B64_LIKE.findall(text)
    decoded_parts = []
    for segment in segments:
        try:
            padding = (4 - len(segment) % 4) % 4
            decoded = base64.b64decode(segment + "=" * padding).decode("utf-8", errors="ignore")
            decoded_parts.append(decoded)
            logger.debug("Decoded base64 segment: %.80s -> %.80s", segment, decoded)
        except (binascii.Error, UnicodeDecodeError):
            pass
    return " ".join(decoded_parts) if decoded_parts else ""


def extract_decoded_content(user_input: str) -> str:
    lowered = user_input.lower()
    if "base64" in lowered or "decode" in lowered or "b64" in lowered:
        decoded = decode_base64_segments(user_input)
        if decoded:
            return f"{user_input} [DECODED_CONTENT: {decoded}]"
    return user_input
