import os
import sys
from pathlib import Path

# Register NVIDIA CUDA DLLs before any imports that need them.
# pip-installed nvidia-cublas-cu12 / nvidia-cudnn-cu12 place DLLs in
# site-packages/nvidia/*/bin/ which isn't on the default DLL search path.
if sys.platform == "win32":
    for sp in [Path(p) for p in sys.path if "site-packages" in p]:
        nvidia_dir = sp / "nvidia"
        if not nvidia_dir.is_dir():
            continue
        for pkg in nvidia_dir.iterdir():
            bin_dir = pkg / "bin"
            if bin_dir.is_dir():
                os.add_dll_directory(str(bin_dir))
                # Also add to PATH as a fallback for lazy-loaded DLLs
                os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000)
