"""01.03 A neuron, a layer, a network

MLP(2, [4, 4, 1]) has 37 weights; its output and every weight's gradient are PyTorch's for the
same weights (1e-6); a seed gives the same weights twice; and the experiment's nudges agree with
backward() for every weight.
"""


def test(t):
    T = t.track
    T.inside(t, __file__)
    r = T.experiment(t, "network")
    lines = [l for l in r.out.splitlines() if l.startswith("seed ")]
    t.check(len(lines) == 3 and all("37 weights" in l for l in lines), f"three seeds, 37 weights:\n{r.out}")
    for line in lines:
        t.check(T.value(line, r"from the nudge (\S+)") < 1e-6, f"backward and nudge differ: {line}")


def inside(S):
    import numpy as np
    import torch
    from engine.value import MLP, Layer, Neuron

    model = MLP(2, [4, 4, 1], seed=0)
    assert len(model.parameters()) == 37, len(model.parameters())
    again = MLP(2, [4, 4, 1], seed=0)
    assert [p.data for p in again.parameters()] == [p.data for p in model.parameters()], "a seed, the same weights"
    assert len(Layer(3, 5, __import__("random").Random(1))([1.0, 2.0, 3.0])) == 5
    assert len(MLP(3, [5, 2], seed=1)([1.0, -1.0, 0.5])) == 2, "two outputs come back as a list"
    assert Neuron(2, __import__("random").Random(2), linear=True)([0.0, 0.0]).data == 0.0, "bias starts at 0"
    x = [0.5, -1.5]
    out = model(x)
    out.backward()
    tx = torch.tensor(x, dtype=torch.float64)
    weights = []
    h = tx
    for i, layer in enumerate(model.layers):
        w = torch.tensor([[wi.data for wi in n.w] for n in layer.neurons], dtype=torch.float64, requires_grad=True)
        b = torch.tensor([n.b.data for n in layer.neurons], dtype=torch.float64, requires_grad=True)
        weights.append((layer, w, b))
        h = w @ h + b
        if i < len(model.layers) - 1:
            h = h.relu()
    h[0].backward()
    S.same(out.data, h[0], "the network's output")
    for layer, w, b in weights:
        S.same(np.array([[wi.grad for wi in n.w] for n in layer.neurons]), w.grad, "the weights' gradients")
        S.same(np.array([n.b.grad for n in layer.neurons]), b.grad, "the biases' gradients")
