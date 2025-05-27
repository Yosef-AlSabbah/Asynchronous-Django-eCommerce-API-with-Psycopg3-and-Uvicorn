import re

from django.core.exceptions import ValidationError


def validate_phone(phone: str) -> None:
    # Remove spaces, dashes, and parentheses
    cleaned = re.sub(r"[ \-()]", "", phone)
    # Ensure it starts with +972 or +970 and has 9 digits after the prefix
    match = re.match(r"^\+(972|970)(\d{9})$", cleaned)
    if not match:
        raise ValidationError(
            "Phone number must start with +972 or +970 and have 9 digits after the prefix."
        )

def normalize_and_validate_phone(phone: str) -> str:
    # Remove all non-digit characters except leading +
    phone = re.sub(r"[^\d+]", "", phone)
    validate_phone(phone)
    match = re.match(r"^\+(972|970)(\d{9})$", phone)
    prefix = match.group(1)
    digits = match.group(2)
    # Format to +972 XX-XXX-XXXX
    formatted = f"+{prefix} {digits[:2]}-{digits[2:5]}-{digits[5:]}"
    return formatted

def validate_arabic(value):
    # Ensure the value contains only Arabic characters and spaces
    if not re.fullmatch(r"[\u0600-\u06FF\s]+", value):
        raise ValidationError("Only Arabic characters are allowed.")
