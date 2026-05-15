import torch
import torch.nn as nn
import torch.nn.functional as F


class SinusoidalTimeEmbedding(nn.Module):
    def __init__(self, dim: int):
        super().__init__()
        self.dim = dim

    def forward(self, t: torch.Tensor) -> torch.Tensor:
        half = self.dim // 2
        freqs = torch.exp(
            torch.arange(half, device=t.device, dtype=t.dtype)
            * (-torch.log(torch.tensor(10000.0, device=t.device, dtype=t.dtype)) / max(half - 1, 1))
        )
        args = t[:, None] * freqs[None]
        emb = torch.cat([torch.sin(args), torch.cos(args)], dim=1)
        return emb if self.dim % 2 == 0 else F.pad(emb, (0, 1))


class TinyDiffusionTeacher(nn.Module):
    """Small conditional denoiser scaffold for RGB low-light enhancement experiments."""

    def __init__(self, base_channels: int = 32, time_dim: int = 32):
        super().__init__()
        self.time_embed = nn.Sequential(
            SinusoidalTimeEmbedding(time_dim),
            nn.Linear(time_dim, base_channels),
            nn.ReLU(inplace=True),
            nn.Linear(base_channels, base_channels),
        )
        self.in_conv = nn.Conv2d(6, base_channels, kernel_size=3, padding=1)
        self.block1 = nn.Sequential(
            nn.ReLU(inplace=True),
            nn.Conv2d(base_channels, base_channels, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
        )
        self.block2 = nn.Sequential(
            nn.Conv2d(base_channels, base_channels, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
        )
        self.out_conv = nn.Conv2d(base_channels, 3, kernel_size=3, padding=1)

    def forward(self, noisy_target: torch.Tensor, low_rgb: torch.Tensor, t: torch.Tensor) -> torch.Tensor:
        x = torch.cat([noisy_target, low_rgb], dim=1)
        feat = self.in_conv(x)
        temb = self.time_embed(t.float()).unsqueeze(-1).unsqueeze(-1)
        feat = feat + temb
        feat = self.block1(feat)
        feat = self.block2(feat)
        return self.out_conv(feat)
