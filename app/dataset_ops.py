import re
from pathlib import Path

from .captioner import OfflineBlipCaptioner, format_caption_text
from .file_utils import ensure_dir, file_crc32, list_images, read_text_if_exists, write_metadata_jsonl
from .image_tools import preprocess_image


def _filename_caption(path: Path, prefix: str, suffix: str, style: str = "conservative") -> str:
    stem = re.sub(r"[_\-]+", " ", path.stem).strip()
    return format_caption_text(stem, prefix, suffix, style)


def _clear_prepared_dataset(dataset_folder: Path) -> None:
    image_dir = ensure_dir(dataset_folder / "images")
    for path in image_dir.iterdir():
        if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".txt"}:
            path.unlink(missing_ok=True)
    metadata = dataset_folder / "metadata.jsonl"
    if metadata.exists():
        metadata.unlink()


def import_and_prepare_images(
    source_folder: Path,
    dataset_folder: Path,
    target_size: tuple[int, int],
    crop_mode: str,
    blip_model_dir: Path | None,
    make_captions: bool,
    caption_prefix: str,
    caption_suffix: str,
    caption_settings: dict | None = None,
    progress_callback=None,
    log_callback=None,
) -> dict:
    images = list_images(source_folder)
    image_dir = ensure_dir(dataset_folder / "images")
    _clear_prepared_dataset(dataset_folder)
    items = []
    captioner = None
    caption_backend_warning_shown = False
    if make_captions:
        if blip_model_dir is None or not blip_model_dir.exists():
            if log_callback:
                log_callback("Captioning model not found locally. Continuing with filename-based fallback captions.")
        else:
            captioner = OfflineBlipCaptioner(blip_model_dir, **(caption_settings or {}))
    seen_hashes: set[str] = set()
    duplicates_skipped = 0
    processed_count = 0
    captioned_count = 0
    total_input = len(images)

    for scan_index, src in enumerate(images, start=1):
        crc_key = file_crc32(src)
        if crc_key in seen_hashes:
            duplicates_skipped += 1
            if log_callback:
                log_callback(f"Skipped duplicate source image: {src.name} (CRC32 {crc_key})")
            if progress_callback:
                progress_callback(scan_index, total_input)
            continue
        seen_hashes.add(crc_key)

        processed_count += 1
        dst_name = f"{processed_count:05d}.png"
        dst_path = image_dir / dst_name
        preprocess_image(src, dst_path, target_size=target_size, crop_mode=crop_mode)

        caption = ""
        txt_src = src.with_suffix(".txt")
        if txt_src.exists():
            caption = read_text_if_exists(txt_src)
            if caption_prefix or caption_suffix:
                caption = " ".join([p for p in [caption_prefix.strip(), caption, caption_suffix.strip()] if p]).strip()
        elif captioner is not None:
            try:
                caption = captioner.caption(dst_path, caption_prefix, caption_suffix)
            except Exception as exc:
                if log_callback and not caption_backend_warning_shown:
                    log_callback(
                        "Captioning backend could not be used. Continuing with filename-based fallback captions. "
                        f"Reason: {exc}"
                    )
                caption_backend_warning_shown = True
                captioner = None
                caption = _filename_caption(src, caption_prefix, caption_suffix, (caption_settings or {}).get("style", "conservative"))
        else:
            caption = _filename_caption(src, caption_prefix, caption_suffix, (caption_settings or {}).get("style", "conservative"))

        if caption:
            captioned_count += 1
            (image_dir / f"{processed_count:05d}.txt").write_text(caption, encoding="utf-8")
        items.append({"file_name": f"images/{dst_name}", "text": caption})
        if progress_callback:
            progress_callback(scan_index, total_input)
        if log_callback:
            log_callback(f"Prepared {src.name} -> {dst_name}")

    write_metadata_jsonl(items, dataset_folder / "metadata.jsonl")
    return {
        "total_input": total_input,
        "total": processed_count,
        "captioned": captioned_count,
        "duplicates_skipped": duplicates_skipped,
    }


def rebuild_metadata_from_existing_images(dataset_folder: Path) -> int:
    image_dir = dataset_folder / "images"
    files = list_images(image_dir)
    items = []
    for path in files:
        txt = read_text_if_exists(path.with_suffix(".txt"))
        rel = f"images/{path.name}"
        items.append({"file_name": rel, "text": txt})
    write_metadata_jsonl(items, dataset_folder / "metadata.jsonl")
    return len(items)
