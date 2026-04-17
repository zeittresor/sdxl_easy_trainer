import json
import re
from pathlib import Path
from PyQt6.QtCore import Qt, QSize, QThread, QTimer
from PyQt6.QtGui import QIcon, QPixmap, QAction
from PyQt6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QCheckBox,
    QSpinBox,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from ..config import load_config, save_config
from ..constants import APP_NAME, APP_VERSION, RESOLUTION_PRESETS, VRAM_TRAINING_PRESETS
from ..file_utils import copy_images_into_folder, list_images, open_in_file_manager, read_text_if_exists
from ..i18n import ENGLISH_STRINGS, get_strings, language_options
from ..theme import get_stylesheet
from ..runtime_checks import torch_status
from ..image_tools import rotate_prepared_image
from ..captioner import OfflineBlipCaptioner, format_caption_text
from ..workers import DatasetWorker, MetadataWorker, TrainingWorker
from ..dataset_ops import rebuild_metadata_from_existing_images


class ConfigEditorDialog(QDialog):
    def __init__(self, parent, config_text: str):
        super().__init__(parent)
        self.setWindowTitle(parent.tr("edit_user_config") if hasattr(parent, "tr") else "Edit user_config.json")
        self.resize(980, 760)
        layout = QVBoxLayout(self)
        info = QLabel(parent.tr("edit_json_info") if hasattr(parent, "tr") else "Edit the JSON manually. Save only valid JSON objects.")
        layout.addWidget(info)
        self.editor = QTextEdit()
        self.editor.setPlainText(config_text)
        layout.addWidget(self.editor)
        self.error_label = QLabel("")
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._parsed = None

    def _validate_and_accept(self):
        try:
            data = json.loads(self.editor.toPlainText())
            if not isinstance(data, dict):
                raise ValueError(self.parent().tr("invalid_json_object") if self.parent() and hasattr(self.parent(), "tr") else "The root JSON value must be an object/dictionary.")
        except Exception as exc:
            label = self.parent().tr("invalid_json") if self.parent() and hasattr(self.parent(), "tr") else "Invalid JSON"
            self.error_label.setText(f"{label}: {exc}")
            return
        self._parsed = data
        self.accept()

    def parsed_config(self):
        return self._parsed


