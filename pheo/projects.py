from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from pheo.storage.sqlite import now_iso, project_db_path

REGISTRY_VERSION = 1


def pheo_home() -> Path:
    configured = os.environ.get("PHEO_HOME")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".pheo"


def registry_path() -> Path:
    return pheo_home() / "projects.json"


def default_project_path(name: str) -> str:
    return str(pheo_home() / "projects" / slugify(name))


def resolve_project(project: str | os.PathLike[str] | None = None) -> str:
    if project:
        return project_location(project)["path"]
    configured = os.environ.get("PHEO_PROJECT")
    if configured:
        return project_location(configured)["path"]
    current = current_project()
    if current:
        return current["path"]
    return "./.pheo"


def create_project(name: str, path: str | os.PathLike[str] | None = None, make_current: bool = True) -> dict[str, Any]:
    location = project_location(path or default_project_path(name))
    return register_project(location["path"], name=name, make_current=make_current)


def register_project(
    project: str | os.PathLike[str],
    name: str | None = None,
    make_current: bool = False,
) -> dict[str, Any]:
    location = project_location(project)
    registry = load_registry()
    projects = registry["projects"]
    existing = next((item for item in projects if item["path"] == location["path"] or item["database"] == location["database"]), None)
    timestamp = now_iso()
    if existing:
        existing.update(
            {
                "name": name or existing["name"],
                "path": location["path"],
                "database": location["database"],
                "updated_at": timestamp,
            }
        )
        record = existing
    else:
        record = {
            "name": unique_project_name(name or infer_project_name(location), projects),
            "path": location["path"],
            "database": location["database"],
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        projects.append(record)
    if make_current:
        registry["current"] = record["name"]
    save_registry(registry)
    return with_current_flag(record, registry)


def set_current_project(ref: str) -> dict[str, Any]:
    registry = load_registry()
    record = find_project(ref, registry)
    if not record:
        record = register_project(ref, make_current=False)
        registry = load_registry()
    registry["current"] = record["name"]
    save_registry(registry)
    return with_current_flag(record, registry)


def current_project() -> dict[str, Any] | None:
    registry = load_registry()
    current = registry.get("current")
    if not current:
        return None
    record = find_project(current, registry)
    return with_current_flag(record, registry) if record else None


def list_projects() -> list[dict[str, Any]]:
    registry = load_registry()
    return [with_current_flag(item, registry) for item in sorted(registry["projects"], key=lambda row: row["updated_at"], reverse=True)]


def remove_project(ref: str) -> dict[str, Any]:
    registry = load_registry()
    record = find_project(ref, registry)
    if not record:
        raise ValueError(f"Project not found: {ref}")
    registry["projects"] = [item for item in registry["projects"] if item["name"] != record["name"]]
    if registry.get("current") == record["name"]:
        registry["current"] = registry["projects"][0]["name"] if registry["projects"] else ""
    save_registry(registry)
    return with_current_flag(record, registry)


def project_summary(project: str | os.PathLike[str], name: str | None = None) -> dict[str, Any]:
    location = project_location(project)
    return {
        "name": name or infer_project_name(location),
        "path": location["path"],
        "database": location["database"],
        "current": False,
    }


def find_project(ref: str, registry: dict[str, Any] | None = None) -> dict[str, Any] | None:
    registry = registry or load_registry()
    location = None
    if any(separator in ref for separator in ("/", "\\")) or ref.startswith("sqlite:///") or ref.startswith("."):
        location = project_location(ref)
    for item in registry["projects"]:
        if ref in {item["name"], item["path"], item["database"]}:
            return item
        if location and (item["path"] == location["path"] or item["database"] == location["database"]):
            return item
    return None


def load_registry() -> dict[str, Any]:
    path = registry_path()
    if not path.exists():
        return {"version": REGISTRY_VERSION, "current": "", "projects": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        data = {}
    return {
        "version": data.get("version") or REGISTRY_VERSION,
        "current": data.get("current") or "",
        "projects": data.get("projects") or [],
    }


def save_registry(registry: dict[str, Any]) -> None:
    path = registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": REGISTRY_VERSION,
        "current": registry.get("current") or "",
        "projects": registry.get("projects") or [],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def project_location(project: str | os.PathLike[str]) -> dict[str, str]:
    value = str(project)
    if value.startswith("sqlite:///"):
        raw = value.replace("sqlite:///", "", 1)
        db_path = Path(raw).expanduser().resolve()
        return {"path": f"sqlite:///{db_path}", "database": str(db_path)}
    path = Path(value).expanduser().resolve()
    return {"path": str(path), "database": str(project_db_path(path).resolve())}


def infer_project_name(location: dict[str, str]) -> str:
    path = location["path"]
    if path.startswith("sqlite:///"):
        return slugify(Path(location["database"]).stem)
    project_path = Path(path)
    name = project_path.name
    if name.startswith(".pheo") and project_path.parent.name:
        name = project_path.parent.name if name == ".pheo" else name.lstrip(".")
    return slugify(name or "default")


def unique_project_name(name: str, projects: list[dict[str, Any]]) -> str:
    base = slugify(name)
    used = {item["name"] for item in projects}
    if base not in used:
        return base
    index = 2
    while f"{base}-{index}" in used:
        index += 1
    return f"{base}-{index}"


def with_current_flag(record: dict[str, Any], registry: dict[str, Any]) -> dict[str, Any]:
    return {**record, "current": record.get("name") == registry.get("current")}


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", str(value or "project").strip().lower()).strip("-_")
    return slug or "project"
