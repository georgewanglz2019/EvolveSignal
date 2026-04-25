#!/usr/bin/env python
"""
Entry point for OpenEvolve / EvolveSignal.

With no arguments (e.g. Run in the IDE), defaults to the traffic_signal_control
example. Working directory is set to that example so template_dir and SUMO
paths in Intersections/ resolve on any machine.
"""
import os
import sys

if __name__ == "__main__":
    from dotenv import load_dotenv

    _root = os.path.dirname(os.path.abspath(__file__))
    # Prefer repo-root .env (not committed; see .env.example)
    load_dotenv(os.path.join(_root, ".env"))

    # This fork's CLI (openevolve/cli.py) only accepts --initial_program / --evaluation_file, not positionals.
    if len(sys.argv) == 1:
        example_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "examples",
            "traffic_signal_control",
        )
        os.chdir(example_dir)
        cfg = os.path.join(example_dir, "config.yaml")
        sys.argv = [
            sys.argv[0],
            "--initial_program",
            "initial_program.py",
            "--evaluation_file",
            "evaluator.py",
            "--config",
            cfg,
        ]

    from openevolve.cli import main

    sys.exit(main())
