"""04.04 Layer normalisation, and what the batch had to do with it

LayerNorm gives PyTorch's outputs and gradients (1e-6, float64); an example's output under batch
norm depends on its batchmates and under layer norm does not; layer norm takes a batch of one;
batch norm turns a batch of two into -1 and +1; and on batches of two the sigmoid network trains
far better with layer norm, on either engine.
"""


def test(t):
    T = t.track
    T.need(t, "mnist")
    T.inside(t, __file__)
    ours = T.experiment(t, "layernorm", "seeds=2", "steps=2000", "settings=[[2, 0.02]]")
    t.check(T.value(ours.out, r"^1\. batch norm, .* output (\S+)$") > 0.1, ours.out)
    t.check(T.value(ours.out, r"^1\. layer norm, .* output (\S+)$") < 1e-6, ours.out)
    t.check("2. batch norm, a batch of one: Expected more than 1 value" in ours.out
            and "2. layer norm, a batch of one: fine" in ours.out, ours.out)
    row = re.search(r"^3\. batch norm on a batch of two, .*: (.*)$", ours.out, re.M).group(1)
    t.check(all(abs(abs(float(v)) - 1) < 0.02 for v in row.replace(";", " ").split()), f"+-1 everywhere: {row}")
    bn = T.value(ours.out, r"batches of  2, .* batch norm: test accuracy (\S+)")
    ln = T.value(ours.out, r"batches of  2, .* layer norm: test accuracy (\S+)")
    t.check(ln > bn + 0.15, f"on batches of two, layer norm {ln} against batch norm {bn}")
    theirs = T.on_torch(t, "layernorm", "seeds=1", "steps=2000", "settings=[[2, 0.02]]")
    bn = T.value(theirs.out, r"batches of  2, .* batch norm: test accuracy (\S+)")
    ln = T.value(theirs.out, r"batches of  2, .* layer norm: test accuracy (\S+)")
    t.check(ln > bn + 0.15 and "layer norm, a batch of one: fine" in theirs.out, f"on PyTorch:\n{theirs.out}")


def inside(S):
    import numpy as np
    import engine
    import torch

    for shape in ((6, 5), (2, 3, 5)):
        ours = engine.nn.LayerNorm(5).double()
        theirs = S.copy_weights(ours, torch.nn.LayerNorm(5))
        rng = np.random.default_rng(len(shape))
        with torch.no_grad():
            theirs.weight += torch.tensor(rng.standard_normal(5))
        ours.weight.data[...] = theirs.weight.detach().numpy()
        a, b = S.pair([rng.standard_normal(shape) * 2 + 1])
        out, ref = ours(a[0]), theirs(b[0])
        S.same(out, ref, f"layer norm of {shape}")
        g = rng.standard_normal(shape)
        out.backward(engine.tensor(g))
        ref.backward(torch.tensor(g))
        S.same(a[0].grad, b[0].grad, f"its input gradient, {shape}")
        S.same(ours.weight.grad, theirs.weight.grad, f"its weight gradient, {shape}")
        S.same(ours.bias.grad, theirs.bias.grad, f"its bias gradient, {shape}")
    assert list(ours.state_dict()) == ["weight", "bias"]


import re  # noqa: E402
