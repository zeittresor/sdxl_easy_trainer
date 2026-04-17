import os
import sys
from pathlib import Path
from .post_export import convert_safetensors_to_pt


class TrainingCommandBuilder:
    def __init__(self, project_root: Path, config: dict):
        self.project_root = project_root
        self.config = config

    def _python_exe(self) -> str:
        if os.name == "nt":
            return str(self.project_root / ".venv" / "Scripts" / "python.exe")
        return sys.executable

    def _env(self) -> dict:
        env = os.environ.copy()
        env["HF_HUB_DISABLE_TELEMETRY"] = "1"
        env["HF_HUB_OFFLINE"] = "1"
        env["TRANSFORMERS_OFFLINE"] = "1"
        env["HF_DATASETS_OFFLINE"] = "1"
        env["DIFFUSERS_VERBOSITY"] = "info"
        return env

    def lora_command(self) -> tuple[list[str], dict]:
        script = Path(self.config["diffusers_dir"]) / "examples" / "text_to_image" / "train_text_to_image_lora_sdxl.py"
        output_dir = Path(self.config["output_dir"]) / self.config["run_name"]
        output_dir.mkdir(parents=True, exist_ok=True)
        cmd = [
            self._python_exe(), "-m", "accelerate.commands.launch",
            str(script),
            "--pretrained_model_name_or_path", self.config["base_model_dir"],
            "--train_data_dir", self.config["dataset_dir"],
            "--output_dir", str(output_dir),
            "--resolution", str(self.config["resolution"]),
            "--train_batch_size", str(self.config["batch_size"]),
            "--gradient_accumulation_steps", str(self.config["gradient_accumulation_steps"]),
            "--learning_rate", str(self.config["learning_rate"]),
            "--lr_scheduler", str(self.config["lr_scheduler"]),
            "--max_train_steps", str(self.config["max_train_steps"]),
            "--checkpointing_steps", str(self.config["save_steps"]),
            "--rank", str(self.config["rank"]),
            "--mixed_precision", self.config["mixed_precision"],
            "--report_to", "tensorboard",
            "--center_crop",
        ]
        if self.config.get("base_model_variant"):
            cmd.extend(["--variant", self.config["base_model_variant"]])
        if self.config.get("gradient_checkpointing"):
            cmd.append("--gradient_checkpointing")
        if self.config.get("train_text_encoder"):
            cmd.extend(["--train_text_encoder", "--text_encoder_lr", str(self.config["text_encoder_lr"])])
        return cmd, self._env()

    def embedding_command(self) -> tuple[list[str], dict]:
        script = Path(self.config["diffusers_dir"]) / "examples" / "textual_inversion" / "textual_inversion_sdxl.py"
        output_dir = Path(self.config["output_dir"]) / self.config["run_name"]
        output_dir.mkdir(parents=True, exist_ok=True)
        cmd = [
            self._python_exe(), "-m", "accelerate.commands.launch",
            str(script),
            "--pretrained_model_name_or_path", self.config["base_model_dir"],
            "--train_data_dir", str(Path(self.config["dataset_dir"]) / "images"),
            "--output_dir", str(output_dir),
            "--placeholder_token", self.config["embedding_placeholder_token"],
            "--initializer_token", self.config["embedding_initializer_token"],
            "--learnable_property", self.config["embedding_learnable_property"],
            "--resolution", str(self.config["embedding_resolution"]),
            "--train_batch_size", str(self.config["batch_size"]),
            "--gradient_accumulation_steps", str(self.config["gradient_accumulation_steps"]),
            "--learning_rate", str(self.config["learning_rate"]),
            "--max_train_steps", str(self.config["max_train_steps"]),
            "--save_steps", str(self.config["save_steps"]),
            "--num_vectors", str(self.config["embedding_num_vectors"]),
            "--repeats", str(self.config["embedding_repeats"]),
            "--mixed_precision", self.config["mixed_precision"],
            "--center_crop",
            "--report_to", "tensorboard",
        ]
        if self.config.get("base_model_variant"):
            cmd.extend(["--variant", self.config["base_model_variant"]])
        if self.config.get("gradient_checkpointing"):
            cmd.append("--gradient_checkpointing")
        return cmd, self._env()


def find_main_output_file(output_dir: Path, mode: str) -> Path | None:
    if not output_dir.exists():
        return None
    if mode == "lora":
        candidate = output_dir / "pytorch_lora_weights.safetensors"
        if candidate.exists():
            return candidate
        files = sorted(output_dir.glob("**/*lora*.safetensors"))
        return files[-1] if files else None
    files = sorted(output_dir.glob("**/learned_embeds*.safetensors"))
    return files[-1] if files else None


def maybe_export_extra_formats(output_dir: Path, mode: str, export_pt: bool) -> list[Path]:
    created = []
    if not export_pt:
        return created
    src = find_main_output_file(output_dir, mode)
    if src is None:
        return created
    dst = src.with_suffix(".pt")
    convert_safetensors_to_pt(src, dst)
    created.append(dst)
    return created
