from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from .dataset_ops import import_and_prepare_images, rebuild_metadata_from_existing_images
from .process_runner import ManagedProcess
from .trainer import TrainingCommandBuilder, maybe_export_extra_formats


class DatasetWorker(QObject):
    progress = pyqtSignal(int, int)
    log = pyqtSignal(str)
    finished = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, cfg: dict, target_size: tuple[int, int], make_captions: bool):
        super().__init__()
        self.cfg = cfg
        self.target_size = target_size
        self.make_captions = make_captions

    @pyqtSlot()
    def run(self):
        try:
            result = import_and_prepare_images(
                source_folder=Path(self.cfg["source_folder"]),
                dataset_folder=Path(self.cfg["dataset_dir"]),
                target_size=self.target_size,
                crop_mode=self.cfg["crop_mode"],
                blip_model_dir=Path(self.cfg["blip_model_dir"]) if self.cfg.get("blip_model_dir") else None,
                make_captions=self.make_captions,
                caption_prefix=self.cfg["caption_prefix"],
                caption_suffix=self.cfg["caption_suffix"],
                caption_settings={
                    "prompt": self.cfg.get("blip_prompt", "a photo of"),
                    "style": self.cfg.get("blip_caption_style", "conservative"),
                    "max_new_tokens": int(self.cfg.get("blip_max_new_tokens", 28)),
                    "min_new_tokens": int(self.cfg.get("blip_min_new_tokens", 6)),
                    "num_beams": int(self.cfg.get("blip_num_beams", 3)),
                    "no_repeat_ngram_size": int(self.cfg.get("blip_no_repeat_ngram_size", 3)),
                    "repetition_penalty": float(self.cfg.get("blip_repetition_penalty", 1.15)),
                },
                progress_callback=lambda a, b: self.progress.emit(a, b),
                log_callback=lambda line: self.log.emit(line),
            )
            self.finished.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))


class MetadataWorker(QObject):
    finished = pyqtSignal(int)
    failed = pyqtSignal(str)

    def __init__(self, dataset_dir: str):
        super().__init__()
        self.dataset_dir = dataset_dir

    @pyqtSlot()
    def run(self):
        try:
            count = rebuild_metadata_from_existing_images(Path(self.dataset_dir))
            self.finished.emit(count)
        except Exception as exc:
            self.failed.emit(str(exc))


class TrainingWorker(QObject):
    log = pyqtSignal(str)
    finished = pyqtSignal(int)
    failed = pyqtSignal(str)

    def __init__(self, project_root: Path, cfg: dict):
        super().__init__()
        self.project_root = project_root
        self.cfg = cfg
        self.proc = None

    @pyqtSlot()
    def run(self):
        try:
            builder = TrainingCommandBuilder(self.project_root, self.cfg)
            if self.cfg["training_mode"] == "lora":
                cmd, env = builder.lora_command()
            else:
                cmd, env = builder.embedding_command()
            self.proc = ManagedProcess(cmd, cwd=str(self.project_root), env=env)
            self.proc.start(self.log.emit, self._on_finished)
        except Exception as exc:
            self.failed.emit(str(exc))

    def _on_finished(self, code: int):
        try:
            out_dir = Path(self.cfg["output_dir"]) / self.cfg["run_name"]
            extra = maybe_export_extra_formats(out_dir, self.cfg["training_mode"], self.cfg.get("export_pt", False))
            for path in extra:
                self.log.emit(f"Created extra export: {path}")
        except Exception as exc:
            self.log.emit(f"Post-export warning: {exc}")
        self.finished.emit(code)

    def stop(self):
        if self.proc:
            self.proc.stop()
