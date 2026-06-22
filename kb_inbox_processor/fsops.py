from __future__ import annotations

import os
import shutil
from pathlib import Path

from .models import InboxItem


class DryRunRecorder:
    def __init__(self, enabled: bool = False):
        self.enabled = enabled
        self.actions: list[str] = []

    def record(self, action: str) -> None:
        if self.enabled:
            self.actions.append(action)


def uniquify_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    counter = 2
    while True:
        candidate = parent / f"{stem}-{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def atomic_write_text(path: Path, content: str, dry_run: DryRunRecorder) -> None:
    if dry_run.enabled:
        dry_run.record(f"write {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def copy_assets(item: InboxItem, target_dir: Path, dry_run: DryRunRecorder) -> None:
    if not item.has_assets:
        return
    for child in item.md_path.parent.iterdir():
        if child == item.md_path:
            continue
        if child.is_file() and child.suffix.lower() == ".md":
            continue
        destination = target_dir / child.name
        if dry_run.enabled:
            dry_run.record(f"copy asset {child} -> {destination}")
            continue
        target_dir.mkdir(parents=True, exist_ok=True)
        if child.is_dir():
            if destination.exists():
                shutil.rmtree(destination)
            shutil.copytree(child, destination)
        elif child.is_file():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(child, destination)


def move_to_todelete(item: InboxItem, todelete_root: Path, dry_run: DryRunRecorder) -> Path:
    destination = todelete_root / item.relative_source_unit
    destination = uniquify_path(destination)
    if dry_run.enabled:
        dry_run.record(f"move {item.source_unit} -> {destination}")
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(item.source_unit), str(destination))
    return destination


def cleanup_source(item: InboxItem, dry_run: DryRunRecorder) -> None:
    if dry_run.enabled:
        dry_run.record(f"cleanup {item.source_unit}")
        return
    if item.move_whole_dir:
        if item.source_unit.exists():
            shutil.rmtree(item.source_unit)
    elif item.md_path.exists():
        item.md_path.unlink()
