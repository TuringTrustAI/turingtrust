"""
TuringTrust — Tier 1 PII Detection (Open Source)

Regex-based detection for 15 sensitive data entity types.
Detects and flags findings. Does NOT enforce (no BLOCK/REDACT).
Enforcement is available in TuringTrust Cloud (turingtrust.ai).

License: MIT
"""

import re
import time
from dataclasses import dataclass, field
from typing import List
from enum import Enum


class EntityType(str, Enum):
    """15 supported PII/PHI/PCI entity types."""
    EMAIL = "email"
    PHONE_US = "phone_us"
    PHONE_INTL = "phone_intl"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    AWS_ACCESS_KEY = "aws_access_key"
    AWS_SECRET_KEY = "aws_secret_key"
    PRIVATE_KEY = "private_key"
    EC_PRIVATE_KEY = "private_key"
    JWT_TOKEN = "jwt_token"
    IP_ADDRESS = "ip_address"
    IBAN = "iban"
    PASSPORT_US = "passport_us"
    DRIVERS_LICENSE = "drivers_license"
    DATE_OF_BIRTH = "date_of_birth"
    API_KEY_GENERIC = "api_key_generic"


@dataclass
class PIIFinding:
    """A single PII detection result."""
    entity_type: EntityType
    confidence: str          # "high" or "medium" — regex confidence level
    start: int               # Character position start
    end: int                 # Character position end
    masked_value: str        # e.g., "****@gmail.com" — never expose full value
    context: str             # Surrounding words (redacted)


@dataclass
class DetectionResult:
    """Result of scanning a text block."""
    text_length: int
    total_findings: int
    findings: List[PIIFinding] = field(default_factory=list)
    entity_counts: dict = field(default_factory=dict)  # {"email": 3, "ssn": 1}
    scan_time_ms: float = 0.0


# ──────────────────────────────────────────────
# PATTERN DEFINITIONS
# ──────────────────────────────────────────────
# Each pattern: (EntityType, compiled_regex, confidence, description)
#
# HIGH confidence: Very specific patterns with low false positive rate.
#   Examples: AWS keys (start with AKIA), SSN (3-2-4 digit format), JWTs (eyJ prefix)
#
# MEDIUM confidence: Patterns that COULD be something else.
#   Examples: Credit card numbers (could be product SKUs), phone numbers
#   (could be order numbers), IP addresses (could be version numbers).
#   In TuringTrust Cloud, medium-confidence findings are sent to Tier 2
#   (LLM verification) for confirmation. In open-source, they're flagged
#   as "medium" and the user decides.

PATTERNS = [
    # ── HIGH CONFIDENCE ──
    (EntityType.EMAIL, re.compile(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    ), "high", "Email address"),

    (EntityType.SSN, re.compile(
        r'\b(?!000|666|9\d{2})\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b'
    ), "high", "US Social Security Number"),

    (EntityType.AWS_ACCESS_KEY, re.compile(
        r'\b(AKIA[0-9A-Z]{16})\b'
    ), "high", "AWS Access Key ID"),

    (EntityType.AWS_SECRET_KEY, re.compile(
        r'\b([A-Za-z0-9/+=]{40})\b'
    ), "medium", "Possible AWS Secret Key (40-char base64)"),

    (EntityType.PRIVATE_KEY, re.compile(
        r'-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----'
    ), "high", "Private key header"),

    (EntityType.JWT_TOKEN, re.compile(
        r'\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b'
    ), "high", "JWT Token"),

    (EntityType.IBAN, re.compile(
        r'\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}([A-Z0-9]?){0,16}\b'
    ), "high", "International Bank Account Number"),

    # ── MEDIUM CONFIDENCE ──
    (EntityType.CREDIT_CARD, re.compile(
        r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|'
        r'6(?:011|5[0-9]{2})[0-9]{12}|'
        r'(?:2131|1800|35\d{3})\d{11})\b'
    ), "medium", "Possible credit card number (Luhn check recommended)"),

    (EntityType.PHONE_US, re.compile(
        r'\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'
    ), "medium", "US phone number"),

    (EntityType.PHONE_INTL, re.compile(
        r'\b\+(?:[1-9]\d{0,2})[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}\b'
    ), "medium", "International phone number"),

    (EntityType.IP_ADDRESS, re.compile(
        r'\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b'
    ), "medium", "IPv4 address"),

    (EntityType.PASSPORT_US, re.compile(
        r'\b[A-Z]\d{8}\b'
    ), "medium", "Possible US passport number"),

    (EntityType.DRIVERS_LICENSE, re.compile(
        r'\b[A-Z]\d{7,14}\b'
    ), "medium", "Possible driver's license number"),

    (EntityType.DATE_OF_BIRTH, re.compile(
        r'\b(?:0[1-9]|1[0-2])[/-](?:0[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}\b'
    ), "medium", "Date that may be a date of birth"),

    (EntityType.API_KEY_GENERIC, re.compile(
        r'\b(?:sk-[a-zA-Z0-9]{20,}|sk-ant-[a-zA-Z0-9_-]{20,}|gsk_[a-zA-Z0-9]{20,}|AIza[0-9A-Za-z_-]{35}|xai-[a-zA-Z0-9]{20,})\b'
    ), "high", "API key (OpenAI, Anthropic, Groq, Google, xAI)"),
]


