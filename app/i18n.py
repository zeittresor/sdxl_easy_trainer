import json
from pathlib import Path

ENGLISH_STRINGS = {'app_title': 'SDXL Easy Trainer Offline',
 'language': 'Language',
 'workspace': 'Workspace',
 'dataset_tools': 'Dataset Tools',
 'training': 'Training',
 'settings': 'Settings',
 'logs': 'Logs',
 'paths': 'Paths',
 'prepared_images': 'Prepared images',
 'batch_import_preprocessing': 'Batch import and preprocessing',
 'embedding_textual_inversion': 'Embedding / Textual Inversion',
 'training_queue': 'Training queue',
 'offline_assets': 'Offline assets',
 'simple_mode': 'Simple mode',
 'advanced_settings': 'Advanced settings',
 'source_folder': 'Source folder',
 'dataset_name': 'Dataset name',
 'target_resolution': 'Target resolution',
 'crop_mode': 'Crop mode',
 'caption_model': 'Caption model',
 'caption_images': 'Generate captions',
 'import_images': 'Import + preprocess',
 'prepare_dataset': 'Prepare dataset',
 'run_name': 'Run name',
 'training_mode': 'Training mode',
 'base_model_dir': 'Base model folder',
 'dataset_dir': 'Prepared dataset folder',
 'output_dir': 'Output folder',
 'start_training': 'Start training',
 'stop_training': 'Stop training',
 'open_folder': 'Open folder',
 'browse': 'Browse',
 'status': 'Status',
 'caption_prefix': 'Caption prefix',
 'caption_suffix': 'Caption suffix',
 'train_text_encoder': 'Train text encoder',
 'gradient_checkpointing': 'Use gradient checkpointing',
 'export_pt': 'Also export .pt',
 'base_model_repo': 'Base model repo',
 'base_model_variant': 'Base model weight variant',
 'blip_model_dir': 'BLIP model folder',
 'diffusers_dir': 'Diffusers source folder',
 'download_status': 'Offline asset status',
 'ready': 'Ready',
 'not_found': 'Not found',
 'detected': 'Detected',
 'placeholder_token': 'Placeholder token',
 'initializer_token': 'Initializer token',
 'learnable_property': 'Learnable property',
 'add_source_images': 'Add source images...',
 'open_source_folder': 'Open source folder',
 'open_dataset_folder': 'Open dataset folder',
 'open_output_folder': 'Open output folder',
 'preview': 'Preview',
 'image': 'Image',
 'caption': 'Caption',
 'caption_file': 'Caption file',
 'batch_size': 'Batch size',
 'gradient_accumulation': 'Gradient accumulation',
 'lora_rank': 'LoRA rank',
 'learning_rate': 'Learning rate',
 'text_encoder_lr': 'Text encoder LR',
 'lr_scheduler': 'LR scheduler',
 'max_train_steps': 'Max train steps',
 'save_every': 'Save every',
 'mixed_precision': 'Mixed precision',
 'num_vectors': 'Num vectors',
 'repeats': 'Repeats',
 'embedding_resolution': 'Embedding resolution',
 'add_current_job': 'Add current job',
 'remove_selected': 'Remove selected',
 'move_up': 'Move up',
 'move_down': 'Move down',
 'start_queue': 'Start queue',
 'clear_queue': 'Clear queue',
 'run': 'Run',
 'mode': 'Mode',
 'dataset': 'Dataset',
 'output': 'Output',
 'refresh_asset_status': 'Refresh asset status',
 'edit_user_config': 'Edit user_config.json',
 'open_config_folder': 'Open config folder',
 'edit_json_info': 'Edit the JSON manually. Save only valid JSON objects.',
 'invalid_json': 'Invalid JSON',
 'invalid_json_object': 'The root JSON value must be an object/dictionary.',
 'theme': 'Appearance',
 'theme_dark': 'Dark mode',
 'theme_light': 'Light mode',
 'training_progress': 'Training progress',
 'training_idle': 'Waiting for training',
 'training_running': 'Training is running...',
 'training_finished': 'Training finished',
 'simple_workflow': 'Simple workflow:\n'
                    '1. Add many source images.\n'
                    '2. Choose target format and crop mode.\n'
                    '3. Enable offline captions if needed.\n'
                    '4. Click import to create a clean SDXL-ready dataset.',
 'choose_source_images': 'Choose source images',
 'source_images_added': 'Source images added',
 'source_images_added_text': 'Imported {count} image(s) into the source folder.',
 'missing_source_title': 'Missing source folder',
 'missing_source_text': 'Please choose a valid source folder.',
 'missing_dataset_title': 'Missing dataset folder',
 'missing_dataset_text': 'Please choose a valid prepared dataset folder.',
 'dataset_import_failed': 'Dataset import failed',
 'metadata_rebuild_failed': 'Metadata rebuild failed',
 'queue_busy': 'Queue busy',
 'queue_busy_remove': 'The currently running queue job cannot be removed.',
 'queue_busy_stop': 'Stop the running queue first.',
 'training_running_title': 'Training already running',
 'training_running_text': 'Please wait until the current training job finishes.',
 'queue_empty_title': 'Queue empty',
 'queue_empty_text': 'Add one or more jobs to the queue first.',
 'cannot_queue_title': 'Cannot queue job',
 'training_cannot_start_title': 'Training cannot start',
 'training_failed_title': 'Training failed',
 'tooltip_language': 'Switch the interface language. Extra languages can be added as JSON files in app/lang/.',
 'tooltip_workspace': 'Main working directory for datasets, models, outputs and logs.',
 'tooltip_source_folder': 'Folder with your original source images before preprocessing.',
 'tooltip_dataset_name': 'Friendly name used to build dataset-related paths.',
 'tooltip_dataset_dir': 'Prepared dataset folder used for local training after import.',
 'tooltip_output_dir': 'Where LoRA or embedding results, checkpoints and exports are written.',
 'tooltip_base_model_dir': 'Local SDXL base model folder downloaded during setup and used offline.',
 'tooltip_resolution': 'Target image size for preprocessing. Choose a format that matches your training goal.',
 'tooltip_crop_mode': 'How images are adapted to the target aspect ratio: center crop, smart crop or padded fit.',
 'tooltip_caption_prefix': 'Optional text prepended to every generated caption.',
 'tooltip_caption_suffix': 'Optional text appended to every generated caption.',
 'tooltip_make_captions': 'Enable offline BLIP caption generation for imported images.',
 'tooltip_import': 'Imports the source images, resizes/crops them and optionally creates captions.',
 'tooltip_prepare_dataset': 'Rebuilds metadata.jsonl from the prepared image folder without importing again.',
 'tooltip_run_name': 'Name of the current training run. Also used as the output subfolder name.',
 'tooltip_training_mode': 'Choose whether to train an SDXL LoRA or an SDXL embedding/textual inversion.',
 'tooltip_batch_size': 'Number of training images processed per step. Higher values need more VRAM.',
 'tooltip_grad_accum': 'Accumulates gradients over multiple mini-batches to simulate a bigger batch size.',
 'tooltip_rank': 'LoRA rank. Higher values increase flexibility, size and VRAM usage.',
 'tooltip_learning_rate': 'Main optimizer learning rate for the training run.',
 'tooltip_text_encoder_lr': 'Separate learning rate for the text encoder when that option is enabled.',
 'tooltip_scheduler': 'Learning-rate scheduler used by the official Diffusers training script.',
 'tooltip_max_steps': 'Maximum number of optimizer steps before training stops.',
 'tooltip_save_steps': 'How often checkpoints are written during training.',
 'tooltip_mixed_precision': 'Precision mode used for training. fp16 is usually the most practical on consumer GPUs.',
 'tooltip_train_text_encoder': 'Also trains the text encoder. Can improve specificity but costs more VRAM and time.',
 'tooltip_gradient_checkpointing': 'Trades speed for lower VRAM usage by recomputing parts of the model.',
 'tooltip_export_pt': 'Creates an additional .pt export after the main safetensors result is finished.',
 'tooltip_placeholder_token': 'New token that represents your custom concept in embedding mode.',
 'tooltip_initializer_token': 'Existing token used as the initial semantic starting point for the new embedding.',
 'tooltip_learnable_property': 'Treat the embedding more like an object or more like a style.',
 'tooltip_num_vectors': 'Number of embedding vectors reserved for the placeholder token.',
 'tooltip_repeats': 'How often each image is virtually repeated during embedding training.',
 'tooltip_embedding_resolution': 'Training resolution for textual inversion mode.',
 'tooltip_queue_table': 'List of queued training jobs that can be reordered and processed one after another.',
 'tooltip_add_queue': 'Add the currently visible training configuration to the queue.',
 'tooltip_remove_queue': 'Remove the selected queued training job.',
 'tooltip_move_up': 'Move the selected queued job one position up.',
 'tooltip_move_down': 'Move the selected queued job one position down.',
 'tooltip_start_queue': 'Run all queued jobs from top to bottom.',
 'tooltip_clear_queue': 'Clear the training queue when nothing is running.',
 'tooltip_base_model_repo': 'Repository name remembered for setup/update purposes.',
 'tooltip_base_model_variant': 'Model weight variant such as fp16. This is passed to the training script when '
                               'available.',
 'tooltip_blip_model_dir': 'Local folder that contains the offline BLIP captioning model.',
 'tooltip_diffusers_dir': 'Local Diffusers source tree with the official training scripts.',
 'tooltip_asset_status': 'Quick check whether the required offline model assets were found.',
 'tooltip_refresh_asset_status': 'Refresh the asset detection summary.',
 'tooltip_edit_config': 'Open user_config.json in a built-in JSON editor with validation.',
 'tooltip_open_config_folder': 'Open the project folder that contains user_config.json and other app files.',
 'tooltip_theme': 'Switch between a modern dark theme and a light theme.',
 'tooltip_dataset_table': 'Preview of the prepared dataset images and their caption files. Double-click a caption cell to edit it directly; changes are saved into the matching .txt file and metadata.jsonl.',
 'tooltip_logs': 'Live application and training log output.',
 'tooltip_training_progress': 'Shows training activity and tries to estimate step progress from the trainer output.'}

