"""The runner: the settings, the seed and the log of every run, kept on disk.

An experiment declares its settings as a dictionary of defaults, CONFIG at
the top of its file. config() starts from those and takes key=value pairs
from the command line, so a run is changed without editing the script:

    python3 -m experiments.curve lr=0.1 steps=500

A Run is one run of an experiment, with one seed, in a directory of its
own under out/ (default runs/<experiment>/[label/]seed<seed>/):

    config.json    every setting the run used, and its seed
    log.jsonl      one line of JSON per logged step: {"step": 100, "loss": 0.25}
    summary.json   the run's final numbers

Nothing in them depends on the clock or the machine's state: the same
settings and seed give the same files, byte for byte, on the same machine.
That is what makes a result something another person can check.
"""

import ast
import json
import os
import sys

import numpy as np


class Config(dict):
    """The settings of a run: a dictionary whose keys can also be read as attributes (cfg.lr)."""

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(f"no setting {key!r}") from None


# @build 00.02 config
# The defaults, overridden by key=value arguments (argv, else the command
# line). A value is read as a Python literal (0.1, 500, [1, 2], True), or
# as text when it is not one; an int given for a float setting becomes a
# float. A key the defaults do not have, or anything that is not key=value,
# stops the script with exit status 2 and one line listing the settings.
# "out" (where runs are written) is always a setting, "runs" unless given.
# "name" is the experiment's name, from the script's file name.
def config(defaults, argv=None):
    argv = sys.argv[1:] if argv is None else argv
    name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
    cfg = Config(defaults)
    cfg.setdefault("out", "runs")
    for arg in argv:
        key, eq, text = arg.partition("=")
        if not eq or key not in cfg:
            print(f"{name}: no setting {key!r} (settings: {', '.join(f'{k}={cfg[k]!r}' for k in cfg)})",
                  file=sys.stderr)
            sys.exit(2)
        try:
            value = ast.literal_eval(text)
        except (ValueError, SyntaxError):
            value = text
        if isinstance(cfg[key], float) and isinstance(value, int) and not isinstance(value, bool):
            value = float(value)
        cfg[key] = value
    cfg["name"] = name
    return cfg
# @end


class Run:
    """One run: its directory, its random numbers (rng), its log."""

    # @build 00.02 __init__
    # Make the run's directory, out/<experiment>/<label>/seed<seed> (no label
    # level when label is ""), write config.json there (the settings, the
    # label and the seed, keys sorted), open log.jsonl for writing (a new file:
    # a run started again replaces the old one), and make rng, a numpy
    # Generator seeded with seed: every random number the run draws comes
    # from it, so the seed decides them all.
    def __init__(self, cfg, seed, label=""):
        self.seed = seed
        self.dir = os.path.join(cfg.out, cfg.name, *([label] if label else []), f"seed{seed}")
        os.makedirs(self.dir, exist_ok=True)
        with open(os.path.join(self.dir, "config.json"), "w") as f:
            json.dump({**cfg, "label": label, "seed": seed}, f, indent=1, sort_keys=True)
            f.write("\n")
        self._log = open(os.path.join(self.dir, "log.jsonl"), "w")
        self.rows = []
        self.rng = np.random.default_rng(seed)
    # @end

    # @build 00.02 log
    # One line of the log: the values given, as one JSON object, written at
    # once (a run that crashes keeps its log so far), and kept in self.rows.
    # Floats are written in full (repr), so nothing is rounded away.
    def log(self, **values):
        values = {k: float(v) if isinstance(v, (float, np.floating)) else v for k, v in values.items()}
        self.rows.append(values)
        self._log.write(json.dumps(values) + "\n")
        self._log.flush()
    # @end

    # @build 00.02 finish
    # The run's final numbers: written to summary.json (keys sorted), kept in
    # self.summary, returned. The log is closed.
    def finish(self, **values):
        self.summary = {k: float(v) if isinstance(v, (float, np.floating)) else v for k, v in values.items()}
        with open(os.path.join(self.dir, "summary.json"), "w") as f:
            json.dump(self.summary, f, indent=1, sort_keys=True)
            f.write("\n")
        self._log.close()
        return self.summary
    # @end


def read_log(directory):
    """The rows of a run's log.jsonl, as dictionaries."""
    with open(os.path.join(directory, "log.jsonl")) as f:
        return [json.loads(line) for line in f if line.strip()]
