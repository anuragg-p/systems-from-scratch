"""Derivatives by nudging: move an input a little and watch the output.

The derivative of f at x is how much f(x) moves per unit that x moves, for
a very small move. Nudging x by h each way and dividing the change in f
by 2h estimates it with nothing but two calls to f. No formula is needed,
so this is the check every derivative in the track is held to: a gradient
worked out by hand, or by backpropagation, must agree with the nudge.

The estimate is not exact, and h decides how far off it is. A big h measures
the slope of a chord, not of the curve. A tiny h subtracts two nearly equal
numbers, and the digits that cancel take the answer with them.
"""


# @build 01.01 derivative
# The slope of f at x by a central difference: f(x + h) and f(x - h), their
# difference over 2h. f takes one float and returns one float.
def derivative(f, x, h=1e-6):
    return (f(x + h) - f(x - h)) / (2 * h)
# @end


# @build 01.01 gradient
# Every partial derivative of f at the point xs (a list of floats): nudge
# one coordinate at a time, both ways, and leave the others where they are.
# f takes a list of floats and returns one float. Returns a list of floats,
# one per coordinate.
def gradient(f, xs, h=1e-6):
    grads = []
    for i in range(len(xs)):
        up = list(xs)
        down = list(xs)
        up[i] += h
        down[i] -= h
        grads.append((f(up) - f(down)) / (2 * h))
    return grads
# @end
