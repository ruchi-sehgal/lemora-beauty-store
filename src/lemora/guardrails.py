import time
from collections import defaultdict, deque
import re

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
NRIC = re.compile(r"\b[STFGM]\d{7}[A-Z]\b", re.IGNORECASE)
NUMBER_RUN = re.compile(r"\+?\d[\d ()-]{6,}\d")


def scrub_pii(text):
    """Return (clean_text, list_of_what_was_removed)."""
    found = []

    def hide(label):
        def replace(match):
            found.append(label)
            return f"[{label} removed]"
        return replace

    def hide_number(match):
        digits = sum(ch.isdigit() for ch in match.group())
        if digits >= 13:
            label = "card number"
        elif digits >= 8:
            label = "phone number"
        else:
            return match.group()
        found.append(label)
        return f"[{label} removed]"

    text = EMAIL.sub(hide("email"), text)
    text = NRIC.sub(hide("ID number"), text)
    text = NUMBER_RUN.sub(hide_number, text)
    return text, found

_recent = defaultdict(deque)


def allow(key, limit=20, window_seconds=600):
    """True if this key is under its limit; records the call if so."""
    now = time.monotonic()
    calls = _recent[key]
    while calls and now - calls[0] > window_seconds:
        calls.popleft()
    if len(calls) >= limit:
        return False
    calls.append(now)
    return True

INJECTION = re.compile(
    r"ignore (all |any )?(the |your )?(previous|prior|above|earlier) (instructions|rules|prompts?)"
    r"|disregard (all |any )?(the |your )?(previous|prior|above|earlier)"
    r"|(reveal|show|print|repeat|tell me) (me )?(your|the) (system )?(prompt|instructions|rules)"
    r"|you are now\b|pretend (to be|you are)|\bjailbreak\b|developer mode",
    re.IGNORECASE,
)


def looks_like_injection(text):
    return bool(INJECTION.search(text))