from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np
import torch
from torch.utils.data import Dataset

from .image_dataset import resize_hw, rgb_to_y, read_rgb


class TemporalClipDataset(Dataset):
    def __init__(
        self,
        clips_root: str,
        teacher_root: Optional[str] = None,
        input_size: int = 96,
        out_h: int = 120,
        out_w: int = 160,
    ):
        self.clips_root = Path(clips_root)
        self.teacher_root = Path(teacher_root) if teacher_root else None
        self.input_size = input_size
        self.out_h = out_h
        self.out_w = out_w
        self.pairs: List[Tuple[Path, Path]] = []

        for clip_dir in sorted([p for p in self.clips_root.iterdir() if p.is_dir()]):
            frames = []
            for ext in ('*.png', '*.jpg', '*.jpeg', '*.bmp'):
                frames.extend(sorted(clip_dir.glob(ext)))
            for i in range(len(frames) - 1):
                self.pairs.append((frames[i], frames[i + 1]))

        if not self.pairs:
            raise RuntimeError(f'No temporal pairs found in {self.clips_root}')

    def __len__(self):
        return len(self.pairs)

    def _prep(self, path: Path):
        rgb = read_rgb(str(path))
        y = rgb_to_y(rgb)
        y_full = resize_hw(y, self.out_h, self.out_w)
        y_96 = resize_hw(y_full, self.input_size, self.input_size, interpolation=cv2.INTER_AREA)
        return y_96, y_full

    def __getitem__(self, idx):
        p0, p1 = self.pairs[idx]
        y96_0, yfull_0 = self._prep(p0)
        y96_1, yfull_1 = self._prep(p1)

        sample = {
            'name0': p0.stem,
            'name1': p1.stem,
            'y_low_96_t': torch.from_numpy(y96_0[None, ...]),
            'y_low_full_t': torch.from_numpy(yfull_0[None, ...]),
            'y_low_96_t1': torch.from_numpy(y96_1[None, ...]),
            'y_low_full_t1': torch.from_numpy(yfull_1[None, ...]),
        }

        if self.teacher_root:
            clip_name = p0.parent.name
            t0 = self.teacher_root / clip_name / f'{p0.stem}.npy'
            t1 = self.teacher_root / clip_name / f'{p1.stem}.npy'
            if t0.exists() and t1.exists():
                sample['teacher_y_full_t'] = torch.from_numpy(np.load(str(t0)).astype(np.float32)[None, ...])
                sample['teacher_y_full_t1'] = torch.from_numpy(np.load(str(t1)).astype(np.float32)[None, ...])

        return sample
