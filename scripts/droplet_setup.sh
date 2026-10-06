#!/usr/bin/env bash
# Set up an AMD Developer Cloud MI300X droplet for Turno.
#
# Assumes a ROCm image with PyTorch preinstalled. Aurora lists torch unpinned,
# so the venv inherits the system packages and pip keeps the image's ROCm build
# instead of pulling a CUDA wheel. The script stops if torch cannot see the GPU.
#
# Run on the droplet:
#   export GITHUB_TOKEN=...   # only for the clone, not stored in the remote URL
#   bash droplet_setup.sh
#
# The droplet bills while powered off. Destroy it when a session ends.
set -euo pipefail

WORK="${WORK:-$HOME/turno-work}"
mkdir -p "$WORK"
cd "$WORK"

echo "== GPU and ROCm"
(rocm-smi --showproductname || amd-smi static) 2>/dev/null | head -20 || echo "no rocm-smi or amd-smi on PATH"

echo "== Python and torch from the image"
python3 - <<'PY'
import torch
print("torch", torch.__version__, "hip", getattr(torch.version, "hip", None))
assert torch.cuda.is_available(), "torch cannot see the GPU"
print("device", torch.cuda.get_device_name(0))
print("memory GB", round(torch.cuda.get_device_properties(0).total_memory / 1e9, 1))
PY

echo "== Repository"
if [ ! -d turno ]; then
  git -c http.extraheader="AUTHORIZATION: basic $(printf 'x-access-token:%s' "$GITHUB_TOKEN" | base64 -w0)" \
    clone https://github.com/Aashan47/turno.git
fi
cd turno

echo "== Environment, inheriting the image's ROCm torch"
python3 -m venv --system-site-packages .venv
. .venv/bin/activate
python -m pip install -q --upgrade pip
python -m pip install -q microsoft-aurora==2.0.1 thermofeel==2.3.0 xarray netCDF4 zarr gcsfs httpx dask
python - <<'PY'
import torch, aurora
assert torch.cuda.is_available() and getattr(torch.version, "hip", None), "lost the ROCm torch"
print("aurora", aurora.__version__ if hasattr(aurora, "__version__") else "installed", "torch", torch.__version__)
PY

echo "== Disk"
df -h "$WORK" | tail -1
echo "ready: $WORK/turno"