class MainWindow(QMainWindow):
    def __init__(self, project_root: Path):
        super().__init__()
        self.project_root = project_root
        self.cfg = load_config(project_root)
        self.log_buffer: list[str] = []
        self.current_lang = self.cfg.get("language", "en")
        self._loading_ui = False
        self.dataset_thread = None
        self.training_thread = None
        self.dataset_worker = None
        self.training_worker = None
        self.training_queue: list[dict] = self._normalize_training_queue(self.cfg.get("training_queue", []))
        self.queue_running = False
        self.current_queue_index: int | None = None
        self.current_training_cfg: dict | None = None
        self.stop_requested = False
        self._updating_dataset_table = False
        self.setWindowTitle(f"{self.tr('app_title')} {APP_VERSION}")
        for icon_path in [self.project_root / "app" / "assets" / "app_icon.ico", self.project_root / "app" / "assets" / "app_icon.png"]:
            if icon_path.exists():
                self.setWindowIcon(QIcon(str(icon_path)))
                break
        self._build_ui()
        self._apply_window_defaults()
        self._load_config_into_ui()
        self.refresh_asset_status()
        self.refresh_dataset_table()
        self.pending_queue_resume = False
        self.refresh_queue_table()
        self._apply_theme()
        self._apply_tooltips()

    def tr(self, key: str, default: str | None = None) -> str:
        return get_strings(self.current_lang).get(key, default or ENGLISH_STRINGS.get(key, key))

    def _icon_text(self, symbol: str, text: str) -> str:
        return f"{symbol}  {text}".strip() if text else symbol

    def _apply_window_defaults(self):
        screen = QApplication.primaryScreen()
        if screen is None:
            self.resize(1120, 760)
            self.setMinimumSize(760, 520)
            return
        geometry = screen.availableGeometry()
        width = max(880, min(int(geometry.width() * 0.82), geometry.width() - 36))
        height = max(620, min(int(geometry.height() * 0.82), geometry.height() - 48))
        self.resize(width, height)
        self.setMinimumSize(760, 520)

    def _prepare_scroll_tab(self, tab: QWidget) -> QVBoxLayout:
        tab.setObjectName("TabPage")
        outer = QVBoxLayout(tab)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        content = QWidget()
        content.setObjectName("ScrollPage")
        content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        content.setMinimumWidth(760)
        scroll.setWidget(content)
        outer.addWidget(scroll)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        return layout

    def _restore_log_buffer(self):
        if hasattr(self, "log_text"):
            self.log_text.setPlainText("\n".join(self.log_buffer))

    def _rebuild_ui(self):
        self.sync_config_from_ui()
        current_tab = self.tabs.currentIndex() if hasattr(self, "tabs") else 0
        old = self.takeCentralWidget()
        if old is not None:
            old.deleteLater()
        self._build_ui()
        self._load_config_into_ui()
        self.refresh_asset_status()
        self.refresh_dataset_table()
        self.refresh_queue_table()
        self._apply_theme()
        self._apply_tooltips()
        self._restore_log_buffer()
        if self.training_worker:
            self.start_train_btn.setEnabled(False)
            self.stop_train_btn.setEnabled(True)
            self.queue_start_btn.setEnabled(False)
            self.training_status_label.setText(self.tr("training_running"))
        if hasattr(self, "tabs"):
            self.tabs.setCurrentIndex(min(current_tab, self.tabs.count() - 1))

    def _apply_theme(self):
        appearance = self.cfg.get("appearance", "dark")
        app = QApplication.instance()
        if app is not None:
            app.setStyle("Fusion")
            app.setStyleSheet(get_stylesheet(appearance))

    def _apply_tooltips(self):
        mapping = {
            getattr(self, "lang_combo", None): "tooltip_language",
            getattr(self, "workspace_edit", None): "tooltip_workspace",
            getattr(self, "source_folder_edit", None): "tooltip_source_folder",
            getattr(self, "dataset_name_edit", None): "tooltip_dataset_name",
            getattr(self, "dataset_dir_edit", None): "tooltip_dataset_dir",
            getattr(self, "output_dir_edit", None): "tooltip_output_dir",
            getattr(self, "base_model_dir_edit", None): "tooltip_base_model_dir",
            getattr(self, "resolution_combo", None): "tooltip_resolution",
            getattr(self, "crop_mode_combo", None): "tooltip_crop_mode",
            getattr(self, "caption_prefix_edit", None): "tooltip_caption_prefix",
            getattr(self, "caption_suffix_edit", None): "tooltip_caption_suffix",
            getattr(self, "make_captions_cb", None): "tooltip_make_captions",
            getattr(self, "import_btn", None): "tooltip_import",
            getattr(self, "rebuild_metadata_btn", None): "tooltip_prepare_dataset",
            getattr(self, "run_name_edit", None): "tooltip_run_name",
            getattr(self, "training_preset_combo", None): "tooltip_training_preset",
            getattr(self, "apply_preset_btn", None): "tooltip_apply_preset",
            getattr(self, "preset_hint_label", None): "tooltip_preset_hint",
            getattr(self, "training_mode_combo", None): "tooltip_training_mode",
            getattr(self, "train_batch_spin", None): "tooltip_batch_size",
            getattr(self, "grad_accum_spin", None): "tooltip_grad_accum",
            getattr(self, "rank_spin", None): "tooltip_rank",
            getattr(self, "lr_edit", None): "tooltip_learning_rate",
            getattr(self, "text_encoder_lr_edit", None): "tooltip_text_encoder_lr",
            getattr(self, "lr_scheduler_combo", None): "tooltip_scheduler",
            getattr(self, "max_steps_spin", None): "tooltip_max_steps",
            getattr(self, "save_steps_spin", None): "tooltip_save_steps",
            getattr(self, "mixed_precision_combo", None): "tooltip_mixed_precision",
            getattr(self, "train_text_encoder_cb", None): "tooltip_train_text_encoder",
            getattr(self, "gradient_checkpointing_cb", None): "tooltip_gradient_checkpointing",
            getattr(self, "export_pt_cb", None): "tooltip_export_pt",
            getattr(self, "embedding_placeholder_edit", None): "tooltip_placeholder_token",
            getattr(self, "embedding_initializer_edit", None): "tooltip_initializer_token",
            getattr(self, "embedding_property_combo", None): "tooltip_learnable_property",
            getattr(self, "embedding_num_vectors_spin", None): "tooltip_num_vectors",
            getattr(self, "embedding_repeats_spin", None): "tooltip_repeats",
            getattr(self, "embedding_resolution_spin", None): "tooltip_embedding_resolution",
            getattr(self, "queue_table", None): "tooltip_queue_table",
            getattr(self, "queue_add_btn", None): "tooltip_add_queue",
            getattr(self, "queue_remove_btn", None): "tooltip_remove_queue",
            getattr(self, "queue_up_btn", None): "tooltip_move_up",
            getattr(self, "queue_down_btn", None): "tooltip_move_down",
            getattr(self, "queue_start_btn", None): "tooltip_start_queue",
            getattr(self, "queue_clear_btn", None): "tooltip_clear_queue",
            getattr(self, "base_model_repo_edit", None): "tooltip_base_model_repo",
            getattr(self, "base_model_variant_edit", None): "tooltip_base_model_variant",
            getattr(self, "blip_model_dir_edit", None): "tooltip_blip_model_dir",
            getattr(self, "blip_prompt_edit", None): "tooltip_blip_prompt",
            getattr(self, "blip_style_combo", None): "tooltip_caption_style",
            getattr(self, "blip_max_tokens_spin", None): "tooltip_blip_max_new_tokens",
            getattr(self, "blip_min_tokens_spin", None): "tooltip_blip_min_new_tokens",
            getattr(self, "blip_num_beams_spin", None): "tooltip_blip_num_beams",
            getattr(self, "blip_no_repeat_spin", None): "tooltip_blip_no_repeat_ngram",
            getattr(self, "blip_repetition_penalty_spin", None): "tooltip_blip_repetition_penalty",
            getattr(self, "diffusers_dir_edit", None): "tooltip_diffusers_dir",
            getattr(self, "asset_status_text", None): "tooltip_asset_status",
            getattr(self, "refresh_assets_btn", None): "tooltip_refresh_asset_status",
            getattr(self, "edit_config_btn", None): "tooltip_edit_config",
            getattr(self, "open_config_folder_btn", None): "tooltip_open_config_folder",
            getattr(self, "appearance_combo", None): "tooltip_appearance",
            getattr(self, "dataset_table", None): "tooltip_dataset_table",
            getattr(self, "rotate_left_btn", None): "tooltip_rotate_left",
            getattr(self, "rotate_right_btn", None): "tooltip_rotate_right",
            getattr(self, "recaption_btn", None): "tooltip_recaption_selected",
            getattr(self, "log_text", None): "tooltip_logs",
            getattr(self, "training_progress", None): "tooltip_training_progress",
        }
        for widget, key in mapping.items():
            if widget is not None:
                widget.setToolTip(self.tr(key))

    def _update_training_progress_from_log(self, line: str):
        if not hasattr(self, "training_progress"):
            return
        match = re.search(r"(?:Steps?:.*?)?(\d+)\s*/\s*(\d+)", line)
        if match:
            current = int(match.group(1))
            total = int(match.group(2))
            if total > 0 and current <= total:
                self.training_progress.setRange(0, total)
                self.training_progress.setValue(current)
                self.training_progress.setFormat(f"{current}/{total} ({int(current * 100 / max(total,1))}%)")
                if hasattr(self, "training_status_label"):
                    self.training_status_label.setText(self.tr("training_running"))


    def _normalize_training_queue(self, raw_queue) -> list[dict]:
        normalized = []
        if not isinstance(raw_queue, list):
            return normalized
        for item in raw_queue:
            if not isinstance(item, dict):
                continue
            cfg = item.get("cfg")
            if not isinstance(cfg, dict):
                continue
            normalized.append({
                "cfg": cfg.copy(),
                "status": str(item.get("status", "Pending")),
            })
        return normalized

    def _queue_for_storage(self) -> list[dict]:
        return [
            {"cfg": item.get("cfg", {}).copy(), "status": item.get("status", "Pending")}
            for item in self.training_queue
            if isinstance(item, dict) and isinstance(item.get("cfg"), dict)
        ]

    def _save_all_state(self):
        self.cfg["training_queue"] = self._queue_for_storage()
        save_config(self.project_root, self.cfg)

    def _apply_loaded_config_to_ui(self):
        self._load_config_into_ui()
        self.refresh_asset_status()
        self.refresh_dataset_table()
        self.refresh_queue_table()

    def _build_ui(self):
        root = QWidget()
        root.setObjectName("AppRoot")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(10)
        self.header_title_label = QLabel(f"<b>{self._icon_text('🧪', APP_NAME)}</b> {APP_VERSION}")
        self.lang_combo = QComboBox()
        for code, label in language_options():
            self.lang_combo.addItem(label, code)
        self.lang_combo.currentIndexChanged.connect(self.on_language_changed)
        self.lang_label = QLabel(self.tr("language"))
        header.addWidget(self.header_title_label)
        header.addStretch(1)
        header.addWidget(self.lang_label)
        header.addWidget(self.lang_combo)
        outer.addLayout(header)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setUsesScrollButtons(True)
        outer.addWidget(self.tabs)

        self.workspace_tab = QWidget()
        self.tools_tab = QWidget()
        self.training_tab = QWidget()
        self.settings_tab = QWidget()
        self.logs_tab = QWidget()

        self.tabs.addTab(self.workspace_tab, self._icon_text("🗂️", self.tr("workspace")))
        self.tabs.addTab(self.tools_tab, self._icon_text("🖼️", self.tr("dataset_tools")))
        self.tabs.addTab(self.training_tab, self._icon_text("🚀", self.tr("training")))
        self.tabs.addTab(self.settings_tab, self._icon_text("⚙️", self.tr("settings")))
        self.tabs.addTab(self.logs_tab, self._icon_text("📝", self.tr("logs")))

        self._build_workspace_tab()
        self._build_tools_tab()
        self._build_training_tab()
        self._build_settings_tab()
        self._build_logs_tab()

    def _build_workspace_tab(self):
        layout = self._prepare_scroll_tab(self.workspace_tab)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)

        paths_box = QGroupBox(self.tr("paths"))
        paths_form = QFormLayout(paths_box)
        paths_form.setHorizontalSpacing(12)
        paths_form.setVerticalSpacing(10)

        self.workspace_edit = QLineEdit()
        self.source_folder_edit = QLineEdit()
        self.dataset_name_edit = QLineEdit()
        self.dataset_dir_edit = QLineEdit()
        self.output_dir_edit = QLineEdit()
        self.base_model_dir_edit = QLineEdit()

        for edit in [
            self.workspace_edit,
            self.source_folder_edit,
            self.dataset_name_edit,
            self.dataset_dir_edit,
            self.output_dir_edit,
            self.base_model_dir_edit,
        ]:
            edit.editingFinished.connect(self.sync_config_from_ui)

        paths_form.addRow(*self._path_row(self.tr("workspace"), self.workspace_edit, folder=True))
        paths_form.addRow(*self._path_row(self.tr("source_folder"), self.source_folder_edit, folder=True))
        paths_form.addRow(self.tr("dataset_name"), self.dataset_name_edit)
        paths_form.addRow(*self._path_row(self.tr("dataset_dir"), self.dataset_dir_edit, folder=True))
        paths_form.addRow(*self._path_row(self.tr("output_dir"), self.output_dir_edit, folder=True))
        paths_form.addRow(*self._path_row(self.tr("base_model_dir"), self.base_model_dir_edit, folder=True))
        left_layout.addWidget(paths_box)

        source_buttons = QHBoxLayout()
        source_buttons.setContentsMargins(0, 8, 0, 0)
        source_buttons.setSpacing(8)
        self.add_source_images_btn = QPushButton(self._icon_text("➕", self.tr("add_source_images")))
        self.add_source_images_btn.clicked.connect(self.add_source_images)
        self.open_source_btn = QPushButton(self._icon_text("📂", self.tr("open_source_folder")))
        self.open_source_btn.clicked.connect(lambda: open_in_file_manager(Path(self.source_folder_edit.text())))
        source_buttons.addWidget(self.add_source_images_btn)
        source_buttons.addWidget(self.open_source_btn)
        source_buttons.addStretch(1)
        left_layout.addLayout(source_buttons)
        left_layout.addStretch(1)

        right = QWidget()
        right_layout = QVBoxLayout(right)

        preview_box = QGroupBox(self.tr("prepared_images"))
        preview_layout = QVBoxLayout(preview_box)
        self.dataset_table = QTableWidget(0, 4)
        self.dataset_table.setHorizontalHeaderLabels([self.tr("preview"), self.tr("image"), self.tr("caption"), self.tr("caption_file")])
        self.dataset_table.setAlternatingRowColors(True)
        self.dataset_table.setWordWrap(True)
        self.dataset_table.setIconSize(QSize(96, 96))
        self.dataset_table.verticalHeader().setVisible(False)
        self.dataset_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.dataset_table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
            | QAbstractItemView.EditTrigger.SelectedClicked
        )
        self.dataset_table.itemChanged.connect(self.on_dataset_item_changed)
        header = self.dataset_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        preview_layout.addWidget(self.dataset_table)

        preview_buttons = QHBoxLayout()
        preview_buttons.setContentsMargins(0, 8, 0, 0)
        preview_buttons.setSpacing(8)
        self.rotate_left_btn = QPushButton(self._icon_text("↶", self.tr("rotate_left")))
        self.rotate_right_btn = QPushButton(self._icon_text("↷", self.tr("rotate_right")))
        self.recaption_btn = QPushButton(self._icon_text("🪄", self.tr("recaption_selected")))
        self.rotate_left_btn.clicked.connect(lambda: self.rotate_selected_dataset_image(-90))
        self.rotate_right_btn.clicked.connect(lambda: self.rotate_selected_dataset_image(90))
        self.recaption_btn.clicked.connect(self.recaption_selected_dataset_image)
        preview_buttons.addWidget(self.rotate_left_btn)
        preview_buttons.addWidget(self.rotate_right_btn)
        preview_buttons.addWidget(self.recaption_btn)
        preview_buttons.addStretch(1)
        preview_layout.addLayout(preview_buttons)
        right_layout.addWidget(preview_box)

        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 8, 0, 0)
        buttons.setSpacing(8)
        self.open_dataset_btn = QPushButton(self._icon_text("📁", self.tr("open_dataset_folder")))
        self.open_dataset_btn.clicked.connect(lambda: open_in_file_manager(Path(self.dataset_dir_edit.text())))
        self.open_output_btn = QPushButton(self._icon_text("📦", self.tr("open_output_folder")))
        self.open_output_btn.clicked.connect(lambda: open_in_file_manager(Path(self.output_dir_edit.text())))
        buttons.addWidget(self.open_dataset_btn)
        buttons.addWidget(self.open_output_btn)
        buttons.addStretch(1)
        right_layout.addLayout(buttons)

        left.setMinimumWidth(280)
        right.setMinimumWidth(420)
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setChildrenCollapsible(False)
        splitter.setSizes([360, 820])
        layout.addWidget(splitter)

    def _build_tools_tab(self):
        layout = self._prepare_scroll_tab(self.tools_tab)

        box = QGroupBox(self.tr("batch_import_preprocessing"))
        form = QGridLayout(box)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(10)

        self.simple_mode_cb = QCheckBox(self.tr("simple_mode"))
        self.simple_mode_cb.setChecked(True)

        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(list(RESOLUTION_PRESETS.keys()))
        self.resolution_combo.currentTextChanged.connect(self.sync_config_from_ui)

        self.crop_mode_combo = QComboBox()
        self.crop_mode_combo.addItems(["center", "smart", "pad"])
        self.crop_mode_combo.currentTextChanged.connect(self.sync_config_from_ui)

        self.caption_prefix_edit = QLineEdit()
        self.caption_suffix_edit = QLineEdit()
        self.caption_prefix_edit.editingFinished.connect(self.sync_config_from_ui)
        self.caption_suffix_edit.editingFinished.connect(self.sync_config_from_ui)

        self.make_captions_cb = QCheckBox(self.tr("caption_images"))
        self.make_captions_cb.setChecked(bool(self.cfg.get("make_captions", True)))

        form.addWidget(self.simple_mode_cb, 0, 0, 1, 2)
        form.addWidget(QLabel(self.tr("target_resolution")), 1, 0)
        form.addWidget(self.resolution_combo, 1, 1)
        form.addWidget(QLabel(self.tr("crop_mode")), 2, 0)
        form.addWidget(self.crop_mode_combo, 2, 1)
        form.addWidget(QLabel(self.tr("caption_prefix")), 3, 0)
        form.addWidget(self.caption_prefix_edit, 3, 1)
        form.addWidget(QLabel(self.tr("caption_suffix")), 4, 0)
        form.addWidget(self.caption_suffix_edit, 4, 1)
        form.addWidget(self.make_captions_cb, 5, 0, 1, 2)

        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 10, 0, 2)
        buttons.setSpacing(10)
        self.import_btn = QPushButton(self._icon_text("🛠️", self.tr("import_images")))
        self.import_btn.clicked.connect(self.start_import)
        self.rebuild_metadata_btn = QPushButton(self._icon_text("🧾", self.tr("prepare_dataset")))
        self.rebuild_metadata_btn.clicked.connect(self.rebuild_metadata)
        self.tools_add_source_images_btn = QPushButton(self._icon_text("➕", self.tr("add_source_images")))
        self.tools_add_source_images_btn.clicked.connect(self.add_source_images)
        buttons.addWidget(self.tools_add_source_images_btn)
        buttons.addWidget(self.import_btn)
        buttons.addWidget(self.rebuild_metadata_btn)
        buttons.addStretch(1)

        self.dataset_progress = QProgressBar()
        self.dataset_progress.setValue(0)

        tips = QTextEdit()
        tips.setReadOnly(True)
        tips.setPlainText(self.tr("simple_workflow"))

        layout.addWidget(box)
        layout.addLayout(buttons)
        layout.addWidget(self.dataset_progress)
        layout.addWidget(tips)

    def _build_training_tab(self):
        layout = self._prepare_scroll_tab(self.training_tab)

        preset_box = QGroupBox(self.tr("preset_profile"))
        preset_layout = QGridLayout(preset_box)
        preset_layout.setHorizontalSpacing(14)
        preset_layout.setVerticalSpacing(8)
        self.training_preset_combo = QComboBox()
        for key, preset in VRAM_TRAINING_PRESETS.items():
            label_key = "custom_preset" if key == "custom" else None
            label = self.tr(label_key) if label_key else preset["label"]
            self.training_preset_combo.addItem(label, key)
        self.training_preset_combo.currentIndexChanged.connect(self.on_training_preset_changed)
        self.apply_preset_btn = QPushButton(self._icon_text('✨', self.tr('apply_preset')))
        self.apply_preset_btn.clicked.connect(self.apply_selected_training_preset)
        self.preset_hint_label = QLabel()
        self.preset_hint_label.setWordWrap(True)
        self.preset_hint_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        preset_layout.addWidget(QLabel(self.tr("preset_profile")), 0, 0)
        preset_layout.addWidget(self.training_preset_combo, 0, 1)
        preset_layout.addWidget(self.apply_preset_btn, 0, 2)
        preset_layout.addWidget(QLabel(self.tr("preset_hint")), 1, 0, Qt.AlignmentFlag.AlignTop)
        preset_layout.addWidget(self.preset_hint_label, 1, 1, 1, 2)
        layout.addWidget(preset_box)

        top = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        box = QGroupBox(self.tr("training"))
        form = QGridLayout(box)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(10)

        self.run_name_edit = QLineEdit()
        self.training_mode_combo = QComboBox()
        self.training_mode_combo.addItems(["lora", "embedding"])
        self.train_batch_spin = QSpinBox()
        self.train_batch_spin.setRange(1, 64)
        self.grad_accum_spin = QSpinBox()
        self.grad_accum_spin.setRange(1, 128)
        self.rank_spin = QSpinBox()
        self.rank_spin.setRange(1, 256)
        self.max_steps_spin = QSpinBox()
        self.max_steps_spin.setRange(1, 500000)
        self.save_steps_spin = QSpinBox()
        self.save_steps_spin.setRange(1, 100000)
        self.lr_edit = QLineEdit()
        self.text_encoder_lr_edit = QLineEdit()
        self.mixed_precision_combo = QComboBox()
        self.mixed_precision_combo.addItems(["no", "fp16", "bf16"])
        self.lr_scheduler_combo = QComboBox()
        self.lr_scheduler_combo.addItems(["constant", "linear", "cosine"])
        self.train_text_encoder_cb = QCheckBox(self.tr("train_text_encoder"))
        self.gradient_checkpointing_cb = QCheckBox(self.tr("gradient_checkpointing"))
        self.export_pt_cb = QCheckBox(self.tr("export_pt"))

        self.embedding_placeholder_edit = QLineEdit()
        self.embedding_initializer_edit = QLineEdit()
        self.embedding_property_combo = QComboBox()
        self.embedding_property_combo.addItems(["object", "style"])
        self.embedding_num_vectors_spin = QSpinBox()
        self.embedding_num_vectors_spin.setRange(1, 16)
        self.embedding_repeats_spin = QSpinBox()
        self.embedding_repeats_spin.setRange(1, 10000)
        self.embedding_resolution_spin = QSpinBox()
        self.embedding_resolution_spin.setRange(64, 2048)
        self.embedding_resolution_spin.setSingleStep(64)

        controls = [
            self.run_name_edit,
            self.training_mode_combo,
            self.train_batch_spin,
            self.grad_accum_spin,
            self.rank_spin,
            self.max_steps_spin,
            self.save_steps_spin,
            self.lr_edit,
            self.text_encoder_lr_edit,
            self.mixed_precision_combo,
            self.lr_scheduler_combo,
            self.train_text_encoder_cb,
            self.gradient_checkpointing_cb,
            self.export_pt_cb,
            self.embedding_placeholder_edit,
            self.embedding_initializer_edit,
            self.embedding_property_combo,
            self.embedding_num_vectors_spin,
            self.embedding_repeats_spin,
            self.embedding_resolution_spin,
        ]
        for control in controls:
            if isinstance(control, QLineEdit):
                control.editingFinished.connect(self.sync_config_from_ui)
            elif isinstance(control, QComboBox):
                control.currentTextChanged.connect(self.sync_config_from_ui)
            elif isinstance(control, QSpinBox):
                control.valueChanged.connect(self.sync_config_from_ui)
            elif isinstance(control, QCheckBox):
                control.toggled.connect(self.sync_config_from_ui)

        row = 0
        form.addWidget(QLabel(self.tr("run_name")), row, 0); form.addWidget(self.run_name_edit, row, 1); row += 1
        form.addWidget(QLabel(self.tr("training_mode")), row, 0); form.addWidget(self.training_mode_combo, row, 1); row += 1
        form.addWidget(QLabel(self.tr("batch_size")), row, 0); form.addWidget(self.train_batch_spin, row, 1); row += 1
        form.addWidget(QLabel(self.tr("gradient_accumulation")), row, 0); form.addWidget(self.grad_accum_spin, row, 1); row += 1
        form.addWidget(QLabel(self.tr("lora_rank")), row, 0); form.addWidget(self.rank_spin, row, 1); row += 1
        form.addWidget(QLabel(self.tr("learning_rate")), row, 0); form.addWidget(self.lr_edit, row, 1); row += 1
        form.addWidget(QLabel(self.tr("text_encoder_lr")), row, 0); form.addWidget(self.text_encoder_lr_edit, row, 1); row += 1
        form.addWidget(QLabel(self.tr("lr_scheduler")), row, 0); form.addWidget(self.lr_scheduler_combo, row, 1); row += 1
        form.addWidget(QLabel(self.tr("max_train_steps")), row, 0); form.addWidget(self.max_steps_spin, row, 1); row += 1
        form.addWidget(QLabel(self.tr("save_every")), row, 0); form.addWidget(self.save_steps_spin, row, 1); row += 1
        form.addWidget(QLabel(self.tr("mixed_precision")), row, 0); form.addWidget(self.mixed_precision_combo, row, 1); row += 1
        form.addWidget(self.train_text_encoder_cb, row, 0, 1, 2); row += 1
        form.addWidget(self.gradient_checkpointing_cb, row, 0, 1, 2); row += 1
        form.addWidget(self.export_pt_cb, row, 0, 1, 2); row += 1

        emb_box = QGroupBox(self.tr("embedding_textual_inversion"))
        emb_form = QFormLayout(emb_box)
        emb_form.addRow(self.tr("placeholder_token"), self.embedding_placeholder_edit)
        emb_form.addRow(self.tr("initializer_token"), self.embedding_initializer_edit)
        emb_form.addRow(self.tr("learnable_property"), self.embedding_property_combo)
        emb_form.addRow(self.tr("num_vectors"), self.embedding_num_vectors_spin)
        emb_form.addRow(self.tr("repeats"), self.embedding_repeats_spin)
        emb_form.addRow(self.tr("embedding_resolution"), self.embedding_resolution_spin)

        direct_buttons = QHBoxLayout()
        direct_buttons.setContentsMargins(0, 8, 0, 0)
        direct_buttons.setSpacing(8)
        self.start_train_btn = QPushButton(self._icon_text("▶️", self.tr("start_training")))
        self.stop_train_btn = QPushButton(self._icon_text("⏹️", self.tr("stop_training")))
        self.start_train_btn.clicked.connect(self.start_training)
        self.stop_train_btn.clicked.connect(self.stop_training)
        self.stop_train_btn.setEnabled(False)
        direct_buttons.addWidget(self.start_train_btn)
        direct_buttons.addWidget(self.stop_train_btn)
        direct_buttons.addStretch(1)

        self.training_progress_box = QGroupBox(self.tr("training_progress"))
        training_progress_layout = QVBoxLayout(self.training_progress_box)
        self.training_progress = QProgressBar()
        self.training_progress.setRange(0, 100)
        self.training_progress.setValue(0)
        self.training_progress.setFormat(self.tr("training_idle"))
        self.training_status_label = QLabel(self.tr("ready"))
        training_progress_layout.addWidget(self.training_progress)
        training_progress_layout.addWidget(self.training_status_label)

        left_layout.addWidget(box)
        left_layout.addWidget(emb_box)
        left_layout.addLayout(direct_buttons)
        left_layout.addWidget(self.training_progress_box)
        left_layout.addStretch(1)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        queue_box = QGroupBox(self.tr("training_queue"))
        queue_layout = QVBoxLayout(queue_box)
        self.queue_table = QTableWidget(0, 5)
        self.queue_table.setHorizontalHeaderLabels([self.tr("run"), self.tr("mode"), self.tr("dataset"), self.tr("output"), self.tr("status")])
        self.queue_table.setAlternatingRowColors(True)
        self.queue_table.verticalHeader().setVisible(False)
        self.queue_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.queue_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        queue_header = self.queue_table.horizontalHeader()
        queue_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        queue_header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        queue_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        queue_header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        queue_header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        queue_layout.addWidget(self.queue_table)

        queue_buttons1 = QHBoxLayout()
        queue_buttons1.setContentsMargins(0, 8, 0, 0)
        queue_buttons1.setSpacing(8)
        self.queue_add_btn = QPushButton(self._icon_text("➕", self.tr("add_current_job")))
        self.queue_remove_btn = QPushButton(self._icon_text("🗑️", self.tr("remove_selected")))
        self.queue_up_btn = QPushButton(self._icon_text("⬆️", self.tr("move_up")))
        self.queue_down_btn = QPushButton(self._icon_text("⬇️", self.tr("move_down")))
        self.queue_add_btn.clicked.connect(self.add_current_job_to_queue)
        self.queue_remove_btn.clicked.connect(self.remove_selected_queue_job)
        self.queue_up_btn.clicked.connect(lambda: self.move_selected_queue_job(-1))
        self.queue_down_btn.clicked.connect(lambda: self.move_selected_queue_job(1))
        queue_buttons1.addWidget(self.queue_add_btn)
        queue_buttons1.addWidget(self.queue_remove_btn)
        queue_buttons1.addWidget(self.queue_up_btn)
        queue_buttons1.addWidget(self.queue_down_btn)
        queue_buttons1.addStretch(1)

        queue_buttons2 = QHBoxLayout()
        queue_buttons2.setContentsMargins(0, 8, 0, 0)
        queue_buttons2.setSpacing(8)
        self.queue_start_btn = QPushButton(self._icon_text("🚀", self.tr("start_queue")))
        self.queue_clear_btn = QPushButton(self._icon_text("♻️", self.tr("clear_queue")))
        self.queue_start_btn.clicked.connect(self.start_training_queue)
        self.queue_clear_btn.clicked.connect(self.clear_queue)
        queue_buttons2.addWidget(self.queue_start_btn)
        queue_buttons2.addWidget(self.queue_clear_btn)
        queue_buttons2.addStretch(1)

        queue_layout.addLayout(queue_buttons1)
        queue_layout.addLayout(queue_buttons2)
        right_layout.addWidget(queue_box)
        right_layout.addStretch(1)

        left.setMinimumWidth(320)
        right.setMinimumWidth(380)
        top.addWidget(left)
        top.addWidget(right)
        top.setChildrenCollapsible(False)
        top.setSizes([600, 520])
        layout.addWidget(top)

    def _build_settings_tab(self):
        layout = self._prepare_scroll_tab(self.settings_tab)
        box = QGroupBox(self.tr("offline_assets"))
        form = QFormLayout(box)

        self.base_model_repo_edit = QLineEdit()
        self.base_model_variant_edit = QLineEdit()
        self.blip_model_dir_edit = QLineEdit()
        self.diffusers_dir_edit = QLineEdit()
        self.blip_prompt_edit = QLineEdit()
        self.blip_style_combo = QComboBox()
        self.blip_style_combo.addItem(self.tr("caption_style_conservative"), "conservative")
        self.blip_style_combo.addItem(self.tr("caption_style_detailed"), "detailed")
        self.blip_max_tokens_spin = QSpinBox()
        self.blip_max_tokens_spin.setRange(4, 128)
        self.blip_min_tokens_spin = QSpinBox()
        self.blip_min_tokens_spin.setRange(0, 64)
        self.blip_num_beams_spin = QSpinBox()
        self.blip_num_beams_spin.setRange(1, 8)
        self.blip_no_repeat_spin = QSpinBox()
        self.blip_no_repeat_spin.setRange(0, 6)
        self.blip_repetition_penalty_spin = QDoubleSpinBox()
        self.blip_repetition_penalty_spin.setRange(1.0, 2.5)
        self.blip_repetition_penalty_spin.setDecimals(2)
        self.blip_repetition_penalty_spin.setSingleStep(0.05)
        self.appearance_combo = QComboBox()
        self.appearance_combo.addItem(self.tr("theme_dark"), "dark")
        self.appearance_combo.addItem(self.tr("theme_light"), "light")
        self.appearance_combo.currentIndexChanged.connect(self.on_appearance_changed)
        self.asset_status_text = QTextEdit()
        self.asset_status_text.setReadOnly(True)
        self.asset_status_text.setMinimumHeight(140)

        for edit in [self.base_model_repo_edit, self.base_model_variant_edit, self.blip_model_dir_edit, self.diffusers_dir_edit, self.blip_prompt_edit]:
            edit.editingFinished.connect(self.sync_config_from_ui)
        for combo in [self.blip_style_combo]:
            combo.currentIndexChanged.connect(self.sync_config_from_ui)
        for spin in [self.blip_max_tokens_spin, self.blip_min_tokens_spin, self.blip_num_beams_spin, self.blip_no_repeat_spin, self.blip_repetition_penalty_spin]:
            spin.valueChanged.connect(self.sync_config_from_ui)

        form.addRow(self.tr("theme"), self.appearance_combo)
        form.addRow(self.tr("base_model_repo"), self.base_model_repo_edit)
        form.addRow(self.tr("base_model_variant"), self.base_model_variant_edit)
        form.addRow(*self._path_row(self.tr("blip_model_dir"), self.blip_model_dir_edit, folder=True))
        form.addRow(*self._path_row(self.tr("diffusers_dir"), self.diffusers_dir_edit, folder=True))
        form.addRow(self.tr("blip_prompt"), self.blip_prompt_edit)
        form.addRow(self.tr("caption_style"), self.blip_style_combo)
        form.addRow(self.tr("blip_max_new_tokens"), self.blip_max_tokens_spin)
        form.addRow(self.tr("blip_min_new_tokens"), self.blip_min_tokens_spin)
        form.addRow(self.tr("blip_num_beams"), self.blip_num_beams_spin)
        form.addRow(self.tr("blip_no_repeat_ngram"), self.blip_no_repeat_spin)
        form.addRow(self.tr("blip_repetition_penalty"), self.blip_repetition_penalty_spin)
        form.addRow(self.tr("download_status"), self.asset_status_text)

        self.refresh_assets_btn = QPushButton(self._icon_text("🔄", self.tr("refresh_asset_status")))
        self.refresh_assets_btn.clicked.connect(self.refresh_asset_status)
        self.edit_config_btn = QPushButton(self._icon_text("✏️", self.tr("edit_user_config")))
        self.edit_config_btn.clicked.connect(self.open_config_editor)
        self.open_config_folder_btn = QPushButton(self._icon_text("📂", self.tr("open_config_folder")))
        self.open_config_folder_btn.clicked.connect(lambda: open_in_file_manager(self.project_root))

        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 8, 0, 0)
        button_row.setSpacing(8)
        button_row.addWidget(self.refresh_assets_btn)
        button_row.addWidget(self.edit_config_btn)
        button_row.addWidget(self.open_config_folder_btn)
        button_row.addStretch(1)

        layout.addWidget(box)
        layout.addLayout(button_row)
        layout.addStretch(1)

    def _build_logs_tab(self):
        layout = self._prepare_scroll_tab(self.logs_tab)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        self._restore_log_buffer()

    def _path_row(self, label: str, edit: QLineEdit, folder: bool = True):
        wrapper = QWidget()
        wrapper.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        row = QHBoxLayout(wrapper)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        edit.setMinimumWidth(230)
        row.addWidget(edit, 1)
        btn = QPushButton(self._icon_text("📂", self.tr("browse")))
        btn.setMinimumWidth(118)
        if folder:
            btn.clicked.connect(lambda: self.pick_folder_for(edit))
        row.addWidget(btn, 0)
        return label, wrapper

    def pick_folder_for(self, edit: QLineEdit):
        current = edit.text() or str(self.project_root)
        path = QFileDialog.getExistingDirectory(self, self.tr("browse"), current)
        if path:
            edit.setText(path)
            if edit is self.workspace_edit:
                dataset_name = self.dataset_name_edit.text().strip() or "my_dataset"
                self.dataset_dir_edit.setText(str(Path(path) / "datasets" / dataset_name))
                self.output_dir_edit.setText(str(Path(path) / "output"))
                self.source_folder_edit.setText(str(Path(path) / "imported_raw"))
                self.base_model_dir_edit.setText(str(Path(path) / "models" / "sdxl-base"))
                self.blip_model_dir_edit.setText(str(Path(path) / "models" / "blip-image-captioning-base"))
            self.sync_config_from_ui()

    def add_source_images(self):
        self.sync_config_from_ui()
        start_dir = self.source_folder_edit.text().strip() or str(self.project_root)
        files, _ = QFileDialog.getOpenFileNames(
            self,
            self.tr("choose_source_images"),
            start_dir,
            "Images (*.png *.jpg *.jpeg *.webp *.bmp)",
        )
        if not files:
            return
        source_dir = Path(self.source_folder_edit.text().strip())
        source_dir.mkdir(parents=True, exist_ok=True)
        copied = copy_images_into_folder([Path(p) for p in files], source_dir)
        self.append_log(f"Copied {len(copied)} source images into {source_dir}")
        QMessageBox.information(self, self.tr("source_images_added"), self.tr("source_images_added_text").format(count=len(copied)))

    def on_language_changed(self, _index: int):
        if self._loading_ui:
            return
        lang = self.lang_combo.currentData() or self.lang_combo.currentText().lower()
        self.current_lang = lang
        self.cfg["language"] = lang
        save_config(self.project_root, self.cfg)
        self._rebuild_ui()

    def on_appearance_changed(self, index: int):
        if self._loading_ui:
            return
        self.sync_config_from_ui()
        self._apply_theme()

    def _load_config_into_ui(self):
        self._loading_ui = True
        self.current_lang = self.cfg.get("language", "en")
        self.lang_combo.blockSignals(True)
        lang_index = self.lang_combo.findData(self.current_lang)
        if lang_index >= 0:
            self.lang_combo.setCurrentIndex(lang_index)
        self.lang_combo.blockSignals(False)
        self.workspace_edit.setText(self.cfg.get("workspace_dir", ""))
        self.source_folder_edit.setText(self.cfg.get("source_folder", ""))
        self.dataset_name_edit.setText(self.cfg.get("dataset_name", "my_dataset"))
        self.dataset_dir_edit.setText(self.cfg.get("dataset_dir", ""))
        self.output_dir_edit.setText(self.cfg.get("output_dir", ""))
        self.base_model_dir_edit.setText(self.cfg.get("base_model_dir", ""))
        self.base_model_repo_edit.setText(self.cfg.get("base_model_repo", ""))
        self.base_model_variant_edit.setText(self.cfg.get("base_model_variant", ""))
        self.blip_model_dir_edit.setText(self.cfg.get("blip_model_dir", ""))
        self.diffusers_dir_edit.setText(self.cfg.get("diffusers_dir", ""))
        self.blip_prompt_edit.setText(str(self.cfg.get("blip_prompt", "a photo of")))
        self.blip_style_combo.setCurrentIndex(max(0, self.blip_style_combo.findData(self.cfg.get("blip_caption_style", "conservative"))))
        self.blip_max_tokens_spin.setValue(int(self.cfg.get("blip_max_new_tokens", 28)))
        self.blip_min_tokens_spin.setValue(int(self.cfg.get("blip_min_new_tokens", 6)))
        self.blip_num_beams_spin.setValue(int(self.cfg.get("blip_num_beams", 3)))
        self.blip_no_repeat_spin.setValue(int(self.cfg.get("blip_no_repeat_ngram_size", 3)))
        self.blip_repetition_penalty_spin.setValue(float(self.cfg.get("blip_repetition_penalty", 1.15)))
        appearance = self.cfg.get("appearance", "dark")
        self.appearance_combo.blockSignals(True)
        idx = self.appearance_combo.findData(appearance)
        if idx >= 0:
            self.appearance_combo.setCurrentIndex(idx)
        self.appearance_combo.blockSignals(False)
        self.resolution_combo.setCurrentText(self.cfg.get("resolution_preset", list(RESOLUTION_PRESETS.keys())[0]))
        self.crop_mode_combo.setCurrentText(self.cfg.get("crop_mode", "center"))
        self.caption_prefix_edit.setText(self.cfg.get("caption_prefix", ""))
        self.caption_suffix_edit.setText(self.cfg.get("caption_suffix", ""))
        self.make_captions_cb.setChecked(bool(self.cfg.get("make_captions", True)))
        self.run_name_edit.setText(self.cfg.get("run_name", "my_sdxl_run"))
        self.training_mode_combo.setCurrentText(self.cfg.get("training_mode", "lora"))
        preset_key = self.cfg.get("training_preset", "custom")
        preset_index = self.training_preset_combo.findData(preset_key)
        if preset_index >= 0:
            self.training_preset_combo.setCurrentIndex(preset_index)
        self._update_preset_hint(preset_key)
        self.train_batch_spin.setValue(int(self.cfg.get("batch_size", 1)))
        self.grad_accum_spin.setValue(int(self.cfg.get("gradient_accumulation_steps", 1)))
        self.rank_spin.setValue(int(self.cfg.get("rank", 4)))
        self.max_steps_spin.setValue(int(self.cfg.get("max_train_steps", 1200)))
        self.save_steps_spin.setValue(int(self.cfg.get("save_steps", 500)))
        self.lr_edit.setText(str(self.cfg.get("learning_rate", "1e-4")))
        self.text_encoder_lr_edit.setText(str(self.cfg.get("text_encoder_lr", "5e-6")))
        self.mixed_precision_combo.setCurrentText(self.cfg.get("mixed_precision", "fp16"))
        self.lr_scheduler_combo.setCurrentText(self.cfg.get("lr_scheduler", "constant"))
        self.train_text_encoder_cb.setChecked(bool(self.cfg.get("train_text_encoder", False)))
        self.gradient_checkpointing_cb.setChecked(bool(self.cfg.get("gradient_checkpointing", True)))
        self.export_pt_cb.setChecked(bool(self.cfg.get("export_pt", False)))
        self.embedding_placeholder_edit.setText(self.cfg.get("embedding_placeholder_token", "<myconcept>"))
        self.embedding_initializer_edit.setText(self.cfg.get("embedding_initializer_token", "object"))
        self.embedding_property_combo.setCurrentText(self.cfg.get("embedding_learnable_property", "object"))
        self.embedding_num_vectors_spin.setValue(int(self.cfg.get("embedding_num_vectors", 1)))
        self.embedding_repeats_spin.setValue(int(self.cfg.get("embedding_repeats", 100)))
        self.embedding_resolution_spin.setValue(int(self.cfg.get("embedding_resolution", 512)))
        self._loading_ui = False

    def sync_config_from_ui(self):
        self.cfg["language"] = self.lang_combo.currentData() or self.lang_combo.currentText().lower()
        self.cfg["workspace_dir"] = self.workspace_edit.text().strip()
        self.cfg["source_folder"] = self.source_folder_edit.text().strip()
        self.cfg["dataset_name"] = self.dataset_name_edit.text().strip() or "my_dataset"
        self.cfg["dataset_dir"] = self.dataset_dir_edit.text().strip()
        self.cfg["output_dir"] = self.output_dir_edit.text().strip()
        self.cfg["base_model_dir"] = self.base_model_dir_edit.text().strip()
        self.cfg["appearance"] = self.appearance_combo.currentData() or self.appearance_combo.currentText()
        self.cfg["base_model_repo"] = self.base_model_repo_edit.text().strip()
        self.cfg["base_model_variant"] = self.base_model_variant_edit.text().strip()
        self.cfg["blip_model_dir"] = self.blip_model_dir_edit.text().strip()
        self.cfg["diffusers_dir"] = self.diffusers_dir_edit.text().strip()
        self.cfg["blip_prompt"] = self.blip_prompt_edit.text().strip() or "a photo of"
        self.cfg["blip_caption_style"] = self.blip_style_combo.currentData() or "conservative"
        self.cfg["blip_max_new_tokens"] = self.blip_max_tokens_spin.value()
        self.cfg["blip_min_new_tokens"] = self.blip_min_tokens_spin.value()
        self.cfg["blip_num_beams"] = self.blip_num_beams_spin.value()
        self.cfg["blip_no_repeat_ngram_size"] = self.blip_no_repeat_spin.value()
        self.cfg["blip_repetition_penalty"] = f"{self.blip_repetition_penalty_spin.value():.2f}"
        self.cfg["resolution_preset"] = self.resolution_combo.currentText()
        width, height = RESOLUTION_PRESETS[self.cfg["resolution_preset"]]
        self.cfg["resolution"] = width
        self.cfg["resolution_width"] = width
        self.cfg["resolution_height"] = height
        self.cfg["crop_mode"] = self.crop_mode_combo.currentText()
        self.cfg["caption_prefix"] = self.caption_prefix_edit.text().strip()
        self.cfg["caption_suffix"] = self.caption_suffix_edit.text().strip()
        self.cfg["make_captions"] = self.make_captions_cb.isChecked()
        self.cfg["run_name"] = self.run_name_edit.text().strip() or "my_sdxl_run"
        self.cfg["training_mode"] = self.training_mode_combo.currentText()
        self.cfg["training_preset"] = self.training_preset_combo.currentData() or "custom"
        self.cfg["batch_size"] = self.train_batch_spin.value()
        self.cfg["gradient_accumulation_steps"] = self.grad_accum_spin.value()
        self.cfg["rank"] = self.rank_spin.value()
        self.cfg["max_train_steps"] = self.max_steps_spin.value()
        self.cfg["save_steps"] = self.save_steps_spin.value()
        self.cfg["learning_rate"] = self.lr_edit.text().strip() or "1e-4"
        self.cfg["text_encoder_lr"] = self.text_encoder_lr_edit.text().strip() or "5e-6"
        self.cfg["mixed_precision"] = self.mixed_precision_combo.currentText()
        self.cfg["lr_scheduler"] = self.lr_scheduler_combo.currentText()
        self.cfg["train_text_encoder"] = self.train_text_encoder_cb.isChecked()
        self.cfg["gradient_checkpointing"] = self.gradient_checkpointing_cb.isChecked()
        self.cfg["export_pt"] = self.export_pt_cb.isChecked()
        self.cfg["embedding_placeholder_token"] = self.embedding_placeholder_edit.text().strip() or "<myconcept>"
        self.cfg["embedding_initializer_token"] = self.embedding_initializer_edit.text().strip() or "object"
        self.cfg["embedding_learnable_property"] = self.embedding_property_combo.currentText()
        self.cfg["embedding_num_vectors"] = self.embedding_num_vectors_spin.value()
        self.cfg["embedding_repeats"] = self.embedding_repeats_spin.value()
        self.cfg["embedding_resolution"] = self.embedding_resolution_spin.value()
        self._save_all_state()

    def on_training_preset_changed(self, _index: int):
        self._update_preset_hint(self.training_preset_combo.currentData() or "custom")
        if self._loading_ui:
            return
        self.sync_config_from_ui()

    def _update_preset_hint(self, preset_key: str):
        preset = VRAM_TRAINING_PRESETS.get(preset_key or "custom", VRAM_TRAINING_PRESETS["custom"])
        self.preset_hint_label.setText(preset.get("note", ""))

    def apply_selected_training_preset(self):
        preset_key = self.training_preset_combo.currentData() or "custom"
        preset = VRAM_TRAINING_PRESETS.get(preset_key)
        if not preset or preset_key == "custom":
            self._update_preset_hint("custom")
            self.sync_config_from_ui()
            return
        self.train_batch_spin.setValue(int(preset["batch_size"]))
        self.grad_accum_spin.setValue(int(preset["gradient_accumulation_steps"]))
        self.rank_spin.setValue(int(preset["rank"]))
        self.lr_edit.setText(str(preset["learning_rate"]))
        self.text_encoder_lr_edit.setText(str(preset["text_encoder_lr"]))
        self.max_steps_spin.setValue(int(preset["max_train_steps"]))
        self.save_steps_spin.setValue(int(preset["save_steps"]))
        self.mixed_precision_combo.setCurrentText(str(preset["mixed_precision"]))
        self.train_text_encoder_cb.setChecked(bool(preset["train_text_encoder"]))
        self.gradient_checkpointing_cb.setChecked(bool(preset["gradient_checkpointing"]))
        resolution_preset = preset.get("resolution_preset")
        if resolution_preset and resolution_preset in RESOLUTION_PRESETS:
            self.resolution_combo.setCurrentText(resolution_preset)
        self.cfg["training_preset"] = preset_key
        self._update_preset_hint(preset_key)
        self.sync_config_from_ui()
        self.append_log(f"{self.tr('preset_applied')}: {preset['label']}")

    def open_config_editor(self):
        self.sync_config_from_ui()
        dialog = ConfigEditorDialog(self, json.dumps(self.cfg, indent=2, ensure_ascii=False))
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        data = dialog.parsed_config()
        if not isinstance(data, dict):
            QMessageBox.critical(self, self.tr("invalid_json"), self.tr("invalid_json_object"))
            return
        defaults = load_config(self.project_root)
        defaults.update(data)
        if not isinstance(defaults.get("training_queue"), list):
            defaults["training_queue"] = []
        self.cfg = defaults
        self.training_queue = self._normalize_training_queue(self.cfg.get("training_queue", []))
        self._save_all_state()
        self._apply_loaded_config_to_ui()
        self.append_log("Configuration updated from user_config.json editor.")

    def append_log(self, line: str):
        self.log_buffer.append(line)
        if hasattr(self, "log_text"):
            self.log_text.append(line)
        self._update_training_progress_from_log(line)

    def _thumbnail_icon(self, path: Path) -> QIcon:
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            return QIcon()
        scaled = pixmap.scaled(96, 96, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        return QIcon(scaled)

    def refresh_dataset_table(self):
        dataset_images = list_images(Path(self.dataset_dir_edit.text()) / "images")
        self._updating_dataset_table = True
        try:
            self.dataset_table.clearContents()
            self.dataset_table.setRowCount(len(dataset_images))
            for row, path in enumerate(dataset_images):
                self.dataset_table.setRowHeight(row, 112)
                preview_item = QTableWidgetItem()
                preview_item.setIcon(self._thumbnail_icon(path))
                preview_item.setText("")
                preview_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                preview_item.setToolTip(str(path))

                image_item = QTableWidgetItem(path.name)
                image_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                image_item.setToolTip(str(path))

                caption = read_text_if_exists(path.with_suffix(".txt"))
                caption_item = QTableWidgetItem(caption)
                caption_item.setFlags(
                    Qt.ItemFlag.ItemIsEnabled
                    | Qt.ItemFlag.ItemIsSelectable
                    | Qt.ItemFlag.ItemIsEditable
                )
                caption_item.setToolTip(self.tr("tooltip_dataset_table"))

                caption_name = path.with_suffix(".txt").name if path.with_suffix(".txt").exists() else ""
                caption_file_item = QTableWidgetItem(caption_name)
                caption_file_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                caption_file_item.setToolTip(str(path.with_suffix('.txt')) if caption_name else "")

                self.dataset_table.setItem(row, 0, preview_item)
                self.dataset_table.setItem(row, 1, image_item)
                self.dataset_table.setItem(row, 2, caption_item)
                self.dataset_table.setItem(row, 3, caption_file_item)
        finally:
            self._updating_dataset_table = False

    def on_dataset_item_changed(self, item: QTableWidgetItem):
        if self._updating_dataset_table or item is None or item.column() != 2:
            return
        image_item = self.dataset_table.item(item.row(), 1)
        if image_item is None:
            return
        image_name = image_item.text().strip()
        if not image_name:
            return
        txt_path = Path(self.dataset_dir_edit.text()) / "images" / Path(image_name).with_suffix(".txt")
        caption_text = item.text().strip()
        try:
            if caption_text:
                txt_path.write_text(caption_text, encoding="utf-8")
                caption_name = txt_path.name
            else:
                if txt_path.exists():
                    txt_path.unlink()
                caption_name = ""
            self._updating_dataset_table = True
            caption_file_item = self.dataset_table.item(item.row(), 3)
            if caption_file_item is None:
                caption_file_item = QTableWidgetItem(caption_name)
                caption_file_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                self.dataset_table.setItem(item.row(), 3, caption_file_item)
            else:
                caption_file_item.setText(caption_name)
            rebuild_metadata_from_existing_images(Path(self.dataset_dir_edit.text()))
            self.append_log(f"Saved caption for {image_name}")
        except Exception as exc:
            QMessageBox.critical(self, self.tr("dataset_import_failed"), str(exc))
        finally:
            self._updating_dataset_table = False

    def _selected_dataset_image_path(self) -> Path | None:
        row = self.dataset_table.currentRow() if hasattr(self, "dataset_table") else -1
        if row < 0:
            return None
        image_item = self.dataset_table.item(row, 1)
        if image_item is None:
            return None
        image_name = image_item.text().strip()
        if not image_name:
            return None
        return Path(self.dataset_dir_edit.text()) / "images" / image_name

    def _filename_fallback_caption(self, image_path: Path) -> str:
        stem = re.sub(r"[_\-]+", " ", image_path.stem).strip()
        return format_caption_text(
            stem,
            self.caption_prefix_edit.text().strip(),
            self.caption_suffix_edit.text().strip(),
            self.cfg.get("blip_caption_style", "conservative"),
        )

    def _recaption_image_path(self, image_path: Path) -> str:
        model_dir_text = self.blip_model_dir_edit.text().strip()
        if model_dir_text:
            model_dir = Path(model_dir_text)
            if model_dir.exists():
                captioner = OfflineBlipCaptioner(
                    model_dir,
                    prompt=self.cfg.get("blip_prompt", "a photo of"),
                    style=self.cfg.get("blip_caption_style", "conservative"),
                    max_new_tokens=int(self.cfg.get("blip_max_new_tokens", 28)),
                    min_new_tokens=int(self.cfg.get("blip_min_new_tokens", 6)),
                    num_beams=int(self.cfg.get("blip_num_beams", 3)),
                    no_repeat_ngram_size=int(self.cfg.get("blip_no_repeat_ngram_size", 3)),
                    repetition_penalty=float(self.cfg.get("blip_repetition_penalty", 1.15)),
                )
                return captioner.caption(
                    image_path,
                    self.caption_prefix_edit.text().strip(),
                    self.caption_suffix_edit.text().strip(),
                )
        return self._filename_fallback_caption(image_path)

    def _write_caption_for_image(self, image_path: Path, caption_text: str):
        txt_path = image_path.with_suffix(".txt")
        caption_text = (caption_text or "").strip()
        if caption_text:
            txt_path.write_text(caption_text, encoding="utf-8")
        elif txt_path.exists():
            txt_path.unlink()
        rebuild_metadata_from_existing_images(Path(self.dataset_dir_edit.text()))

    def rotate_selected_dataset_image(self, angle: int):
        image_path = self._selected_dataset_image_path()
        if image_path is None or not image_path.exists():
            QMessageBox.information(self, self.tr("no_image_selected_title"), self.tr("no_image_selected_text"))
            return
        try:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            rotate_prepared_image(image_path, angle)
        except Exception as exc:
            QMessageBox.critical(self, self.tr("image_rotate_failed"), str(exc))
            return
        finally:
            QApplication.restoreOverrideCursor()
        self.append_log(f"Rotated prepared image: {image_path.name} ({angle}°)")
        self.refresh_dataset_table()
        # restore selection
        for row in range(self.dataset_table.rowCount()):
            item = self.dataset_table.item(row, 1)
            if item and item.text() == image_path.name:
                self.dataset_table.selectRow(row)
                break
        self.append_log("Use Re-caption selected if you want to refresh the caption after rotation.")

    def recaption_selected_dataset_image(self):
        image_path = self._selected_dataset_image_path()
        if image_path is None or not image_path.exists():
            QMessageBox.information(self, self.tr("no_image_selected_title"), self.tr("no_image_selected_text"))
            return
        try:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            caption_text = self._recaption_image_path(image_path)
            self._write_caption_for_image(image_path, caption_text)
        except Exception as exc:
            QMessageBox.critical(self, self.tr("recaption_failed_title"), str(exc))
            return
        finally:
            QApplication.restoreOverrideCursor()
        self.append_log(f"Re-captioned prepared image: {image_path.name}")
        self.refresh_dataset_table()
        for row in range(self.dataset_table.rowCount()):
            item = self.dataset_table.item(row, 1)
            if item and item.text() == image_path.name:
                self.dataset_table.selectRow(row)
                caption_item = self.dataset_table.item(row, 2)
                if caption_item is not None:
                    self.dataset_table.scrollToItem(caption_item)
                break

    def refresh_asset_status(self):
        items = {
            self.tr("base_model_dir"): Path(self.base_model_dir_edit.text()) if self.base_model_dir_edit.text() else None,
            self.tr("blip_model_dir"): Path(self.blip_model_dir_edit.text()) if self.blip_model_dir_edit.text() else None,
            self.tr("diffusers_dir"): Path(self.diffusers_dir_edit.text()) if self.diffusers_dir_edit.text() else None,
        }
        lines = []
        for name, path in items.items():
            if path and path.exists():
                lines.append(f"{name}: {self.tr('detected')} -> {path}")
            else:
                lines.append(f"{name}: {self.tr('not_found')}")
        if self.base_model_variant_edit.text().strip():
            lines.append(f"{self.tr('base_model_variant')}: {self.base_model_variant_edit.text().strip()}")
        status = torch_status()
        if status.get("ok"):
            lines.append(f"PyTorch: {self.tr('detected')} -> {status.get('version', '')}")
        else:
            lines.append(f"PyTorch: {self.tr('not_found')} -> {status.get('error', '')}")
        self.asset_status_text.setPlainText("\n".join(lines))

    def start_import(self):
        self.sync_config_from_ui()
        source = Path(self.source_folder_edit.text())
        dataset_dir = Path(self.dataset_dir_edit.text())
        if not source.exists():
            QMessageBox.warning(self, self.tr("missing_source_title"), self.tr("missing_source_text"))
            return
        dataset_dir.mkdir(parents=True, exist_ok=True)
        status = torch_status()
        if self.make_captions_cb.isChecked() and not status.get("ok"):
            self.append_log("PyTorch/BLIP captioning is not available on this system. Import will continue with filename-based fallback captions.")
        self.dataset_progress.setValue(0)
        self.import_btn.setEnabled(False)
        self.dataset_thread = QThread(self)
        target_size = RESOLUTION_PRESETS[self.resolution_combo.currentText()]
        self.dataset_worker = DatasetWorker(self.cfg.copy(), target_size, self.make_captions_cb.isChecked())
        self.dataset_worker.moveToThread(self.dataset_thread)
        self.dataset_thread.started.connect(self.dataset_worker.run)
        self.dataset_worker.progress.connect(self.on_dataset_progress)
        self.dataset_worker.log.connect(self.append_log)
        self.dataset_worker.finished.connect(self.on_dataset_finished)
        self.dataset_worker.failed.connect(self.on_dataset_failed)
        self.dataset_worker.finished.connect(self.dataset_thread.quit)
        self.dataset_worker.failed.connect(self.dataset_thread.quit)
        self.dataset_thread.start()
        self.append_log("Dataset import started. Images will be EXIF-rotated automatically and exact duplicates are skipped by CRC32.")

    def on_dataset_progress(self, current: int, total: int):
        pct = int((current / max(total, 1)) * 100)
        self.dataset_progress.setValue(pct)

    def on_dataset_finished(self, payload: dict):
        self.import_btn.setEnabled(True)
        self.dataset_progress.setValue(100)
        duplicates = int(payload.get("duplicates_skipped", 0))
        self.append_log(
            f"Dataset import finished. Images: {payload.get('total', 0)} / {payload.get('total_input', payload.get('total', 0))}, "
            f"captioned: {payload.get('captioned', 0)}, duplicates skipped: {duplicates}"
        )
        self.refresh_dataset_table()

    def on_dataset_failed(self, message: str):
        self.import_btn.setEnabled(True)
        self.append_log(f"Dataset import failed: {message}")
        QMessageBox.critical(self, self.tr("dataset_import_failed"), message)

    def rebuild_metadata(self):
        self.sync_config_from_ui()
        dataset_dir = Path(self.dataset_dir_edit.text())
        if not dataset_dir.exists():
            QMessageBox.warning(self, self.tr("missing_dataset_title"), self.tr("missing_dataset_text"))
            return
        self.dataset_thread = QThread(self)
        worker = MetadataWorker(str(dataset_dir))
        self.dataset_worker = worker
        worker.moveToThread(self.dataset_thread)
        self.dataset_thread.started.connect(worker.run)
        worker.finished.connect(lambda count: self.append_log(f"Rebuilt metadata.jsonl for {count} items."))
        worker.finished.connect(lambda _: self.refresh_dataset_table())
        worker.failed.connect(lambda msg: QMessageBox.critical(self, self.tr("metadata_rebuild_failed"), msg))
        worker.failed.connect(lambda msg: self.append_log(f"Metadata rebuild failed: {msg}"))
        worker.finished.connect(self.dataset_thread.quit)
        worker.failed.connect(self.dataset_thread.quit)
        self.dataset_thread.start()

    def _validate_training_config(self, cfg: dict) -> str | None:
        diffusers_dir = Path(cfg.get("diffusers_dir", ""))
        base_model_dir = Path(cfg.get("base_model_dir", ""))
        dataset_dir = Path(cfg.get("dataset_dir", ""))
        if not diffusers_dir.exists():
            return "The local Diffusers source folder was not found."
        if not base_model_dir.exists():
            return "The local base model folder was not found."
        if not dataset_dir.exists():
            return "The prepared dataset folder was not found."
        if cfg.get("training_mode") == "embedding" and not cfg.get("embedding_placeholder_token", "").strip():
            return "Please enter a placeholder token for embedding mode."
        status = torch_status()
        if not status.get("ok"):
            return "PyTorch could not be initialized on this Windows system. Please install the Microsoft Visual C++ Redistributable and reopen the app, or switch to a compatible PyTorch backend. Details: " + str(status.get("error", ""))
        return None

    def _current_ui_job(self) -> dict:
        self.sync_config_from_ui()
        return self.cfg.copy()

    def add_current_job_to_queue(self):
        cfg = self._current_ui_job()
        error = self._validate_training_config(cfg)
        if error:
            QMessageBox.warning(self, self.tr("cannot_queue_title"), error)
            return
        self.training_queue.append({"cfg": cfg, "status": "Pending"})
        self.refresh_queue_table()
        self.append_log(f"Queued job: {cfg['run_name']} ({cfg['training_mode']})")

    def refresh_queue_table(self):
        self.queue_table.setRowCount(len(self.training_queue))
        self.queue_table.verticalHeader().setDefaultSectionSize(30)
        for row, item in enumerate(self.training_queue):
            cfg = item["cfg"]
            self.queue_table.setItem(row, 0, QTableWidgetItem(cfg.get("run_name", "")))
            self.queue_table.setItem(row, 1, QTableWidgetItem(cfg.get("training_mode", "")))
            self.queue_table.setItem(row, 2, QTableWidgetItem(cfg.get("dataset_dir", "")))
            self.queue_table.setItem(row, 3, QTableWidgetItem(str(Path(cfg.get("output_dir", "")) / cfg.get("run_name", ""))))
            self.queue_table.setItem(row, 4, QTableWidgetItem(item.get("status", "Pending")))
        self.cfg["training_queue"] = self._queue_for_storage()
        self._save_all_state()

    def remove_selected_queue_job(self):
        row = self.queue_table.currentRow()
        if row < 0 or row >= len(self.training_queue):
            return
        if self.queue_running and row == self.current_queue_index:
            QMessageBox.warning(self, self.tr("queue_busy"), self.tr("queue_busy_remove"))
            return
        removed = self.training_queue.pop(row)
        self.refresh_queue_table()
        self.append_log(f"Removed queued job: {removed['cfg']['run_name']}")

    def move_selected_queue_job(self, offset: int):
        row = self.queue_table.currentRow()
        if row < 0:
            return
        new_row = row + offset
        if new_row < 0 or new_row >= len(self.training_queue):
            return
        if self.queue_running and row == self.current_queue_index:
            return
        self.training_queue[row], self.training_queue[new_row] = self.training_queue[new_row], self.training_queue[row]
        if self.current_queue_index == row:
            self.current_queue_index = new_row
        elif self.current_queue_index == new_row:
            self.current_queue_index = row
        self.refresh_queue_table()
        self.queue_table.selectRow(new_row)

    def clear_queue(self):
        if self.queue_running:
            QMessageBox.warning(self, self.tr("queue_busy"), self.tr("queue_busy_stop"))
            return
        self.training_queue.clear()
        self.refresh_queue_table()
        self.append_log("Queue cleared.")

    def start_training(self):
        if self.training_worker:
            QMessageBox.warning(self, self.tr("training_running_title"), self.tr("training_running_text"))
            return
        cfg = self._current_ui_job()
        error = self._validate_training_config(cfg)
        if error:
            QMessageBox.warning(self, self.tr("training_cannot_start_title"), error)
            return
        self.queue_running = False
        self.current_queue_index = None
        self._launch_training_job(cfg)

    def start_training_queue(self):
        if self.training_worker:
            QMessageBox.warning(self, self.tr("training_running_title"), self.tr("training_running_text"))
            return
        if not self.training_queue:
            QMessageBox.information(self, self.tr("queue_empty_title"), self.tr("queue_empty_text"))
            return
        self.queue_running = True
        self.stop_requested = False
        self._updating_dataset_table = False
        for item in self.training_queue:
            if item.get("status") in {"Done", "Failed", "Stopped"}:
                item["status"] = "Pending"
        self.refresh_queue_table()
        self._start_next_queued_job()

    def _start_next_queued_job(self):
        pending_index = None
        for index, item in enumerate(self.training_queue):
            if item.get("status") == "Pending":
                pending_index = index
                break
        if pending_index is None:
            self.queue_running = False
            self.current_queue_index = None
            self.append_log("Queue finished.")
            self.training_status_label.setText(self.tr("ready"))
            return
        self.current_queue_index = pending_index
        self.training_queue[pending_index]["status"] = "Running"
        self.refresh_queue_table()
        self.queue_table.selectRow(pending_index)
        cfg = self.training_queue[pending_index]["cfg"]
        self._launch_training_job(cfg)

    def _launch_training_job(self, cfg: dict):
        self.start_train_btn.setEnabled(False)
        self.stop_train_btn.setEnabled(True)
        self.queue_start_btn.setEnabled(False)
        self.stop_requested = False
        self._updating_dataset_table = False
        self.current_training_cfg = cfg
        self.training_thread = QThread(self)
        self.training_worker = TrainingWorker(self.project_root, cfg.copy())
        self.training_worker.moveToThread(self.training_thread)
        self.training_thread.started.connect(self.training_worker.run)
        self.training_worker.log.connect(self.append_log)
        self.training_worker.finished.connect(self.on_training_finished)
        self.training_worker.failed.connect(self.on_training_failed)
        self.training_worker.finished.connect(self.training_thread.quit)
        self.training_worker.failed.connect(self.training_thread.quit)
        self.training_thread.finished.connect(self._on_training_thread_finished)
        self.training_progress.setRange(0, 0)
        self.training_progress.setFormat(self.tr("training_running"))
        self.training_status_label.setText(self.tr("training_running"))
        self.training_thread.start()
        self.append_log(f"Training started: {cfg['run_name']} ({cfg['training_mode']})")

    def _on_training_thread_finished(self):
        self.training_thread = None
        self.training_worker = None
        if self.pending_queue_resume:
            self.pending_queue_resume = False
            QTimer.singleShot(0, self._start_next_queued_job)

    def stop_training(self):
        self.queue_running = False
        self.stop_requested = True
        if self.training_worker:
            self.training_worker.stop()
            self.append_log("Training termination requested.")
            self.training_status_label.setText(self.tr("ready"))
            self.training_progress.setRange(0, 100)
            self.training_progress.setValue(0)
            self.training_progress.setFormat(self.tr("training_idle"))

    def on_training_finished(self, code: int):
        status = "Done" if code == 0 and not self.stop_requested else "Stopped"
        if self.current_queue_index is not None and 0 <= self.current_queue_index < len(self.training_queue):
            self.training_queue[self.current_queue_index]["status"] = status if code == 0 else "Failed"
            self.refresh_queue_table()
        run_name = self.current_training_cfg.get("run_name", "") if self.current_training_cfg else ""
        self.append_log(f"Training process finished with exit code {code}: {run_name}")
        self.training_progress.setRange(0, 100)
        self.training_progress.setValue(100 if code == 0 else 0)
        self.training_progress.setFormat(self.tr("training_finished") if code == 0 else self.tr("training_idle"))
        self.training_status_label.setText(self.tr("training_finished") if code == 0 else self.tr("ready"))
        self.start_train_btn.setEnabled(True)
        self.stop_train_btn.setEnabled(False)
        self.queue_start_btn.setEnabled(True)
        self.current_training_cfg = None
        if self.queue_running and not self.stop_requested and code == 0:
            self.pending_queue_resume = True
        else:
            self.queue_running = False
            self.current_queue_index = None

    def on_training_failed(self, message: str):
        if self.current_queue_index is not None and 0 <= self.current_queue_index < len(self.training_queue):
            self.training_queue[self.current_queue_index]["status"] = "Failed"
            self.refresh_queue_table()
        self.start_train_btn.setEnabled(True)
        self.stop_train_btn.setEnabled(False)
        self.queue_start_btn.setEnabled(True)
        self.queue_running = False
        self.current_queue_index = None
        self.current_training_cfg = None
        self.append_log(f"Training failed: {message}")
        self.training_progress.setRange(0, 100)
        self.training_progress.setValue(0)
        self.training_progress.setFormat(self.tr("training_idle"))
        self.training_status_label.setText(self.tr("ready"))
        QMessageBox.critical(self, self.tr("training_failed_title"), message)
