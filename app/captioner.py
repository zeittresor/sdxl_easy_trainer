import re
from pathlib import Path
from PIL import Image, ImageOps


_ORIENTATION_PATTERN = re.compile(
    r"(?:,?\s*(?:rotated|turned)\s+to\s+the\s+(?:left|right))|(?:,?\s*upside[- ]down)",
    re.IGNORECASE,
)


def clean_caption_text(text: str) -> str:
    clean = re.sub(r"\s+", " ", (text or "").strip())
    clean = _ORIENTATION_PATTERN.sub("", clean)
    clean = re.sub(r"\s+", " ", clean).strip(" ,.;:-")
    return clean


def format_caption_text(text: str, prefix: str = "", suffix: str = "", style: str = "conservative") -> str:
    clean = clean_caption_text(text)
    lowered = clean.lower()
    if clean:
        if style == "detailed":
            if not (lowered.startswith("a detailed photo of") or lowered.startswith("detailed photo of")):
                clean = f"a detailed photo of {clean}"
        else:
            for lead in ("a photo of ", "photo of "):
                if lowered.startswith(lead):
                    clean = clean[len(lead):].strip()
                    break
    parts = [prefix.strip(), clean, suffix.strip()]
    return " ".join([p for p in parts if p]).strip()


class OfflineBlipCaptioner:
    def __init__(
        self,
        model_dir: Path,
        prompt: str = "a photo of",
        style: str = "conservative",
        max_new_tokens: int = 28,
        min_new_tokens: int = 6,
        num_beams: int = 3,
        no_repeat_ngram_size: int = 3,
        repetition_penalty: float = 1.15,
    ):
        self.model_dir = model_dir
        self.processor = None
        self.model = None
        self.prompt = (prompt or "a photo of").strip()
        self.style = (style or "conservative").strip().lower()
        self.max_new_tokens = int(max_new_tokens)
        self.min_new_tokens = int(min_new_tokens)
        self.num_beams = int(num_beams)
        self.no_repeat_ngram_size = int(no_repeat_ngram_size)
        self.repetition_penalty = float(repetition_penalty)

    def load(self):
        if self.processor is not None and self.model is not None:
            return
        from transformers import AutoProcessor, BlipForConditionalGeneration
        self.processor = AutoProcessor.from_pretrained(str(self.model_dir), local_files_only=True)
        self.model = BlipForConditionalGeneration.from_pretrained(str(self.model_dir), local_files_only=True)

    def caption(self, image_path: Path, prefix: str = "", suffix: str = "") -> str:
        self.load()
        image = ImageOps.exif_transpose(Image.open(image_path)).convert("RGB")
        prompt = self.prompt or "a photo of"
        inputs = self.processor(images=image, text=prompt, return_tensors="pt")
        out = self.model.generate(
            **inputs,
            max_new_tokens=max(4, self.max_new_tokens),
            min_new_tokens=max(0, min(self.min_new_tokens, self.max_new_tokens)),
            num_beams=max(1, self.num_beams),
            no_repeat_ngram_size=max(0, self.no_repeat_ngram_size),
            repetition_penalty=max(1.0, self.repetition_penalty),
        )
        text = self.processor.batch_decode(out, skip_special_tokens=True)[0].strip()
        lowered = text.lower()
        prompt_lower = prompt.lower().strip()
        if prompt_lower and lowered.startswith(prompt_lower):
            text = text[len(prompt):].strip(" ,.;:-")
        return format_caption_text(text, prefix, suffix, self.style)
