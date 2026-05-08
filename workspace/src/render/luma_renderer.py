from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

import torch
import torch.nn.functional as F


@dataclass
class RangeConfig:
    gain_min: float = 1.0
    gain_max: float = 2.5
    gamma_min: float = 0.7
    gamma_max: float = 1.6
    lift_min: float = 0.0
    lift_max: float = 24.0
    map_residual_scale: float = 0.5


@dataclass
class RenderConfig:
    out_h: int = 120
    out_w: int = 160
    eps: float = 1e-4
    ranges: RangeConfig = field(default_factory=RangeConfig)


def decode_outputs(model_out: Dict[str, Optional[torch.Tensor]], cfg: RenderConfig) -> Dict[str, Optional[torch.Tensor]]:
    global_raw = model_out['global_raw']
    local_raw = model_out['local_raw']

    s = torch.sigmoid(global_raw)
    gain = cfg.ranges.gain_min + s[:, 0:1] * (cfg.ranges.gain_max - cfg.ranges.gain_min)
    gamma = cfg.ranges.gamma_min + s[:, 1:2] * (cfg.ranges.gamma_max - cfg.ranges.gamma_min)
    lift = cfg.ranges.lift_min + s[:, 2:3] * (cfg.ranges.lift_max - cfg.ranges.lift_min)

    gain_map = None
    if local_raw is not None:
        local_res = torch.tanh(local_raw) * cfg.ranges.map_residual_scale
        gain_map = 1.0 + local_res

    return {
        'gain_global': gain,
        'gamma_global': gamma,
        'lift_black': lift,
        'gain_map': gain_map,
    }


def render_luma(
    y_full: torch.Tensor,
    decoded: Dict[str, Optional[torch.Tensor]],
    cfg: RenderConfig,
) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
    gain = decoded['gain_global'].view(-1, 1, 1, 1)
    gamma = decoded['gamma_global'].view(-1, 1, 1, 1)
    lift = decoded['lift_black'].view(-1, 1, 1, 1) / 255.0

    gain_map_up = None
    if decoded['gain_map'] is not None:
        gain_map_up = F.interpolate(
            decoded['gain_map'],
            size=(cfg.out_h, cfg.out_w),
            mode='bilinear',
            align_corners=False,
        )

    y = y_full + lift
    y = torch.clamp(y, 0.0, 1.0)

    if gain_map_up is None:
        y = y * gain
    else:
        y = y * gain * gain_map_up
    y = torch.clamp(y, cfg.eps, 1.0)

    y = torch.pow(y, gamma)
    y = torch.clamp(y, 0.0, 1.0)

    return y, gain_map_up
