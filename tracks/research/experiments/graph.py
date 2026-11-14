"""A graph of Values, and backward() through it, held to the nudge.

One neuron with two inputs, written out as arithmetic on Values:
o = tanh(x1 w1 + x2 w2 + b). Building it builds the graph; o.backward()
fills every node's gradient. The script prints each node (its operation,
value and gradient), then checks the gradients of the five inputs against
the nudge of 01.01: the same numbers, two ways.

    python3 -m experiments.graph
"""

import lab
from engine import nudge
from engine.value import Value

CONFIG = dict(x1=1.5, x2=-0.5, w1=0.8, w2=-1.2, b=-1.0)
NAMES = ("x1", "x2", "w1", "w2", "b")


# @build 01.02 neuron
# The neuron's output from five inputs, Values or plain floats alike (the
# nudge calls it with floats, inside a Value each time): tanh of the
# weighted sum plus the bias. Returns the output and the nodes in the
# order they were made, named, for printing.
def neuron(x1, x2, w1, w2, b):
    x1, x2, w1, w2, b = (v if isinstance(v, Value) else Value(v) for v in (x1, x2, w1, w2, b))
    x1w1 = x1 * w1
    x2w2 = x2 * w2
    s = x1w1 + x2w2
    n = s + b
    o = n.tanh()
    return o, [("x1", x1), ("x2", x2), ("w1", w1), ("w2", w2), ("b", b), ("x1*w1", x1w1),
               ("x2*w2", x2w2), ("x1*w1 + x2*w2", s), ("n = ... + b", n), ("o = tanh(n)", o)]
# @end


def main():
    cfg = lab.config(CONFIG)
    inputs = [cfg[k] for k in NAMES]
    o, nodes = neuron(*inputs)
    o.backward()
    print(f"{'node':16s} {'op':5s} {'value':>10s} {'grad':>10s}")
    for name, v in nodes:
        print(f"{name:16s} {v._op or '-':5s} {v.data:10.4f} {v.grad:10.4f}")
    nudged = nudge.gradient(lambda xs: neuron(*xs)[0].data, inputs)
    worst = 0.0
    for (name, v), est in zip(nodes, nudged):
        worst = max(worst, abs(v.grad - est))
        print(f"d o / d {name:3s}: backward {v.grad:+.8f}  nudge {est:+.8f}")
    print(f"largest difference from the nudge: {worst:.1e}")


if __name__ == "__main__":
    main()
