import pytest
from ice.core.episodic import scrub_pii

def test_scrub_pii_ssn():
    text = "My SSN is 123-45-6789."
    scrubbed_text = scrub_pii(text)
    assert scrubbed_text == "My SSN is [REDACTED_SSN]."

def test_scrub_pii_credit_card():
    text = "My credit card number is 1234-5678-9012-3456."
    scrubbed_text = scrub_pii(text)
    assert scrubbed_text == "My credit card number is [REDACTED_CREDIT_CARD]."

def test_scrub_pii_email():
    text = "My email is test@example.com."
    scrubbed_text = scrub_pii(text)
    assert scrubbed_text == "My email is [REDACTED_EMAIL]."

def test_scrub_pii_phone():
    text = "My phone number is (123) 456-7890."
    scrubbed_text = scrub_pii(text)
    assert scrubbed_text == "My phone number is [REDACTED_PHONE]."

def test_scrub_pii_no_pii():
    text = "This text has no PII."
    scrubbed_text = scrub_pii(text)
    assert scrubbed_text == text

def test_scrub_pii_multiple_pii():
    text = "My SSN is 123-45-6789 and my email is test@example.com."
    scrubbed_text = scrub_pii(text)
    assert scrubbed_text == "My SSN is [REDACTED_SSN] and my email is [REDACTED_EMAIL]."

def test_scrub_pii_empty_string():
    text = ""
    scrubbed_text = scrub_pii(text)
    assert scrubbed_text == ""

def test_scrub_pii_non_string_input():
    text = 12345
    scrubbed_text = scrub_pii(text)
    assert scrubbed_text == 12345
