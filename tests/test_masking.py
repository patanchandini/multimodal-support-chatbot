from app.masking import mask, mask_dict


def test_email_is_masked():
    result = mask("Contact me at john@example.com")
    assert "john@example.com" not in result
    assert "[EMAIL_REDACTED]" in result


def test_credit_card_is_masked():
    result = mask("My card is 4111 1111 1111 1111")
    assert "4111" not in result
    assert "[CARD_REDACTED]" in result


def test_phone_is_masked():
    result = mask("Call me at +1 555 123 4567")
    assert "555" not in result or "[PHONE_REDACTED]" in result


def test_cvv_is_masked():
    result = mask("CVV: 123")
    assert "123" not in result or "CVV_REDACTED" in result


def test_clean_text_is_unchanged():
    assert mask("Hello world") == "Hello world"


def test_mask_dict_recurses():
    data = {"user": {"email": "a@b.com"}, "list": ["x@y.com"]}
    masked = mask_dict(data)
    assert "[EMAIL_REDACTED]" in str(masked)


def test_empty_string():
    assert mask("") == ""
    assert mask(None) == ""