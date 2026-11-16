"""Small CUDA allocation, matrix multiplication, and backward-pass check."""
import argparse
import json
import os
import platform
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-cpu", action="store_true", help="Local testing only")
    args = parser.parse_args()
    import torch

    print(f"[environment] Python={platform.python_version()} torch={torch.__version__} CUDA={torch.version.cuda}", flush=True)
    if not torch.cuda.is_available() and not args.allow_cpu:
        raise RuntimeError("CUDA is unavailable. Check the selected image and GPU allocation.")
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    if device.type == "cuda":
        props = torch.cuda.get_device_properties(device)
        print(f"[device] {props.name}; visible_memory_gib={props.total_memory / 1024**3:.2f}", flush=True)
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
    torch.manual_seed(42)
    started = time.monotonic()
    x = torch.randn(256, 256, device=device, requires_grad=True)
    y = torch.randn(256, 256, device=device)
    loss = (x @ y).square().mean()
    loss.backward()
    if device.type == "cuda":
        torch.cuda.synchronize()
    if not torch.isfinite(loss).item() or not torch.isfinite(x.grad).all().item():
        raise RuntimeError("The smoke test produced non-finite values.")
    result = {
        "status": "passed", "device": str(device), "torch": torch.__version__,
        "cuda": torch.version.cuda, "loss": loss.item(),
        "elapsed_seconds": round(time.monotonic() - started, 4),
        "peak_memory_mib": round(torch.cuda.max_memory_allocated() / 1024**2, 2) if device.type == "cuda" else None,
        "data_mount_exists": Path("/app/data").is_dir(),
    }
    output = Path(os.environ["RUN_OUTPUT_DIR"])
    (output / "smoke.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("[smoke] PASS " + json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
