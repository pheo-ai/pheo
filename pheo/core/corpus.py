from __future__ import annotations

import csv
import hashlib
import json
import mimetypes
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


SUPPORTED_TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".markdown",
    ".json",
    ".jsonl",
    ".csv",
    ".tsv",
    ".html",
    ".htm",
    ".xml",
    ".yaml",
    ".yml",
}


@dataclass
class Text:
    title: str
    text: str
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class File:
    path: str
    title: str = ""
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Folder:
    path: str
    tags: list[str] = field(default_factory=list)
    recursive: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


def normalize_sources(items: list[Any]) -> list[dict[str, Any]]:
    normalized = []
    for item in items:
        normalized.extend(_normalize_one(item))
    return [entry for entry in normalized if (entry.get("text") or "").strip()]


def content_hash(text: str) -> str:
    return hashlib.sha256(" ".join((text or "").split()).encode("utf-8")).hexdigest()


def _normalize_one(item: Any) -> list[dict[str, Any]]:
    if isinstance(item, Text):
        return [
            {
                "title": item.title,
                "text": item.text,
                "source_type": "text",
                "source_uri": "",
                "tags": item.tags,
                "metadata": item.metadata,
            }
        ]
    if isinstance(item, File):
        return [_file_record(Path(item.path), item.title, item.tags, item.metadata)]
    if isinstance(item, Folder):
        root = Path(item.path)
        paths = root.rglob("*") if item.recursive else root.glob("*")
        return [_file_record(path, "", item.tags, item.metadata) for path in paths if path.is_file() and _supported(path)]
    if isinstance(item, dict):
        source_type = item.get("source_type") or item.get("type") or "text"
        if source_type == "folder" or item.get("path") and Path(str(item["path"])).is_dir():
            return _normalize_one(Folder(str(item["path"]), tags=item.get("tags") or [], metadata=item.get("metadata") or {}))
        if source_type == "file" or item.get("path"):
            return _normalize_one(File(str(item["path"]), title=item.get("title") or "", tags=item.get("tags") or [], metadata=item.get("metadata") or {}))
        return [
            {
                "title": item.get("title") or "Corpus item",
                "text": item.get("text") or item.get("content") or "",
                "source_type": source_type,
                "source_uri": item.get("url") or item.get("source_uri") or "",
                "tags": item.get("tags") or [],
                "metadata": item.get("metadata") or {},
            }
        ]
    if isinstance(item, str):
        path = Path(item)
        if path.is_dir():
            return _normalize_one(Folder(item))
        if path.exists():
            return [_file_record(path, "", [], {})]
        return [{"title": "Corpus item", "text": item, "source_type": "text", "source_uri": "", "tags": [], "metadata": {}}]
    return []


def _file_record(path: Path, title: str = "", tags: list[str] | None = None, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    text = extract_text(path)
    return {
        "title": title or path.name,
        "text": text,
        "source_type": "file",
        "source_uri": str(path),
        "tags": tags or [],
        "metadata": {"mime_type": mimetypes.guess_type(str(path))[0], **(metadata or {})},
    }


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf(path)
    if suffix == ".docx":
        return _extract_docx(path)
    if suffix == ".csv":
        return _extract_delimited(path, ",")
    if suffix == ".tsv":
        return _extract_delimited(path, "\t")
    if suffix == ".json":
        try:
            return json.dumps(json.loads(path.read_text(encoding="utf-8", errors="ignore")), ensure_ascii=True)
        except json.JSONDecodeError:
            return path.read_text(encoding="utf-8", errors="ignore")
    return _strip_markup(path.read_text(encoding="utf-8", errors="ignore"))


def _supported(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_TEXT_EXTENSIONS or path.suffix.lower() in {".pdf", ".docx"}


def _extract_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return ""
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _extract_docx(path: Path) -> str:
    try:
        import docx
    except ImportError:
        return ""
    document = docx.Document(str(path))
    return "\n".join(paragraph.text for paragraph in document.paragraphs)


def _extract_delimited(path: Path, delimiter: str) -> str:
    lines = []
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
        reader = csv.reader(handle, delimiter=delimiter)
        for row in reader:
            lines.append(" | ".join(cell.strip() for cell in row if cell.strip()))
    return "\n".join(lines)


def _strip_markup(text: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()
