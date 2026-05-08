# LLIE STM32H750 setup notes

## Environment prepared
- Python venv: `/home/stonies/venvs/llie-train`
- Activate: `source /home/stonies/venvs/llie-train/bin/activate`
- Verified packages:
  - torch 2.5.1+cu121
  - torchvision 0.20.1+cu121
  - pillow 12.2.0
  - opencv-python 4.13.0
  - numpy, pyyaml, matplotlib, tqdm, scikit-image
- Verified GPU:
  - NVIDIA GeForce GTX 1050 Ti
  - CUDA available in torch: True

## Working directories
- Project root: `/home/stonies/projects/llie-stm32`
- Datasets: `/home/stonies/projects/llie-stm32/datasets`
- Repos: `/home/stonies/projects/llie-stm32/repos`
- Training workspace: `/home/stonies/projects/llie-stm32/workspace`

## Teacher repo cloned
- Zero-DCE: `/home/stonies/projects/llie-stm32/repos/Zero-DCE`

## Recommended starter datasets
1. LOL-v1
2. LOL-v2 Real
3. LOL-v2 Synthetic (optional)
4. Real low-light images/videos captured locally (optional, but valuable)

## Practical recommendation
- Start with LOL-v1 to debug pipeline quickly.
- Move to LOL-v2 Real for main paired training.
- Add real low-light clips later for temporal finetuning.

## Next build steps
1. Create dataset download/import scripts.
2. Build full training workspace under `workspace/`.
3. Add teacher target generation wrapper using Zero-DCE.
4. Add offline fitting + student training scripts.
5. Run a tiny smoke-train on GTX 1050 Ti.
