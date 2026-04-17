from math import ceil
from pathlib import Path
from PIL import Image, ImageFilter, ImageOps, ImageStat


def _safe_centering(value: float) -> float:
    return max(0.15, min(0.85, float(value)))


def _entropy_score(img: Image.Image) -> float:
    return float(img.convert("L").entropy())


def _contrast_score(img: Image.Image) -> float:
    stat = ImageStat.Stat(img.convert("L"))
    return float(stat.stddev[0])


def _oriented_rgb(img: Image.Image) -> Image.Image:
    return ImageOps.exif_transpose(img).convert("RGB")


def estimate_focal_point(img: Image.Image) -> tuple[float, float]:
    tiny = img.convert("L")
    tiny.thumbnail((256, 256), Image.Resampling.LANCZOS)
    edges = tiny.filter(ImageFilter.FIND_EDGES)
    width, height = edges.size
    pixels = list(edges.getdata())
    total = float(sum(pixels))
    if total <= 0:
        return 0.5, 0.5
    weighted_x = 0.0
    weighted_y = 0.0
    for idx, value in enumerate(pixels):
        x = idx % width
        y = idx // width
        weighted_x += x * value
        weighted_y += y * value
    cx = weighted_x / total / max(width - 1, 1)
    cy = weighted_y / total / max(height - 1, 1)
    return _safe_centering(cx), _safe_centering(cy)


def average_border_color(img: Image.Image) -> tuple[int, int, int]:
    rgb = img.convert("RGB")
    w, h = rgb.size
    sample = max(1, min(w, h) // 20)
    strips = [
        rgb.crop((0, 0, w, sample)),
        rgb.crop((0, h - sample, w, h)),
        rgb.crop((0, 0, sample, h)),
        rgb.crop((w - sample, 0, w, h)),
    ]
    merged = Image.new("RGB", (sample * 2, sample * 4))
    y = 0
    for strip in strips:
        tile = strip.resize((sample * 2, sample), Image.Resampling.BILINEAR)
        merged.paste(tile, (0, y))
        y += sample
    stat = ImageStat.Stat(merged)
    return tuple(int(v) for v in stat.mean[:3])


def _best_smart_crop_box(img: Image.Image, target_size: tuple[int, int]) -> tuple[int, int, int, int]:
    src_w, src_h = img.size
    dst_w, dst_h = target_size
    src_ratio = src_w / max(src_h, 1)
    dst_ratio = dst_w / max(dst_h, 1)
    cx, cy = estimate_focal_point(img)

    if abs(src_ratio - dst_ratio) < 0.01:
        return (0, 0, src_w, src_h)

    if src_ratio > dst_ratio:
        crop_h = src_h
        crop_w = int(round(crop_h * dst_ratio))
        max_x = max(src_w - crop_w, 0)
        preferred_left = int(round(cx * max_x))
        step = max(8, crop_w // 12)
        starts = {0, max_x, max(0, min(max_x, preferred_left))}
        for delta in range(1, ceil(max_x / max(step, 1)) + 1):
            left = preferred_left - delta * step
            right = preferred_left + delta * step
            if left >= 0:
                starts.add(left)
            if right <= max_x:
                starts.add(right)
        best_score = None
        best_box = (0, 0, crop_w, crop_h)
        for left in sorted(starts):
            box = (left, 0, left + crop_w, crop_h)
            region = img.crop(box)
            score = _entropy_score(region) * 1.4 + _contrast_score(region)
            if best_score is None or score > best_score:
                best_score = score
                best_box = box
        return best_box

    crop_w = src_w
    crop_h = int(round(crop_w / dst_ratio))
    max_y = max(src_h - crop_h, 0)
    preferred_top = int(round(cy * max_y))
    step = max(8, crop_h // 12)
    starts = {0, max_y, max(0, min(max_y, preferred_top))}
    for delta in range(1, ceil(max_y / max(step, 1)) + 1):
        up = preferred_top - delta * step
        down = preferred_top + delta * step
        if up >= 0:
            starts.add(up)
        if down <= max_y:
            starts.add(down)
    best_score = None
    best_box = (0, 0, crop_w, crop_h)
    for top in sorted(starts):
        box = (0, top, crop_w, top + crop_h)
        region = img.crop(box)
        score = _entropy_score(region) * 1.4 + _contrast_score(region)
        if best_score is None or score > best_score:
            best_score = score
            best_box = box
    return best_box


def preprocess_image(
    src_path: Path,
    dst_path: Path,
    target_size: tuple[int, int],
    crop_mode: str = "center",
) -> tuple[int, int]:
    with Image.open(src_path) as img:
        img = _oriented_rgb(img)
        if crop_mode == "smart":
            crop_box = _best_smart_crop_box(img, target_size)
            cropped = img.crop(crop_box)
            resized = cropped.resize(target_size, Image.Resampling.LANCZOS)
        elif crop_mode == "pad":
            fill = average_border_color(img)
            resized = ImageOps.pad(
                img,
                target_size,
                method=Image.Resampling.LANCZOS,
                color=fill,
                centering=(0.5, 0.5),
            )
        else:
            resized = ImageOps.fit(
                img,
                target_size,
                method=Image.Resampling.LANCZOS,
                centering=(0.5, 0.5),
            )
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        resized.save(dst_path, format="PNG", optimize=True)
        return resized.size



def rotate_prepared_image(path: Path, angle: int) -> tuple[int, int]:
    with Image.open(path) as img:
        base = _oriented_rgb(img)
        original_size = base.size
        rotated = base.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
        fill = average_border_color(rotated)
        fitted = ImageOps.pad(
            rotated,
            original_size,
            method=Image.Resampling.LANCZOS,
            color=fill,
            centering=(0.5, 0.5),
        )
        fitted.save(path, format="PNG", optimize=True)
        return fitted.size
