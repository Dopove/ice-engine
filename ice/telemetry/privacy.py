# SPDX-License-Identifier: MIT

"""
ICE Telemetry Privacy Utilities

Functions for PII redaction, identifier hashing, and data sanitization.
"""

import hashlib
import re
import ipaddress
from typing import Dict, Any, List, Optional, Union

from .config import TelemetryConfig


# Pre-compiled regex patterns for common PII types
PII_PATTERNS = {
    "email": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
    "phone_us": re.compile(r'(?<!\d)(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'),
    "ssn": re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
    "credit_card": re.compile(r'\b(?:\d[ -]*?){13,16}\b'),
    "ipv4": re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
    "api_key": re.compile(r'(?i)(api[_-]?key|secret[_-]?key|access[_-]?token)[\s:=]+[a-zA-Z0-9_\-]{20,}'),
    "jwt": re.compile(r'eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+'),
    "aws_access_key": re.compile(r'AKIA[0-9A-Z]{16}'),
    "aws_secret_key": re.compile(r'(?i)aws[_-]?secret[_-]?access[_-]?key[\s:=]+[A-Za-z0-9/+=]{40}'),
}


def hash_identifier(value: str, salt: str = "ice-telemetry") -> str:
    """
    Hash an identifier for privacy-preserving telemetry.

    Uses SHA-256 with a salt, returns first 16 chars of hex digest.
    """
    if not value:
        return ""
    return hashlib.sha256(f"{salt}:{value}".encode()).hexdigest()[:16]


def hash_ip(ip: str) -> str:
    """
    Hash an IP address, preserving subnet information for geo analysis.

    For IPv4: keeps first 2 octets, hashes last 2
    For IPv6: keeps first 4 hextets, hashes rest
    """
    if not ip:
        return ""

    try:
        ip_obj = ipaddress.ip_address(ip)
        if isinstance(ip_obj, ipaddress.IPv4Address):
            parts = ip.split('.')
            return f"{parts[0]}.{parts[1]}.{hash_identifier('.'.join(parts[2:]))[:8]}"
        else:  # IPv6
            parts = ip.split(':')
            return ':'.join(parts[:4] + [hash_identifier(':'.join(parts[4:]))[:8]])
    except ValueError:
        return hash_identifier(ip)[:16]


def redact_pii(data: Dict[str, Any], config: TelemetryConfig) -> Dict[str, Any]:
    """
    Recursively redact PII from a dictionary based on config.

    Rules:
    - Skip keys in denied_attributes
    - Only keep keys in allowed_attributes (if specified)
    - Hash identifiers (tenant_id, session_id, user_id, etc.)
    - Anonymize IPs
    - Redact PII patterns in string values
    """
    if not config.pii_redaction:
        return data

    result = {}

    for key, value in data.items():
        # Skip denied attributes
        if key in config.denied_attributes:
            continue

        # Skip if not in allowed list (when allowlist is specified)
        if config.allowed_attributes and key not in config.allowed_attributes:
            continue

        # Process value based on type
        if isinstance(value, dict):
            result[key] = redact_pii(value, config)
        elif isinstance(value, list):
            result[key] = [
                redact_pii(item, config) if isinstance(item, dict) else _sanitize_value(item, config)
                for item in value
            ]
        else:
            result[key] = _sanitize_value(value, config, key)

    return result


def _sanitize_value(value: Any, config: TelemetryConfig, key: str = "") -> Any:
    """Sanitize a single value based on its type and key name."""
    if value is None:
        return None

    if isinstance(value, str):
        # Hash identifiers
        if config.hash_identifiers and key in ("tenant_id", "session_id", "user_id", "trace_id", "span_id"):
            return hash_identifier(value)

        # Anonymize IPs
        if config.anonymize_ips:
            try:
                ipaddress.ip_address(value)
                return hash_ip(value)
            except ValueError:
                pass  # Not an IP address

        # Redact PII patterns
        return _redact_patterns(value)

    return value


def _redact_patterns(text: str) -> str:
    """Redact common PII patterns from text."""
    if not isinstance(text, str):
        return text

    for pattern_name, pattern in PII_PATTERNS.items():
        text = pattern.sub(f"[REDACTED_{pattern_name.upper()}]", text)

    return text


def is_pii_field(key: str) -> bool:
    """Check if a field name likely contains PII."""
    pii_fields = {
        "email", "phone", "phone_number", "mobile", "ssn", "social_security",
        "credit_card", "card_number", "cvv", "address", "street", "city",
        "state", "zip", "zipcode", "postal_code", "birth_date", "dob",
        "first_name", "last_name", "full_name", "username", "password",
        "api_key", "secret", "token", "access_token", "refresh_token",
        "ip", "ip_address", "client_ip", "user_agent"
    }
    return key.lower() in pii_fields


def sanitize_for_logging(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize data for safe logging (removes sensitive fields entirely).
    More aggressive than redact_pii - removes fields entirely rather than redacting.
    """
    sensitive_fields = {
        "password", "secret", "token", "api_key", "access_token",
        "refresh_token", "private_key", "private", "credential",
        "authorization", "cookie", "session_id", "csrf_token"
    }

    result = {}
    for key, value in data.items():
        if any(sensitive in key.lower() for sensitive in sensitive_fields):
            result[key] = "[REDACTED]"
        elif isinstance(value, dict):
            result[key] = sanitize_for_logging(value)
        elif isinstance(value, list):
            result[key] = [
                sanitize_for_logging(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[key] = value
    return result