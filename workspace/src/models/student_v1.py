import torch
import torch.nn as nn
import torch.nn.functional as F


class DSConvBlock(nn.Module):
    def __init__(self, in_ch: int, out_ch: int):
        super().__init__()
        self.dw = nn.Conv2d(in_ch, in_ch, kernel_size=3, padding=1, groups=in_ch, bias=True)
        self.pw = nn.Conv2d(in_ch, out_ch, kernel_size=1, bias=True)
        self.act = nn.ReLU(inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.dw(x)
        x = self.pw(x)
        x = self.act(x)
        return x


class StudentV1(nn.Module):
    def __init__(self, in_channels: int = 1, base_channels: int = 8, local_hidden_channels: int = 4, map_size: int = 24):
        super().__init__()
        if map_size not in (8, 12, 24):
            raise ValueError('map_size must be one of 8, 12, 24 for the current workspace presets')

        self.map_size = map_size
        self.block1 = DSConvBlock(in_channels, base_channels)
        self.block2 = DSConvBlock(base_channels, base_channels)
        self.pool_24 = nn.AvgPool2d(kernel_size=4, stride=4)

        self.local_head = nn.Sequential(
            nn.Conv2d(base_channels, local_hidden_channels, kernel_size=1, bias=True),
            nn.ReLU(inplace=True),
            nn.Conv2d(local_hidden_channels, 1, kernel_size=1, bias=True),
        )

        self.global_fc1 = nn.Linear(base_channels, base_channels)
        self.global_fc2 = nn.Linear(base_channels, 3)

    def forward(self, x: torch.Tensor) -> dict:
        x = self.block1(x)
        x = self.block2(x)
        feat_24 = self.pool_24(x)

        local_raw = self.local_head(feat_24)
        if self.map_size != 24:
            local_raw = F.interpolate(local_raw, size=(self.map_size, self.map_size), mode='bilinear', align_corners=False)

        gap = feat_24.mean(dim=(2, 3))
        g = F.relu(self.global_fc1(gap), inplace=False)
        global_raw = self.global_fc2(g)

        return {
            'local_raw': local_raw,
            'global_raw': global_raw,
        }


class StudentGlobalOnly(nn.Module):
    def __init__(self, in_channels: int = 1, base_channels: int = 8):
        super().__init__()
        self.block1 = DSConvBlock(in_channels, base_channels)
        self.block2 = DSConvBlock(base_channels, base_channels)
        self.pool_24 = nn.AvgPool2d(kernel_size=4, stride=4)
        self.global_fc1 = nn.Linear(base_channels, base_channels)
        self.global_fc2 = nn.Linear(base_channels, 3)

    def forward(self, x: torch.Tensor) -> dict:
        x = self.block1(x)
        x = self.block2(x)
        feat_24 = self.pool_24(x)
        gap = feat_24.mean(dim=(2, 3))
        g = F.relu(self.global_fc1(gap), inplace=False)
        global_raw = self.global_fc2(g)
        return {
            'local_raw': None,
            'global_raw': global_raw,
        }
