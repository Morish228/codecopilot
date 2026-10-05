from pathlib import Path

from coding_assistant.intelligence.embeddings import _deterministic_embedding
from coding_assistant.intelligence.parser import extract_python_symbols


def test_extract_symbols(tmp_path):
    src = tmp_path / "sample.py"
    src.write_text(
        "class Foo:\n    def bar(self):\n        return 1\n\nasync def baz():\n    pass\n",
        encoding="utf-8",
    )
    symbols = extract_python_symbols(src, tmp_path)
    names = {s.name for s in symbols}
    assert "Foo" in names
    assert "bar" in names
    assert "baz" in names


def test_deterministic_embedding_normalized():
    a = _deterministic_embedding("hello world", 384)
    b = _deterministic_embedding("hello world", 384)
    assert a == b
    norm = sum(x * x for x in a) ** 0.5
    assert abs(norm - 1.0) < 0.01
