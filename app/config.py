import json
from pathlib import Path
from .constants import CONFIG_FILE_NAME, SIMPLE_DEFAULTS, DEFAULT_LANGUAGE, DEFAULT_APPEARANCE


def download_manifest_path(base_dir: Path) -> Path:
    return default_workspace(base_dir) / "models" / "download_manifest.json"


def load_download_manifest(base_dir: Path) -> dict:
    path = download_manifest_path(base_dir)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def default_workspace(base_dir: Path) -> Path:
    return base_dir / "workspace"


def make_default_config(base_dir: Path) -> dict:
    workspace = default_workspace(base_dir)
    manifest = load_download_manifest(base_dir)
    return {
        "language": DEFAULT_LANGUAGE,
        "appearance": DEFAULT_APPEARANCE,
        "workspace_dir": str(workspace),
        "source_folder": str(workspace / "imported_raw"),
        "dataset_name": "my_dataset",
        "dataset_dir": str(workspace / "datasets" / "my_dataset"),
        "output_dir": str(workspace / "output"),
        "run_name": "my_sdxl_run",
        "base_model_repo": manifest.get("base_model_repo", "stabilityai/stable-diffusion-xl-base-1.0"),
        "base_model_dir": str(workspace / "models" / "sdxl-base"),
        "base_model_variant": manifest.get("base_model_variant", "fp16"),
        "blip_model_dir": str(workspace / "models" / "blip-image-captioning-base"),
        "diffusers_dir": str(base_dir / "vendor" / "diffusers"),
        "caption_model": "BLIP base",
        "crop_mode": "center",
        "training_queue": [],
        **SIMPLE_DEFAULTS,
    }


def config_path(base_dir: Path) -> Path:
    return base_dir / CONFIG_FILE_NAME


def load_config(base_dir: Path) -> dict:
    path = config_path(base_dir)
    if not path.exists():
        cfg = make_default_config(base_dir)
        save_config(base_dir, cfg)
        return cfg
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        defaults = make_default_config(base_dir)
        defaults.update(loaded)
        if not isinstance(defaults.get("training_queue"), list):
            defaults["training_queue"] = []
        return defaults
    except Exception:
        cfg = make_default_config(base_dir)
        save_config(base_dir, cfg)
        return cfg


def save_config(base_dir: Path, cfg: dict) -> None:
    path = config_path(base_dir)
    path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
