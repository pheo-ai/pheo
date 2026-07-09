# Code Agent Demo

Run the packaged demo from a clone:

```bash
python3.13 examples/code_agent/run_demo.py --reset
```

Or from an installed wheel:

```bash
pheo demo code-agent --reset
```

The demo attaches PHEO to final coding-agent output, blocks release until review, captures a maintainer decision with a reason, then applies that judgment memory on a similar Cycle 2 case.
