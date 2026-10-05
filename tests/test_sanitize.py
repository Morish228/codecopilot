from coding_assistant.util.sanitize import sanitize_for_storage


def test_strips_null_bytes():
    assert sanitize_for_storage("a\x00b") == "ab"
    assert sanitize_for_storage({"x": "a\x00b"}) == {"x": "ab"}
