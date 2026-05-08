from typing import Dict, Optional

import torch
import torch.nn.functional as F


def simple_ssim_loss(x: torch.Tensor, y: torch.Tensor, c1: float = 0.01 ** 2, c2: float = 0.03 ** 2) -> torch.Tensor:
    mu_x = F.avg_pool2d(x, kernel_size=3, stride=1, padding=1)
    mu_y = F.avg_pool2d(y, kernel_size=3, stride=1, padding=1)

    sigma_x = F.avg_pool2d(x * x, kernel_size=3, stride=1, padding=1) - mu_x * mu_x
    sigma_y = F.avg_pool2d(y * y, kernel_size=3, stride=1, padding=1) - mu_y * mu_y
    sigma_xy = F.avg_pool2d(x * y, kernel_size=3, stride=1, padding=1) - mu_x * mu_y

    ssim_n = (2 * mu_x * mu_y + c1) * (2 * sigma_xy + c2)
    ssim_d = (mu_x * mu_x + mu_y * mu_y + c1) * (sigma_x + sigma_y + c2)
    ssim_map = ssim_n / (ssim_d + 1e-8)
    return 1.0 - ssim_map.mean()


def exposure_loss(y: torch.Tensor, target: float = 0.5, patch: int = 16) -> torch.Tensor:
    mean = F.avg_pool2d(y, kernel_size=patch, stride=patch)
    return (mean - target).abs().mean()


def tv_loss(x: Optional[torch.Tensor]) -> torch.Tensor:
    if x is None:
        return torch.tensor(0.0)
    dx = (x[:, :, :, 1:] - x[:, :, :, :-1]).abs().mean()
    dy = (x[:, :, 1:, :] - x[:, :, :-1, :]).abs().mean()
    return dx + dy


def temporal_loss(y0: torch.Tensor, y1: torch.Tensor, t0: torch.Tensor, t1: torch.Tensor) -> torch.Tensor:
    return ((y0 - y1) - (t0 - t1)).abs().mean()


def param_reg(decoded: Dict[str, Optional[torch.Tensor]]) -> torch.Tensor:
    gain = decoded['gain_global']
    gamma = decoded['gamma_global']
    lift = decoded['lift_black']

    reg = torch.relu(gain - 2.3).mean()
    reg = reg + torch.relu(0.8 - gamma).mean()
    reg = reg + torch.relu(lift - 20.0).mean()
    return reg


def param_supervision_loss(
    decoded: Dict[str, Optional[torch.Tensor]],
    target: Dict[str, Optional[torch.Tensor]],
) -> torch.Tensor:
    loss = F.smooth_l1_loss(decoded['gain_global'], target['gain_global'])
    loss = loss + F.smooth_l1_loss(decoded['gamma_global'], target['gamma_global'])
    loss = loss + F.smooth_l1_loss(decoded['lift_black'], target['lift_black'])
    if decoded['gain_map'] is not None and target.get('gain_map') is not None:
        loss = loss + F.smooth_l1_loss(decoded['gain_map'], target['gain_map'])
    return loss


def build_image_loss(
    y_pred: torch.Tensor,
    y_target: torch.Tensor,
    decoded: Dict[str, Optional[torch.Tensor]],
    target_params: Optional[Dict[str, Optional[torch.Tensor]]] = None,
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, torch.Tensor]:
    weights = weights or {
        'l1': 1.0,
        'ssim': 0.5,
        'exposure': 0.2,
        'tv': 0.05,
        'reg': 0.05,
        'param': 0.5,
    }

    loss_l1 = F.l1_loss(y_pred, y_target)
    loss_ssim = simple_ssim_loss(y_pred, y_target)
    loss_exp = exposure_loss(y_pred)
    loss_tv = tv_loss(decoded['gain_map']).to(y_pred.device)
    loss_reg = param_reg(decoded)
    loss_param = torch.tensor(0.0, device=y_pred.device)
    if target_params is not None:
        loss_param = param_supervision_loss(decoded, target_params)

    total = (
        weights['l1'] * loss_l1
        + weights['ssim'] * loss_ssim
        + weights['exposure'] * loss_exp
        + weights['tv'] * loss_tv
        + weights['reg'] * loss_reg
        + weights['param'] * loss_param
    )

    return {
        'total': total,
        'l1': loss_l1,
        'ssim': loss_ssim,
        'exposure': loss_exp,
        'tv': loss_tv,
        'reg': loss_reg,
        'param': loss_param,
    }
