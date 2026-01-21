# mcml-reporting

One repo, one virtual environment, one command to run the full monthly MCML reporting
pipeline (SIM export → Slurm extraction → metrics → aggregation → plots → final tables).

## Goals

- **Single repo + single venv** using `uv`.
- **Single entrypoint**: `mcml-report --months-back N`.
- **One monthly cron job** writing to a dated output folder.
- **Consistent output layout**:

```
output/YYYY-MM-DD/
├── sim/        # SIM exports
├── slurm/      # Slurm metrics and CSVs
├── plots/      # All figures
└── project-information.csv
```

## Recommended project layout

```
mcml-reporting/
├── pyproject.toml
├── src/
│   └── mcml_reporting/
│       ├── __init__.py
│       └── cli.py  # defines mcml-report
└── output/
```

## 1) Create the single uv environment

Quick setup (recommended):

```bash
git clone git@github.com:YOUR_ORG/mcml-reporting.git
cd mcml-reporting
./scripts/bootstrap.sh
```

Manual setup:

```bash
uv venv
source .venv/bin/activate
```

Install both tools into the same environment. If you want editable installs from their
Git repositories (recommended for development):

```bash
uv pip install -e "git+ssh://git@github.com/m-a-r-o-u/sim.git"
uv pip install -e "git+ssh://git@github.com/m-a-r-o-u/slurm.git"
```

Alternatively, if you prefer local clones:

```bash
git clone git@github.com:m-a-r-o-u/sim.git ../sim
git clone git@github.com:m-a-r-o-u/slurm.git ../slurm
uv pip install -e ../sim
uv pip install -e ../slurm
```

## 2) Define the single command

Add a `console_scripts` entry in `pyproject.toml` so the command
`mcml-report` is always available when the venv is active:

```toml
[project]
name = "mcml-reporting"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
  "sim-app @ git+ssh://git@github.com/m-a-r-o-u/sim.git",
  "slurm-utils @ git+ssh://git@github.com/m-a-r-o-u/slurm.git",
]

[project.scripts]
mcml-report = "mcml_reporting.cli:main"
```

The CLI is implemented in `src/mcml_reporting/cli.py` and will:

- Accept `--months-back N`.
- Create a dated output folder.
- Run each step in order.
- Keep SIM and Slurm outputs in their subfolders.
- Support `--dry-run` for safe previews.

## 3) CLI flow (single script)

The `mcml-report` command should do the equivalent of the following shell flow
(plus parameterized months-back and explicit paths):

```bash
# common setup
RUN_DATE="$(date +%Y-%m-%d)"
BASE="./output/${RUN_DATE}"
SIM_OUT="${BASE}/sim"
SLURM_OUT="${BASE}/slurm"
PLOT_OUT="${BASE}/plots"

mkdir -p "$SIM_OUT" "$SLURM_OUT" "$PLOT_OUT"

# SIM
sim-app user-projects-membership > "$SIM_OUT/user-projects-map.txt"
sim-app list-institution-heads AI --filter '*ai-h-mcml' > "$SIM_OUT/project-pi-map-mcml.txt"

# Slurm: export missing data and build metrics
slurm-utils export-sacct --date lastM:${MONTHS_BACK} --missing
slurm-utils metrics build
slurm-utils metrics accounts-work-around --ifile "$SIM_OUT/user-projects-map.txt"

# Aggregate + plot
slurm-utils metrics query gpu_hours --by ${MONTHS_BACK}months,account --format csv \
  --select partition:mcml* > "$SLURM_OUT/gpuhours-by-accounts.csv"

slurm-plot donut-chart-gpuhours \
  --input "$SLURM_OUT/gpuhours-by-accounts.csv" \
  --output "$PLOT_OUT/donut-chart-gpuhours.png" \
  --norm true

slurm-plot horizontal-bar-chart-gpuhours \
  --input "$SLURM_OUT/gpuhours-by-accounts.csv" \
  --output "$PLOT_OUT/horizontal-bar-chart-gpuhours.png" \
  --norm true

slurm-plot project-information \
  --input-pi "$SIM_OUT/project-pi-map-mcml.txt" \
  --input-gpuh "$SLURM_OUT/gpuhours-by-accounts.csv" \
  --format csv \
  --output "$BASE/project-information.csv"
```

## 4) Cron job example (monthly)

```cron
# Run on the 1st of each month at 07:30
30 7 1 * * cd /path/to/mcml-reporting && \
  . .venv/bin/activate && \
  mcml-report --months-back 12 >> ./output/cron.log 2>&1
```

## 5) Why this setup is better

- **Single venv** avoids version drift between SIM and Slurm tools.
- **One CLI** removes manual steps and makes cron reliable.
- **Dated output directories** make runs reproducible and auditable.
- **Parameterization** of `--months-back` enables flexible reporting windows.

## Usage

```bash
mcml-report --months-back 12
```

Preview the commands without executing them:

```bash
mcml-report --months-back 12 --dry-run
```