ENGLISH_STRINGS.update({
    'rotate_left': 'Rotate left',
    'rotate_right': 'Rotate right',
    'recaption_selected': 'Re-caption selected',
    'tooltip_rotate_left': 'Rotate the selected prepared training image 90° to the left and keep the prepared canvas size.',
    'tooltip_rotate_right': 'Rotate the selected prepared training image 90° to the right and keep the prepared canvas size.',
    'tooltip_recaption_selected': 'Run the offline BLIP captioner again for the selected prepared image and overwrite its .txt caption.',
    'no_image_selected_title': 'No image selected',
    'no_image_selected_text': 'Please select a prepared image row first.',
    'image_rotate_failed': 'Image rotation failed',
    'recaption_failed_title': 'Re-captioning failed',
    'recaption_after_rotate_title': 'Create a new caption now?',
    'recaption_after_rotate_text': 'The image was rotated successfully. Do you want to generate a new BLIP caption for this modified image now?',
})

ENGLISH_STRINGS.update({
    'blip_prompt': 'BLIP prompt',
    'caption_style': 'Caption style',
    'caption_style_conservative': 'Conservative / factual',
    'caption_style_detailed': 'Detailed / richer wording',
    'blip_max_new_tokens': 'BLIP max new tokens',
    'blip_min_new_tokens': 'BLIP min new tokens',
    'blip_num_beams': 'BLIP beam count',
    'blip_no_repeat_ngram': 'BLIP no-repeat n-gram',
    'blip_repetition_penalty': 'BLIP repetition penalty',
    'tooltip_blip_prompt': 'Text prompt fed into BLIP before caption generation. Use a conservative prompt like "a photo of" to reduce fanciful interpretations.',
    'tooltip_caption_style': 'How the final caption is phrased. Conservative keeps the wording closer to the detected content, while Detailed expands it slightly.',
    'tooltip_blip_max_new_tokens': 'Maximum number of new tokens BLIP may generate. Lower values usually reduce long speculative captions.',
    'tooltip_blip_min_new_tokens': 'Minimum number of new tokens BLIP should generate.',
    'tooltip_blip_num_beams': 'Beam count for caption generation. More beams can improve stability but costs more time.',
    'tooltip_blip_no_repeat_ngram': 'Prevents repeated phrase fragments of this n-gram length from being emitted again.',
    'tooltip_blip_repetition_penalty': 'Penalty against repetitive or rambling text. Slightly above 1.0 is usually enough.',
})

