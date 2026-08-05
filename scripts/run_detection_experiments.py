import argparse
from pathlib import Path

from aegis.evaluation.experiments import ExperimentConfig, ExperimentRunner


def main() -> None:
    parser = argparse.ArgumentParser(description="Run reproducible AEGIS-X detection experiments")
    parser.add_argument("--output", type=Path, default=Path("artifacts/evaluation"))
    parser.add_argument("--quick", action="store_true", help="run a small smoke experiment matrix")
    args = parser.parse_args()

    config = (
        ExperimentConfig(
            seeds=(42,),
            attack_types=("sensor_spoofing", "drift_injection", "stuck_at_value"),
            magnitudes=(3.0,),
            thresholds=(0.65,),
            length=160,
            attack_start=70,
            attack_end=110,
        )
        if args.quick
        else ExperimentConfig()
    )
    paths = ExperimentRunner(config).write_artifacts(args.output)
    print(f"experiment matrix complete: {sum(1 for _ in config.seeds) * len(config.attack_types) * len(config.magnitudes) * len(config.thresholds)} runs")
    for name, path in paths.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
