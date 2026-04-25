# EvolveSignal

A coding agent for discovering traffic signal control strategies.

This repository contains the open-source implementation of the paper:

**EvolveSignal: A Large Language Model Powered Coding Agent for Discovering Traffic Signal Control Strategies**  
arXiv: <https://arxiv.org/abs/2509.03335>

## Acknowledgments

The evolutionary LLM framework in this project is **based on and derived from** [OpenEvolve](https://github.com/algorithmicsuperintelligence/openevolve) (open-source, Apache-2.0). We are grateful to the OpenEvolve authors; see their repository for the upstream design and additional examples.

## Overview

EvolveSignal couples OpenEvolve-style program evolution with SUMO/TraCI traffic simulations to search for better signal timing policies. The traffic example lives under `examples/traffic_signal_control/`.

## Environment (conda)

```bash
conda create -n evolvesignal-v1 python=3.10
conda activate evolvesignal-v1
cd /path/to/this/repo
pip install -e ".[dev]"
pip install traci
```

- **python-dotenv** is declared in `pyproject.toml` and used to load API keys from `.env`.
- **traci** is the SUMO Python API. You may also rely on the `traci` package shipped under `$SUMO_HOME/tools` after SUMO is installed; installing `traci` via `pip` is the simplest cross-platform approach.

## SUMO

Install SUMO: <https://sumo.dlr.de/docs/Installing/index.html>

**Windows**

- Use the official installer. Typical install root: `C:\Program Files (x86)\Eclipse\Sumo`.
- The code tries to set `SUMO_HOME` and add `$SUMO_HOME\tools` to `sys.path` before importing `traci` / `sumolib`. If imports fail, set `SUMO_HOME` manually in **System Environment Variables** or in `.env` (see `.env.example`).
- Add the SUMO `bin` directory to your `PATH` if `sumo` is not found (`checkBinary`).

**Linux**

- e.g. `sudo apt install sumo sumo-tools` — layout is often `/usr/share/sumo` (with a `tools/` subfolder). The same auto-detection runs; override with `export SUMO_HOME=/usr/share/sumo` if needed.
- Ensure `sumo` is on your `PATH` in the same shell/IDE you use to run Python.

**Windows vs Linux (summary)**

| Topic | Windows | Linux |
|--------|---------|--------|
| `SUMO_HOME` | Often `...\Eclipse\Sumo`; set explicitly if auto-detect fails | Often `/usr/share/sumo` or from distro packages |
| Paths in configs | Use `openevolve-run.py` (see below) so `template_dir` stays relative; avoid hardcoded `/home/...` | Same; no path changes required if you use the default run entry |
| Console encoding | Prefer UTF-8 in the terminal; template `.txt` files are read as UTF-8 | Same |

No Linux-specific code paths are required for normal use: **the same repo runs on both**; only environment variables and SUMO layout differ.

## API keys and models

1. Copy `.env.example` to `.env` in the project root.
2. Set `OPENROUTER_API_KEY` (or match what you use in `examples/traffic_signal_control/config.yaml`).

The default `config.yaml` uses **OpenRouter**-compatible `api_base` for listed models. Adjust `llm` / `models` in that file for other providers.

## How to run

From the **repository root**:

```bash
python openevolve-run.py
```

With no arguments, this `chdir`s to `examples/traffic_signal_control`, loads `config.yaml` there, and uses `initial_program.py` and `evaluator.py`. You can also invoke the CLI explicitly (this fork uses **flag** arguments, not positionals):

```bash
python openevolve-run.py --initial_program examples/traffic_signal_control/initial_program.py \
  --evaluation_file examples/traffic_signal_control/evaluator.py \
  -c examples/traffic_signal_control/config.yaml
```

If you already `cd` into `examples/traffic_signal_control`, use the short filenames in `--initial_program` and `--evaluation_file` as in the `openevolve-run.py` default (see that script).

## Project layout (traffic example)

- `examples/traffic_signal_control/config.yaml` — LLM, evaluator, and `prompt.template_dir` (relative: `Prompt_Templates`).
- `examples/traffic_signal_control/Intersections/` — SUMO `*.sumocfg` / network files.
- `openevolve-run.py` — convenient entry for PyCharm or terminal.

## License

See the upstream `LICENSE` / `pyproject.toml` (Apache-2.0) unless you add a separate `LICENSE` for this fork.
