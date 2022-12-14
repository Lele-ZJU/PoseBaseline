"""
# --------------------------------------------------------
# @Project: MyPoseNet
# @Author : Hanle
# @E-mail : hanle@zju.edu.cn
# @Date   : 2021-06-17
# --------------------------------------------------------
"""

import torch
import torch.nn as nn
from tqdm import tqdm

from torch.autograd import Function

class DiceCoeff(Function):
    """Dice coeff for individual examples"""

    def forward(self, input, target):
        self.save_for_backward(input, target)
        eps = 0.0001
        self.inter = torch.dot(input.view(-1), target.view(-1))
        self.union = torch.sum(input) + torch.sum(target) + eps

        t = (2 * self.inter.float() + eps) / self.union.float()
        return t

    # This function has only a single output, so it gets only one gradient
    def backward(self, grad_output):

        input, target = self.saved_variables
        grad_input = grad_target = None

        if self.needs_input_grad[0]:
            grad_input = grad_output * 2 * (target * self.union - self.inter) \
                         / (self.union * self.union)
        if self.needs_input_grad[1]:
            grad_target = None

        return grad_input, grad_target


def dice_coeff(input, target):
    """Dice coeff for batches"""
    if input.is_cuda:
        s = torch.FloatTensor(1).cuda().zero_()
    else:
        s = torch.FloatTensor(1).zero_()

    for i, c in enumerate(zip(input, target)):
        s = s + DiceCoeff().forward(c[0], c[1])

    return s / (i + 1)


def eval_net(net, loader, device):
    """Evaluation without the densecrf with the dice coefficient"""
    net.eval()
    heatmap_type = torch.float32
    n_val = len(loader)  # the number of batch
    tot = 0

    criterion = nn.MSELoss()

    with tqdm(total=n_val, desc='Validation round', unit='batch', leave=False) as pbar:
        for batch in loader:
            imgs, true_heatmaps = batch['image'], batch['heatmap']
            imgs = imgs.to(device=device, dtype=torch.float32)
            true_heatmaps = true_heatmaps.to(device=device, dtype=heatmap_type)

            with torch.no_grad():
                heatmaps_pred = net(imgs)

            loss_mse = criterion(heatmaps_pred, true_heatmaps).item()
            tot = loss_mse  # + loss_similar
            pbar.update()

    net.train()
    return tot / n_val
