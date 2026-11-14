"""lab: the runner every experiment uses. It knows nothing about tensors, so it serves any
engine: settings, seeds and logs (run.py), the spread of a result over seeds (stats.py),
curves drawn from logs (plot.py), checkpoints (safetensors.py) and the debugging
checklist (checks.py)."""

from lab.run import Config, Run, config, read_log                  # @from 00.02
from lab.stats import mean, sd, spread, welch_t                     # @from 00.03
from lab.plot import Line, lines                                    # @from 00.03
from lab.schedule import warmup_cosine                              # @from 03.05
