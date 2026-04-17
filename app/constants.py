APP_NAME = "SDXL Easy Trainer Offline"
APP_VERSION = "v0.17"
ORG_NAME = "OpenAI Sandbox"

DEFAULT_LANGUAGE = "en"
DEFAULT_APPEARANCE = "dark"

RESOLUTION_PRESETS = {
    "1024 x 1024 (square)": (1024, 1024),
    "1216 x 832 (landscape)": (1216, 832),
    "832 x 1216 (portrait)": (832, 1216),
    "1152 x 896 (landscape)": (1152, 896),
    "896 x 1152 (portrait)": (896, 1152),
    "1344 x 768 (wide)": (1344, 768),
    "768 x 1344 (tall)": (768, 1344),
}

SIMPLE_DEFAULTS = {
    "appearance": DEFAULT_APPEARANCE,
    "training_mode": "lora",
    "resolution_preset": "1024 x 1024 (square)",
    "batch_size": 1,
    "gradient_accumulation_steps": 1,
    "learning_rate": "1e-4",
    "text_encoder_lr": "5e-6",
    "rank": 4,
    "max_train_steps": 1200,
    "save_steps": 500,
    "mixed_precision": "fp16",
    "train_text_encoder": False,
    "gradient_checkpointing": True,
    "center_crop": True,
    "lr_scheduler": "constant",
    "caption_prefix": "",
    "caption_suffix": "",
    "blip_prompt": "a photo of",
    "blip_caption_style": "conservative",
    "blip_max_new_tokens": 28,
    "blip_min_new_tokens": 6,
    "blip_num_beams": 3,
    "blip_no_repeat_ngram_size": 3,
    "blip_repetition_penalty": "1.15",
    "embedding_placeholder_token": "<myconcept>",
    "embedding_initializer_token": "object",
    "embedding_learnable_property": "object",
    "embedding_num_vectors": 1,
    "embedding_repeats": 100,
    "embedding_resolution": 512,
    "export_safetensors": True,
    "export_pt": False,
    "training_preset": "custom",
}

LOG_DIR_NAME = "logs"
CONFIG_FILE_NAME = "user_config.json"


VRAM_TRAINING_PRESETS = {
    'custom': {'label': 'Custom', 'batch_size': 1, 'gradient_accumulation_steps': 1, 'rank': 4, 'learning_rate': '1e-4', 'text_encoder_lr': '5e-6', 'max_train_steps': 1200, 'save_steps': 500, 'mixed_precision': 'fp16', 'train_text_encoder': False, 'gradient_checkpointing': True, 'resolution_preset': '1024 x 1024 (square)', 'note': 'Leaves the current values untouched unless you press Apply.'},
    'vram_6gb': {'label': '6 GB VRAM', 'batch_size': 1, 'gradient_accumulation_steps': 8, 'rank': 4, 'learning_rate': '1e-4', 'text_encoder_lr': '5e-6', 'max_train_steps': 1200, 'save_steps': 250, 'mixed_precision': 'fp16', 'train_text_encoder': False, 'gradient_checkpointing': True, 'resolution_preset': '1024 x 1024 (square)', 'note': 'Most conservative preset. Lowest memory pressure, slower because of accumulation.'},
    'vram_8gb': {'label': '8 GB VRAM', 'batch_size': 1, 'gradient_accumulation_steps': 6, 'rank': 8, 'learning_rate': '1e-4', 'text_encoder_lr': '5e-6', 'max_train_steps': 1200, 'save_steps': 250, 'mixed_precision': 'fp16', 'train_text_encoder': False, 'gradient_checkpointing': True, 'resolution_preset': '1024 x 1024 (square)', 'note': 'Safe consumer preset. Keeps text-encoder training disabled to preserve VRAM headroom.'},
    'vram_12gb': {'label': '12 GB VRAM', 'batch_size': 1, 'gradient_accumulation_steps': 4, 'rank': 8, 'learning_rate': '1e-4', 'text_encoder_lr': '5e-6', 'max_train_steps': 1200, 'save_steps': 300, 'mixed_precision': 'fp16', 'train_text_encoder': False, 'gradient_checkpointing': True, 'resolution_preset': '1024 x 1024 (square)', 'note': 'Balanced SDXL LoRA preset for mid-range cards.'},
    'vram_16gb': {'label': '16 GB VRAM', 'batch_size': 1, 'gradient_accumulation_steps': 2, 'rank': 16, 'learning_rate': '1e-4', 'text_encoder_lr': '5e-6', 'max_train_steps': 1200, 'save_steps': 400, 'mixed_precision': 'fp16', 'train_text_encoder': False, 'gradient_checkpointing': True, 'resolution_preset': '1024 x 1024 (square)', 'note': 'Good quality / stability preset with more expressive rank.'},
    'vram_20gb': {'label': '20 GB VRAM', 'batch_size': 2, 'gradient_accumulation_steps': 1, 'rank': 16, 'learning_rate': '1e-4', 'text_encoder_lr': '5e-6', 'max_train_steps': 1200, 'save_steps': 400, 'mixed_precision': 'fp16', 'train_text_encoder': True, 'gradient_checkpointing': False, 'resolution_preset': '1024 x 1024 (square)', 'note': 'Starts using text-encoder training and disables checkpointing for better speed.'},
    'vram_24gb': {'label': '24 GB VRAM', 'batch_size': 2, 'gradient_accumulation_steps': 1, 'rank': 32, 'learning_rate': '1e-4', 'text_encoder_lr': '5e-6', 'max_train_steps': 1200, 'save_steps': 500, 'mixed_precision': 'fp16', 'train_text_encoder': True, 'gradient_checkpointing': False, 'resolution_preset': '1024 x 1024 (square)', 'note': 'Higher-rank preset for roomier GPUs and stronger concept capacity.'},
    'vram_32gb': {'label': '32 GB VRAM', 'batch_size': 4, 'gradient_accumulation_steps': 1, 'rank': 32, 'learning_rate': '1e-4', 'text_encoder_lr': '5e-6', 'max_train_steps': 1200, 'save_steps': 500, 'mixed_precision': 'fp16', 'train_text_encoder': True, 'gradient_checkpointing': False, 'resolution_preset': '1024 x 1024 (square)', 'note': 'Fastest preset in this app. Uses larger batches instead of gradient accumulation.'},
}
