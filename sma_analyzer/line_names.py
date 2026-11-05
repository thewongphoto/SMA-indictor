"""Portable, plain-text saved-line names; never part of a signal's identity."""
import unicodedata


def normalize_name(value):
    value = unicodedata.normalize("NFC", str(value))
    if any(unicodedata.category(char).startswith("C") and not char.isspace() for char in value):
        raise ValueError("Use a name without control characters.")
    value = " ".join(value.split())
    if len(value)>60:
        raise ValueError("Use a name of 60 characters or fewer.")
    return value
