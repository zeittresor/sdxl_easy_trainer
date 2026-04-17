from pathlib import Path

def convert_safetensors_to_pt(src_path: Path, dst_path: Path) -> None:
    import torch
    from safetensors.torch import load_file
    state_dict = load_file(str(src_path))
    torch.save(state_dict, str(dst_path))
