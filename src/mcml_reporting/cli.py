import argparse
import datetime as dt
import subprocess
from pathlib import Path
from typing import Iterable


def run_command(command: Iterable[str], *, stdout_path: Path | None, dry_run: bool) -> None:
    command_list = list(command)
    if dry_run:
        target = f" > {stdout_path}" if stdout_path else ""
        print(f"[dry-run] {' '.join(command_list)}{target}")
        return

    if stdout_path:
        stdout_path.parent.mkdir(parents=True, exist_ok=True)
        with stdout_path.open("w", encoding="utf-8") as handle:
            subprocess.run(command_list, check=True, stdout=handle)
    else:
        subprocess.run(command_list, check=True)


def build_paths(output_root: Path, run_date: str) -> dict[str, Path]:
    base = output_root / run_date
    return {
        "base": base,
        "sim": base / "sim",
        "slurm": base / "slurm",
        "plots": base / "plots",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run MCML monthly reporting pipeline.")
    parser.add_argument(
        "--months-back",
        type=int,
        default=12,
        help="Number of months to include in the report (default: 12).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Root output directory for report artifacts.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands without executing them.",
    )
    args = parser.parse_args()

    run_date = dt.date.today().isoformat()
    paths = build_paths(args.output_dir, run_date)

    for key in ("sim", "slurm", "plots"):
        paths[key].mkdir(parents=True, exist_ok=True)

    run_command(
        ["sim-app", "user-projects-membership"],
        stdout_path=paths["sim"] / "user-projects-map.txt",
        dry_run=args.dry_run,
    )
    run_command(
        ["sim-app", "list-institution-heads", "AI", "--filter", "*ai-h-mcml"],
        stdout_path=paths["sim"] / "project-pi-map-mcml.txt",
        dry_run=args.dry_run,
    )

    run_command(
        ["slurm-utils", "export-sacct", "--date", f"lastM:{args.months_back}", "--missing"],
        stdout_path=None,
        dry_run=args.dry_run,
    )
    run_command(
        ["slurm-utils", "metrics", "build"],
        stdout_path=None,
        dry_run=args.dry_run,
    )
    run_command(
        [
            "slurm-utils",
            "metrics",
            "accounts-work-around",
            "--ifile",
            str(paths["sim"] / "user-projects-map.txt"),
        ],
        stdout_path=None,
        dry_run=args.dry_run,
    )

    gpuhours_csv = paths["slurm"] / "gpuhours-by-accounts.csv"
    run_command(
        [
            "slurm-utils",
            "metrics",
            "query",
            "gpu_hours",
            "--by",
            f"{args.months_back}months,account",
            "--format",
            "csv",
            "--select",
            "partition:mcml*",
        ],
        stdout_path=gpuhours_csv,
        dry_run=args.dry_run,
    )

    run_command(
        [
            "slurm-plot",
            "donut-chart-gpuhours",
            "--input",
            str(gpuhours_csv),
            "--output",
            str(paths["plots"] / "donut-chart-gpuhours.png"),
            "--norm",
            "true",
        ],
        stdout_path=None,
        dry_run=args.dry_run,
    )
    run_command(
        [
            "slurm-plot",
            "horizontal-bar-chart-gpuhours",
            "--input",
            str(gpuhours_csv),
            "--output",
            str(paths["plots"] / "horizontal-bar-chart-gpuhours.png"),
            "--norm",
            "true",
        ],
        stdout_path=None,
        dry_run=args.dry_run,
    )

    run_command(
        [
            "slurm-plot",
            "project-information",
            "--input-pi",
            str(paths["sim"] / "project-pi-map-mcml.txt"),
            "--input-gpuh",
            str(gpuhours_csv),
            "--format",
            "csv",
            "--output",
            str(paths["base"] / "project-information.csv"),
        ],
        stdout_path=None,
        dry_run=args.dry_run,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
