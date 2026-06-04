import pytest

from note_growth.collector import SourcePolicyError, html_to_document, validate_public_source_url


def test_html_to_document_extracts_title_and_text() -> None:
    doc = html_to_document(
        "https://example.com",
        "<html><head><title>Test</title></head><body><h1>Hello</h1><script>x</script></body></html>",
    )
    assert doc.title == "Test"
    assert "Hello" in doc.text
    assert "script" not in doc.text.lower()


def test_note_api_paths_are_blocked() -> None:
    with pytest.raises(SourcePolicyError):
        validate_public_source_url("https://note.com/api/v3/notes")
