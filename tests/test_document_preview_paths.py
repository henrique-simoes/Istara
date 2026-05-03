from pathlib import Path

from app.api.routes.documents import _resolve_document_file_path
from app.config import settings


class DummyDocument:
    project_id = "project-1"

    def __init__(self, file_path: str):
        self.file_path = file_path


def test_resolve_uploaded_relative_path_without_doubling(tmp_path, monkeypatch):
    upload_dir = tmp_path / "data" / "uploads"
    project_dir = upload_dir / "project-1"
    project_dir.mkdir(parents=True)
    file_path = project_dir / "note.txt"
    file_path.write_text("hello")

    monkeypatch.setattr(settings, "upload_dir", str(upload_dir))

    doc = DummyDocument(str(Path("data") / "uploads" / "project-1" / "note.txt"))

    assert _resolve_document_file_path(doc).resolve() == file_path.resolve()


def test_resolve_plain_filename_inside_project_upload_dir(tmp_path, monkeypatch):
    upload_dir = tmp_path / "data" / "uploads"
    project_dir = upload_dir / "project-1"
    project_dir.mkdir(parents=True)
    file_path = project_dir / "note.txt"
    file_path.write_text("hello")

    monkeypatch.setattr(settings, "upload_dir", str(upload_dir))

    doc = DummyDocument("note.txt")

    assert _resolve_document_file_path(doc).resolve() == file_path.resolve()