ENGLISH_STRINGS.update({
    'language_self_name': 'English',
    'preset_profile': 'VRAM preset',
    'apply_preset': 'Apply preset',
    'preset_hint': 'Preset hint',
    'preset_applied': 'Preset applied',
    'custom_preset': 'Custom values',
    'tooltip_training_preset': 'Choose a hardware-oriented preset for the current training parameters. It adjusts batch size, gradient accumulation, rank and related options.',
    'tooltip_apply_preset': 'Apply the selected VRAM preset to the training controls.',
    'tooltip_preset_hint': 'Short explanation of what the selected VRAM preset is trying to optimize.',
    'tooltip_appearance': 'Choose between a modern dark mode and a light mode.',
})

_CACHE = None


def _lang_dir() -> Path:
    return Path(__file__).resolve().parent / 'lang'


def _load_catalogs() -> dict:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    catalogs = {'en': dict(ENGLISH_STRINGS)}
    lang_dir = _lang_dir()
    if lang_dir.exists():
        for path in lang_dir.glob('*.json'):
            try:
                data = json.loads(path.read_text(encoding='utf-8'))
                if isinstance(data, dict):
                    code = path.stem.lower()
                    base = dict(ENGLISH_STRINGS) if code == 'en' else {}
                    base.update(data)
                    catalogs[code] = base
            except Exception:
                continue
    _CACHE = catalogs
    return catalogs


def reload_catalogs() -> None:
    global _CACHE
    _CACHE = None


def language_options() -> list[tuple[str, str]]:
    catalogs = _load_catalogs()
    codes = sorted(catalogs.keys(), key=lambda code: (code != 'en', code))
    return [(code, catalogs.get(code, {}).get('language_self_name', code.upper())) for code in codes]


def available_languages() -> list[str]:
    return [code for code, _ in language_options()]


def get_strings(lang: str) -> dict:
    catalogs = _load_catalogs()
    base = dict(ENGLISH_STRINGS)
    base.update(catalogs.get(lang, {}))
    return base
