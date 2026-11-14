"""Learning-rate schedules: torch.optim.lr_scheduler.

A schedule changes the "lr" of an optimiser's param_groups as training
goes on. LambdaLR takes any function of the step number and multiplies the
learning rate each group started with by it: warmup, cosine decay, or both.
"""


# @build 03.05 LambdaLR
# Remember each group's starting lr, then set it to start * lr_lambda(0)
# straight away (PyTorch does that step on construction). Each step() after
# that counts one more (last_epoch, as PyTorch names it, though it is
# usually a step) and sets lr = start * lr_lambda(count). get_last_lr()
# gives the lrs now set.
class LambdaLR:
    def __init__(self, optimizer, lr_lambda):
        self.optimizer = optimizer
        self.lr_lambda = lr_lambda
        self.base_lrs = [group["lr"] for group in optimizer.param_groups]
        self.last_epoch = -1
        self.step()

    def step(self):
        self.last_epoch += 1
        for group, base in zip(self.optimizer.param_groups, self.base_lrs):
            group["lr"] = base * self.lr_lambda(self.last_epoch)

    def get_last_lr(self):
        return [group["lr"] for group in self.optimizer.param_groups]
# @end
