from pathlib import Path

from app.core.config import Settings
from app.services import RAG_services


def test_loader_converts_mineru_result_to_markdown(
    monkeypatch,
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "lecture.pdf"
    pdf_path.write_bytes(b"%PDF-1.7\n")

    class FakeParseResult:
        def markdown(self) -> str:
            return "# 第一章\n递归函数需要基准情形。"

    class FakeParser:
        def parse(self, path: Path) -> FakeParseResult:
            assert path == pdf_path.resolve()
            return FakeParseResult()

    monkeypatch.setattr(
        RAG_services,
        "get_mineru_parser",
        lambda: FakeParser(),
    )

    markdown = RAG_services.loader(pdf_path)

    assert markdown == "# 第一章\n递归函数需要基准情形。"


def test_settings_accept_legacy_mineru_token(monkeypatch) -> None:
    monkeypatch.delenv("MINERU_API_KEY", raising=False)
    monkeypatch.setenv("MINERU_TOKEN", "test-token")

    settings = Settings(_env_file=None)

    assert settings.mineru_api_key == "test-token"
