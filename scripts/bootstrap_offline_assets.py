import argparse
import json
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

import requests
from huggingface_hub import HfApi, snapshot_download

DIFFUSERS_MAIN_ZIP = "https://github.com/huggingface/diffusers/archive/refs/heads/main.zip"
KEEP_LOCAL_PREFIXES = (".cache/",)
MANIFEST_NAME = "download_manifest.json"


def download_file(url: str, target: Path):
    with requests.get(url, stream=True, timeout=120) as response:
        response.raise_for_status()
        with open(target, "wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)


def install_diffusers_from_source(base_dir: Path):
    vendor_dir = base_dir / "vendor"
    vendor_dir.mkdir(parents=True, exist_ok=True)
    diffusers_dir = vendor_dir / "diffusers"
    if diffusers_dir.exists():
        print(f"Diffusers source already present: {diffusers_dir}")
        return diffusers_dir

    with tempfile.TemporaryDirectory() as tmp:
        zip_path = Path(tmp) / "diffusers_main.zip"
        print("Downloading Diffusers source zip...")
        download_file(DIFFUSERS_MAIN_ZIP, zip_path)
        extract_dir = Path(tmp) / "extract"
        extract_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as archive:
            archive.extractall(extract_dir)
        extracted = next(extract_dir.glob("diffusers-*"))
        shutil.move(str(extracted), str(diffusers_dir))

    python_exe = base_dir / ".venv" / "Scripts" / "python.exe"
    print("Installing Diffusers from local source...")
    subprocess.check_call([str(python_exe), "-m", "pip", "install", "-e", str(diffusers_dir)])
    req_file = diffusers_dir / "examples" / "requirements.txt"
    if req_file.exists():
        subprocess.check_call([str(python_exe), "-m", "pip", "install", "-r", str(req_file)])
    return diffusers_dir


def _existing(files: set[str], *candidates: str) -> str | None:
    for candidate in candidates:
        if candidate in files:
            return candidate
    return None


def _optional(existing_files: set[str], *candidates: str) -> list[str]:
    return [candidate for candidate in candidates if candidate in existing_files]


def _require(file_path: str | None, description: str) -> str:
    if not file_path:
        raise RuntimeError(f"Required file missing in repo: {description}")
    return file_path


def choose_sdxl_files(repo_id: str, repo_files: list[str], preferred_variant: str) -> tuple[list[str], str]:
    files = set(repo_files)
    selected: list[str] = []

    selected.append(_require(_existing(files, "model_index.json"), "model_index.json"))
    selected.append(_require(_existing(files, "scheduler/scheduler_config.json"), "scheduler/scheduler_config.json"))

    for tokenizer_dir in ("tokenizer", "tokenizer_2"):
        selected.extend(
            _optional(
                files,
                f"{tokenizer_dir}/tokenizer.json",
                f"{tokenizer_dir}/tokenizer_config.json",
                f"{tokenizer_dir}/special_tokens_map.json",
                f"{tokenizer_dir}/merges.txt",
                f"{tokenizer_dir}/vocab.json",
                f"{tokenizer_dir}/vocab.txt",
                f"{tokenizer_dir}/spiece.model",
            )
        )

    component_map = {
        "text_encoder": ("model",),
        "text_encoder_2": ("model",),
        "unet": ("diffusion_pytorch_model",),
        "vae": ("diffusion_pytorch_model",),
    }

    actual_variant = preferred_variant.strip()
    if actual_variant:
        variant_ok = True
        for component, prefixes in component_map.items():
            if not any(f"{component}/{prefix}.{actual_variant}.safetensors" in files for prefix in prefixes):
                variant_ok = False
                break
        if not variant_ok:
            print(f"Requested variant '{actual_variant}' is not fully available in {repo_id}. Falling back to default weights.")
            actual_variant = ""

    for component, prefixes in component_map.items():
        selected.append(_require(_existing(files, f"{component}/config.json"), f"{component}/config.json"))
        chosen_weight = None
        for prefix in prefixes:
            candidates = []
            if actual_variant:
                candidates.append(f"{component}/{prefix}.{actual_variant}.safetensors")
                candidates.append(f"{component}/{prefix}.{actual_variant}.bin")
            candidates.extend([
                f"{component}/{prefix}.safetensors",
                f"{component}/{prefix}.bin",
            ])
            chosen_weight = _existing(files, *candidates)
            if chosen_weight:
                break
        selected.append(_require(chosen_weight, f"{component} weights"))

    deduped = []
    seen = set()
    for item in selected:
        if item not in seen:
            deduped.append(item)
            seen.add(item)
    return deduped, actual_variant


def choose_blip_files(repo_id: str, repo_files: list[str]) -> list[str]:
    files = set(repo_files)
    selected = [
        _require(_existing(files, "config.json"), f"{repo_id}: config.json"),
        _require(_existing(files, "preprocessor_config.json"), f"{repo_id}: preprocessor_config.json"),
        _require(_existing(files, "tokenizer_config.json"), f"{repo_id}: tokenizer_config.json"),
        _require(_existing(files, "special_tokens_map.json"), f"{repo_id}: special_tokens_map.json"),
        _require(_existing(files, "tokenizer.json"), f"{repo_id}: tokenizer.json"),
        _require(_existing(files, "vocab.txt", "vocab.json"), f"{repo_id}: vocabulary file"),
        _require(_existing(files, "generation_config.json", "config.json"), f"{repo_id}: generation/config file"),
    ]
    weight_file = _existing(files, "model.safetensors", "pytorch_model.bin")
    selected.append(_require(weight_file, f"{repo_id}: BLIP weight file"))

    deduped = []
    seen = set()
    for item in selected:
        if item not in seen:
            deduped.append(item)
            seen.add(item)
    return deduped


def prune_to_selected(target_dir: Path, selected_files: set[str]):
    if not target_dir.exists():
        return
    for path in sorted(target_dir.rglob("*"), reverse=True):
        rel = path.relative_to(target_dir).as_posix()
        if any(rel == prefix.rstrip("/") or rel.startswith(prefix) for prefix in KEEP_LOCAL_PREFIXES):
            continue
        if path.is_file() and rel not in selected_files:
            path.unlink(missing_ok=True)
        elif path.is_dir():
            try:
                path.rmdir()
            except OSError:
                pass


def snapshot(repo_id: str, target_dir: Path, token: str | None, *, selected_files: list[str], manifest: dict | None = None):
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    selected_set = set(selected_files)
    print(f"Syncing model: {repo_id}")
    print("Files kept for offline use:")
    for item in selected_files:
        print(f"  - {item}")
    prune_to_selected(target_dir, selected_set)
    snapshot_download(
        repo_id=repo_id,
        local_dir=str(target_dir),
        local_dir_use_symlinks=False,
        token=token or None,
        allow_patterns=selected_files,
        ignore_patterns=["*.msgpack", "*.h5", "*.onnx", "*.xml", "*.bin" if any(f.endswith(".safetensors") for f in selected_files) else "__never__"],
        resume_download=True,
    )
    prune_to_selected(target_dir, selected_set)
    if manifest is not None:
        manifest_path = target_dir.parent / MANIFEST_NAME
        existing = {}
        if manifest_path.exists():
            try:
                existing = json.loads(manifest_path.read_text(encoding="utf-8"))
            except Exception:
                existing = {}
        existing.update(manifest)
        manifest_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
    return target_dir


def write_accelerate_config(base_dir: Path):
    try:
        from accelerate.commands.config.default import write_basic_config

        config_dir = base_dir / "workspace" / "accelerate"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "default_config.yaml"
        write_basic_config(save_location=str(config_file), mixed_precision="fp16")
        print(f"Accelerate default config written: {config_file}")
    except Exception as exc:
        print(f"Accelerate config warning: {exc}")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-dir", required=True)
    parser.add_argument("--base-model", required=True)
    parser.add_argument("--blip-model", required=True)
    parser.add_argument("--hf-token", default="")
    parser.add_argument("--base-model-variant", default="fp16")
    return parser.parse_args()


def main():
    os.environ.setdefault("HF_XET_HIGH_PERFORMANCE", "1")
    args = parse_args()
    base_dir = Path(args.base_dir).resolve()
    workspace = base_dir / "workspace"
    models_dir = workspace / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    diffusers_dir = install_diffusers_from_source(base_dir)
    print(f"Diffusers ready: {diffusers_dir}")

    api = HfApi(token=args.hf_token or None)
    base_repo_files = api.list_repo_files(args.base_model, repo_type="model")
    blip_repo_files = api.list_repo_files(args.blip_model, repo_type="model")

    selected_base_files, actual_variant = choose_sdxl_files(args.base_model, base_repo_files, args.base_model_variant)
    selected_blip_files = choose_blip_files(args.blip_model, blip_repo_files)

    base_model_dir = models_dir / "sdxl-base"
    blip_model_dir = models_dir / "blip-image-captioning-base"

    snapshot(
        args.base_model,
        base_model_dir,
        args.hf_token,
        selected_files=selected_base_files,
        manifest={
            "base_model_repo": args.base_model,
            "base_model_variant": actual_variant,
            "base_model_selected_files": selected_base_files,
        },
    )
    snapshot(
        args.blip_model,
        blip_model_dir,
        args.hf_token,
        selected_files=selected_blip_files,
        manifest={
            "blip_model_repo": args.blip_model,
            "blip_model_selected_files": selected_blip_files,
        },
    )

    write_accelerate_config(base_dir)
    print("Offline bootstrap finished successfully.")


if __name__ == "__main__":
    main()