def mask_value(value: str, entity_type: EntityType) -> str:
    """Mask detected value for safe display. Never expose full PII."""
    if not value:
        return ""

    if entity_type == EntityType.EMAIL:
        parts = value.split("@")
        if len(parts) == 2:
            local = parts[0]
            domain = parts[1]
            masked_local = local[0] + "***" if len(local) > 1 else "*"
            return f"{masked_local}@{domain}"
        return "***@***"

    if entity_type == EntityType.SSN:
        # Show only last 4 digits
        return f"***-**-{value[-4:]}"

    if entity_type == EntityType.CREDIT_CARD:
        return f"****-****-****-{value[-4:]}"

    if entity_type in (EntityType.AWS_ACCESS_KEY, EntityType.API_KEY_GENERIC):
        return f"{value[:4]}***{value[-4:]}" if len(value) > 8 else "***"

    if entity_type == EntityType.PRIVATE_KEY:
        return "-----BEGIN PRIVATE KEY-----[REDACTED]"

    if entity_type == EntityType.JWT_TOKEN:
        return f"{value[:10]}...{value[-6:]}" if len(value) > 16 else "***"

    if entity_type in (EntityType.PHONE_US, EntityType.PHONE_INTL):
        return f"***-***-{value[-4:]}" if len(value) >= 4 else "***"

    if entity_type == EntityType.IP_ADDRESS:
        octets = value.split(".")
        if len(octets) == 4:
            return f"{octets[0]}.{octets[1]}.*.*"
        return "***"

    # Default: show first 2 and last 2 chars
    if len(value) > 6:
        return f"{value[:2]}{'*' * (len(value) - 4)}{value[-2:]}"
    return "*" * len(value)


def get_context(text: str, start: int, end: int, window: int = 30) -> str:
    """Get surrounding context with the finding itself masked."""
    ctx_start = max(0, start - window)
    ctx_end = min(len(text), end + window)
    before = text[ctx_start:start]
    after = text[end:ctx_end]
    return f"...{before}[REDACTED]{after}..."


def detect_pii(text: str) -> DetectionResult:
    """
    Scan text for PII/PHI/PCI/Secrets using regex patterns.

    This is Tier 1 detection — fast, deterministic, zero external dependencies.
    Returns all findings with confidence levels.

    In TuringTrust Cloud, medium-confidence findings are optionally sent to
    Tier 2 (LLM verification) for false-positive elimination.

    Args:
        text: The text to scan for sensitive data.

    Returns:
        DetectionResult with all findings, counts, and timing.
    """
    if not text:
        return DetectionResult(text_length=0, total_findings=0)

    start_time = time.time()
    findings: List[PIIFinding] = []
    entity_counts: dict = {}

    for entity_type, pattern, confidence, description in PATTERNS:
        for match in pattern.finditer(text):
            matched_value = match.group()
            masked = mask_value(matched_value, entity_type)
            context = get_context(text, match.start(), match.end())

            finding = PIIFinding(
                entity_type=entity_type,
                confidence=confidence,
                start=match.start(),
                end=match.end(),
                masked_value=masked,
                context=context,
            )
            findings.append(finding)

            type_name = entity_type.value
            entity_counts[type_name] = entity_counts.get(type_name, 0) + 1

    scan_time_ms = (time.time() - start_time) * 1000

    return DetectionResult(
        text_length=len(text),
        total_findings=len(findings),
        findings=findings,
        entity_counts=entity_counts,
        scan_time_ms=round(scan_time_ms, 2),
    )
