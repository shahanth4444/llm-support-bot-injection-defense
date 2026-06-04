import re
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

BLOCKED_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above|earlier)\s+instructions?",
    r"ignore\s+(your\s+)?(system\s+)?(prompt|guidelines?|rules?|constraints?)",
    r"\bDAN\b",
    r"do\s+anything\s+now",
    r"jailbreak",
    r"you\s+are\s+now\s+(a\s+)?(different|new|another|unrestricted|free)",
    r"forget\s+(your\s+)?(guidelines?|rules?|instructions?|training|prompt|constraints?)",
    r"pretend\s+(you\s+(are|have)\s+no\s+restrictions?|to\s+be\s+an?\s+ai\s+with\s+no)",
    r"act\s+as\s+(if\s+you\s+have\s+no|an?\s+unrestricted|a\s+different)",
    r"system\s+(override|prompt\s*:)",
    r"new\s+(directive|system\s+prompt|instructions?)\s*[:\-]",
    r"reveal\s+(your\s+)?(full\s+)?(system\s+)?(prompt|instructions?|guidelines?)",
    r"show\s+(me\s+)?(your\s+)?(full\s+)?(system\s+)?(prompt|instructions?)",
    r"(share|give|tell|print|output|display)\s+(me\s+)?(your\s+)?(full\s+)?(system\s+)?(prompt|instructions?)",
    r"(what\s+is|what's)\s+your\s+(full\s+)?system\s+prompt",
    r"your\s+(full\s+)?system\s+prompt",
    r"override\s+(all\s+)?(previous\s+)?(instructions?|directives?)",
    r"disregard\s+(all\s+)?(previous|prior)\s+instructions?",
    r"you\s+have\s+no\s+restrictions?",
    r"without\s+(any\s+)?restrictions?",
    r"bypass\s+(your\s+)?(guidelines?|rules?|safety|filters?)",
    r"unlimited\s+(access|mode|ai)",
    r"developer\s+mode",
    r"god\s+mode",
    r"unrestricted\s+(mode|ai|access)",
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in BLOCKED_PATTERNS]


def contains_injection_attempt(user_input: str) -> Tuple[bool, str]:
    for i, pattern in enumerate(COMPILED_PATTERNS):
        if pattern.search(user_input):
            matched = BLOCKED_PATTERNS[i]
            logger.warning("Input filter triggered. Pattern: %s | Input: %.100s", matched, user_input)
            return True, f"Blocked by pattern: {matched}"
    return False, ""


def sanitize_input(user_input: str) -> str:
    if not isinstance(user_input, str):
        raise ValueError("Input must be a string.")
    user_input = user_input.strip()
    if not user_input:
        raise ValueError("Input must not be empty.")
    if len(user_input) > 2000:
        raise ValueError("Input exceeds maximum allowed length of 2000 characters.")
    return user_input
