# Setup Notes

This project is intended to be cloned and run from any local path.

## Python Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install torch torchvision numpy scipy pyyaml opencv-python-headless
```

Use CUDA-enabled PyTorch if training on an NVIDIA GPU.

## Working Directories

```text
datasets/    local datasets, ignored by git
repos/       optional cloned reference repos, ignored by git
workspace/   training and export code
```

## Optional Teacher Repo

Clone Zero-DCE under:

```text
repos/Zero-DCE
```

The teacher path is optional. The student can also train directly against paired `low/high` images.

## Recommended Dataset Order

1. LOL-v1 for quick pipeline debugging.
2. LOL-v2 Real for stronger paired training.
3. Local captured low-light clips for temporal testing.
