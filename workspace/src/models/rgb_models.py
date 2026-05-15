import torch
import torch.nn as nn


class RGBDSConvBlock(nn.Module):
    def __init__(self, in_ch: int, out_ch: int):
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv2d(in_ch, in_ch, kernel_size=3, padding=1, groups=in_ch, bias=True),
            nn.Conv2d(in_ch, out_ch, kernel_size=1, bias=True),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.block(x)


class RGBCNNBaseline(nn.Module):
    """Small direct RGB-to-RGB baseline intended to stay MCU-friendly."""

    def __init__(self, base_channels: int = 16, depth: int = 4):
        super().__init__()
        layers = [nn.Conv2d(3, base_channels, kernel_size=3, padding=1), nn.ReLU(inplace=True)]
        for _ in range(depth):
            layers.append(RGBDSConvBlock(base_channels, base_channels))
        self.body = nn.Sequential(*layers)
        self.head = nn.Conv2d(base_channels, 3, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = self.head(self.body(x))
        return torch.clamp(x + residual, 0.0, 1.0)


class OneStepRGBStudent(nn.Module):
    """Compact one-step RGB student scaffold for later diffusion distillation."""

    def __init__(self, base_channels: int = 24):
        super().__init__()
        self.stem = nn.Sequential(
            nn.Conv2d(3, base_channels, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
        )
        self.encoder = nn.Sequential(
            RGBDSConvBlock(base_channels, base_channels),
            RGBDSConvBlock(base_channels, base_channels),
        )
        self.bottleneck = nn.Sequential(
            nn.AvgPool2d(kernel_size=2, stride=2),
            RGBDSConvBlock(base_channels, base_channels),
        )
        self.decoder = nn.Sequential(
            nn.Upsample(scale_factor=2, mode='bilinear', align_corners=False),
            RGBDSConvBlock(base_channels, base_channels),
        )
        self.head = nn.Conv2d(base_channels, 3, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        feat = self.encoder(self.stem(x))
        decoded = self.decoder(self.bottleneck(feat))
        residual = self.head(decoded + feat)
        return torch.clamp(x + residual, 0.0, 1.0)
