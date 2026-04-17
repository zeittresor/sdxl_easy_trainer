import json
import os
import shutil
import subprocess
import sys
import zlib
from pathlib import Path

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def list_images(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    return sorted([p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS])


def file_crc32(path: Path, chunk_size: int = 1024 * 1024) -> str:
    crc = 0
    total = 0
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            crc = zlib.crc32(chunk, crc)
            total += len(chunk)
    return f"{crc & 0xFFFFFFFF:08x}:{total}"


def copy_images_into_folder(paths: list[Path], dest_folder: Path) -> list[Path]:
    dest_folder = ensure_dir(dest_folder)
    copied = []
    used_names = {p.name.lower() for p in dest_folder.iterdir() if p.is_file()}
    for src in paths:
        stem = src.stem
        suffix = src.suffix.lower()
        candidate = f"{stem}{suffix}"
        counter = 1
        while candidate.lower() in used_names:
            candidate = f"{stem}_{counter:03d}{suffix}"
            counter += 1
        dst = dest_folder / candidate
        shutil.copy2(src, dst)
        txt_src = src.with_suffix(".txt")
        if txt_src.exists():
            shutil.copy2(txt_src, dst.with_suffix(".txt"))
        used_names.add(candidate.lower())
        copied.append(dst)
    return copied


def open_in_file_manager(path: Path) -> None:
    if not path.exists():
        return
    if sys.platform.startswith("win"):
        os.startfile(str(path))
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def read_text_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def write_metadata_jsonl(items: list[dict], path: Path) -> None:
    lines = [json.dumps(item, ensure_ascii=False) for item in items]
    path.write_text("\n".join(lines), encoding="utf-8")
