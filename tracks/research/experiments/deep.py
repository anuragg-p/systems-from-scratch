"""Deep networks for module 04, and what they look like inside.

As in loop.py, the script that calls these passes its engine in (torch),
so they build and measure networks of whichever engine it named.
"""


def network(torch, depth, width, act="relu"):
    """depth linear layers, 784 -> width -> ... -> width -> 10, the activation ("relu", "tanh" or
    "sigmoid") after each but the last, every layer started as nn.Linear starts it."""
    nn = torch.nn
    sizes = [784] + [width] * (depth - 1) + [10]
    acts = {"relu": nn.ReLU, "tanh": nn.Tanh}
    acts["sigmoid"] = nn.Sigmoid                      # @from 04.03
    make = acts[act]
    layers = []
    for i, (n_in, n_out) in enumerate(zip(sizes[:-1], sizes[1:])):
        layers.append(nn.Linear(n_in, n_out))
        if i < depth - 1:
            layers.append(make())
    return nn.Sequential(*layers)


# @build 04.01 layer_stats
# Run the network on the batch one module at a time, keeping each
# activation's output (and asking it to keep its gradient), then backward
# from the cross-entropy. For each activation layer: the spread of its
# output over the batch (the standard deviation, over the examples, of each
# unit, averaged over the units: 0 when every digit gives the same output),
# the standard deviation of the gradient that arrived at it, and the
# fraction of its units that are dead (relu: 0 for every example) or
# saturated (tanh: beyond 0.99 in size).
def layer_stats(torch, model, x, y):
    nn = torch.nn
    h, outs = x, []
    for m in model:
        h = m(h)
        if isinstance(m, (nn.ReLU, nn.Tanh)):
            h.retain_grad()
            outs.append((m, h))
    torch.nn.functional.cross_entropy(h, y).backward()
    stats = []
    for m, a in outs:
        if isinstance(m, nn.ReLU):
            stuck = ((a > 0).float().sum(0) == 0).float().mean().item()
        else:
            stuck = (a.abs() > 0.99).float().mean().item()
        stats.append(dict(spread=a.std(0).mean().item(), grad=a.grad.std().item(), stuck=stuck))
    model.zero_grad()
    return stats
# @end
