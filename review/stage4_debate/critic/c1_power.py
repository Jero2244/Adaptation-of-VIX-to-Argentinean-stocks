"""c1: false-pass and false-fail of the draft rules. Block-resampled pre-2025-03 panel rows, b forced to each target.
Usage: c1_power.py sims reps blocks kinds tag"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sim_core import run
HERE = os.path.dirname(os.path.abspath(__file__))
sims, reps = int(sys.argv[1]), int(sys.argv[2])
blocks = [int(a) for a in sys.argv[3].split(",")]
kinds = sys.argv[4].split(",")
tag = sys.argv[5]
for kind in kinds:
    for b in blocks:
        df, meta = run(kind, sims, reps, b, 20261104 + b)
        df.to_pickle(os.path.join(HERE, f"c1_{tag}_{kind}_{b}.pkl"))
        print(meta, flush=True)
