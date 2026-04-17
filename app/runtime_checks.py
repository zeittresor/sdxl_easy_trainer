from __future__ import annotations

_TORCH_STATUS: dict | None = None


def preload_torch() -> dict:
    global _TORCH_STATUS
    if _TORCH_STATUS is not None:
        return _TORCH_STATUS
    try:
        import torch  # noqa: F401
        _TORCH_STATUS = {
            "ok": True,
            "version": getattr(torch, "__version__", "unknown"),
            "error": "",
        }
    except Exception as exc:
        _TORCH_STATUS = {
            "ok": False,
            "version": "",
            "error": str(exc),
        }
    return _TORCH_STATUS


def torch_status() -> dict:
    return preload_torch()


def torch_is_available() -> bool:
    return bool(preload_torch().get("ok"))
