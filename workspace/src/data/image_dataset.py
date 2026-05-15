from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import torch
from torch.utils.data import Dataset


def read_rgb(path: str) -> np.ndarray:
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return img


def rgb_to_y(img_rgb: np.ndarray) -> np.ndarray:
    img = img_rgb.astype(np.float32) / 255.0
    y = 0.299 * img[:, :, 0] + 0.587 * img[:, :, 1] + 0.114 * img[:, :, 2]
    return y.astype(np.float32)


def resize_hw(img: np.ndarray, h: int, w: int, interpolation=cv2.INTER_AREA) -> np.ndarray:
    return cv2.resize(img, (w, h), interpolation=interpolation)


class PairedImageDataset(Dataset):
    def __init__(
        self,
        low_dir: str,
        high_dir: str,
        teacher_dir: Optional[str] = None,
        input_size: int = 96,
        out_h: int = 120,
        out_w: int = 160,
        param_dir: Optional[str] = None,
        map_size: Optional[int] = None,
    ):
        self.low_dir = Path(low_dir)
        self.high_dir = Path(high_dir)
        self.teacher_dir = Path(teacher_dir) if teacher_dir else None
        self.param_dir = Path(param_dir) if param_dir else None
        self.input_size = input_size
        self.out_h = out_h
        self.out_w = out_w
        self.map_size = map_size

        exts = ('*.png', '*.jpg', '*.jpeg', '*.bmp')
        files = []
        for ext in exts:
            files.extend(sorted(self.low_dir.glob(ext)))
        self.low_files = files
        if not self.low_files:
            raise RuntimeError(f'No images found in {self.low_dir}')

    def __len__(self):
        return len(self.low_files)

    def _match_high_path(self, low_path: Path) -> Path:
        high_path = self.high_dir / low_path.name
        if not high_path.exists():
            raise FileNotFoundError(f'Cannot find matching high image for {low_path.name} in {self.high_dir}')
        return high_path

    def __getitem__(self, idx):
        low_path = self.low_files[idx]
        high_path = self._match_high_path(low_path)

        low_rgb = read_rgb(str(low_path))
        high_rgb = read_rgb(str(high_path))

        low_y = rgb_to_y(low_rgb)
        high_y = rgb_to_y(high_rgb)

        low_y_full = resize_hw(low_y, self.out_h, self.out_w)
        high_y_full = resize_hw(high_y, self.out_h, self.out_w)
        low_y_96 = resize_hw(low_y_full, self.input_size, self.input_size, interpolation=cv2.INTER_AREA)

        sample = {
            'name': low_path.stem,
            'y_low_96': torch.from_numpy(low_y_96[None, ...]),
            'y_low_full': torch.from_numpy(low_y_full[None, ...]),
            'y_high_full': torch.from_numpy(high_y_full[None, ...]),
        }

        if self.teacher_dir:
            teacher_path = self.teacher_dir / f'{low_path.stem}.npy'
            if teacher_path.exists():
                teacher_y = np.load(str(teacher_path)).astype(np.float32)
                sample['teacher_y_full'] = torch.from_numpy(teacher_y[None, ...])

        if self.param_dir:
            param_path = self.param_dir / f'{low_path.stem}.npz'
            if param_path.exists():
                z = np.load(str(param_path))
                gain_global = float(np.asarray(z['gain_global']).reshape(-1)[0])
                gamma_global = float(np.asarray(z['gamma_global']).reshape(-1)[0])
                lift_black = float(np.asarray(z['lift_black']).reshape(-1)[0])
                sample['gain_global_tgt'] = torch.tensor([gain_global], dtype=torch.float32)
                sample['gamma_global_tgt'] = torch.tensor([gamma_global], dtype=torch.float32)
                sample['lift_black_tgt'] = torch.tensor([lift_black], dtype=torch.float32)
                if 'gain_map' in z.files:
                    gain_map = np.asarray(z['gain_map'], dtype=np.float32)
                    sample['gain_map_tgt'] = torch.from_numpy(gain_map[None, ...])

        return sample


class RGBPairedImageDataset(Dataset):
    """Paired RGB low/high-light dataset for direct image-to-image training."""

    def __init__(
        self,
        low_dir: str,
        high_dir: str,
        teacher_dir: Optional[str] = None,
        image_size: int = 96,
    ):
        self.low_dir = Path(low_dir)
        self.high_dir = Path(high_dir)
        self.teacher_dir = Path(teacher_dir) if teacher_dir else None
        self.image_size = image_size

        files = []
        for ext in ('*.png', '*.jpg', '*.jpeg', '*.bmp'):
            files.extend(sorted(self.low_dir.glob(ext)))
        self.low_files = files
        if not self.low_files:
            raise RuntimeError(f'No images found in {self.low_dir}')

    def __len__(self):
        return len(self.low_files)

    def _match_high_path(self, low_path: Path) -> Path:
        high_path = self.high_dir / low_path.name
        if not high_path.exists():
            raise FileNotFoundError(f'Cannot find matching high image for {low_path.name} in {self.high_dir}')
        return high_path

    @staticmethod
    def _to_chw01(img_rgb: np.ndarray) -> torch.Tensor:
        arr = img_rgb.astype(np.float32) / 255.0
        return torch.from_numpy(np.transpose(arr, (2, 0, 1)).copy())

    def __getitem__(self, idx):
        low_path = self.low_files[idx]
        high_path = self._match_high_path(low_path)
        low_rgb = resize_hw(read_rgb(str(low_path)), self.image_size, self.image_size)
        high_rgb = resize_hw(read_rgb(str(high_path)), self.image_size, self.image_size)

        sample = {
            'name': low_path.stem,
            'rgb_low': self._to_chw01(low_rgb),
            'rgb_high': self._to_chw01(high_rgb),
        }

        if self.teacher_dir:
            for suffix in ('.png', '.jpg', '.jpeg', '.bmp'):
                teacher_path = self.teacher_dir / f'{low_path.stem}{suffix}'
                if teacher_path.exists():
                    teacher_rgb = resize_hw(read_rgb(str(teacher_path)), self.image_size, self.image_size)
                    sample['rgb_teacher'] = self._to_chw01(teacher_rgb)
                    break

        return sample
