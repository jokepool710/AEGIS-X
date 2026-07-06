import csv
import json
from dataclasses import asdict, dataclass
from itertools import product
from pathlib import Path
from statistics import fmean, pstdev

from aegis.detection.pipeline import DetectionPipeline
from aegis.evaluation.harness import DetectionEvaluationHarness
from aegis.evaluation.scenarios import AttackEpisode, CPSAttackScenarioGenerator

ATTACK_TYPES = (
    "sensor_spoofing",
    "drift_injection",
    "spike",
    "replay",
    "stuck_at_value",
    "gradual_degradation",
)


@dataclass(frozen=True)
class ExperimentConfig:
    seeds: tuple[int, ...] = (1, 7, 42)
    attack_types: tuple[str, ...] = ATTACK_TYPES
    magnitudes: tuple[float, ...] = (1.0, 3.0, 6.0)
    thresholds: tuple[float, ...] = (0.55, 0.65, 0.75)
    length: int = 240
    attack_start: int = 100
    attack_end: int = 150
    warmup: int = 20
    window_size: int = 60
    retrain_interval: int = 20


@dataclass(frozen=True)
class ExperimentRow:
    seed: int
    attack_type: str
    magnitude: float
    threshold: float
    precision: float
    recall: float
    f1: float
    false_positive_rate: float
    mean_detection_delay: float | None
    detected_attack_episodes: int
    total_attack_episodes: int


class ExperimentRunner:
    def __init__(self, config: ExperimentConfig) -> None:
        self.config = config

    def run(self) -> list[ExperimentRow]:
        rows: list[ExperimentRow] = []
        combinations = product(
            self.config.seeds,
            self.config.attack_types,
            self.config.magnitudes,
            self.config.thresholds,
        )
        for seed, attack_type, magnitude, threshold in combinations:
            samples = CPSAttackScenarioGenerator(seed=seed).generate(
                length=self.config.length,
                episodes=[
                    AttackEpisode(
                        attack_type=attack_type,
                        start=self.config.attack_start,
                        end=self.config.attack_end,
                        magnitude=magnitude,
                    )
                ],
            )
            pipeline = DetectionPipeline(
                window_size=self.config.window_size,
                warmup=self.config.warmup,
                threshold=threshold,
                retrain_interval=self.config.retrain_interval,
            )
            metrics = DetectionEvaluationHarness(pipeline).run(samples).metrics
            rows.append(
                ExperimentRow(
                    seed=seed,
                    attack_type=attack_type,
                    magnitude=magnitude,
                    threshold=threshold,
                    precision=metrics.precision,
                    recall=metrics.recall,
                    f1=metrics.f1,
                    false_positive_rate=metrics.false_positive_rate,
                    mean_detection_delay=metrics.mean_detection_delay,
                    detected_attack_episodes=metrics.detected_attack_episodes,
                    total_attack_episodes=metrics.total_attack_episodes,
                )
            )
        return rows

    @staticmethod
    def aggregate(rows: list[ExperimentRow]) -> list[dict[str, object]]:
        groups: dict[tuple[str, float, float], list[ExperimentRow]] = {}
        for row in rows:
            groups.setdefault((row.attack_type, row.magnitude, row.threshold), []).append(row)

        aggregates: list[dict[str, object]] = []
        for (attack_type, magnitude, threshold), group in sorted(groups.items()):
            item: dict[str, object] = {
                "attack_type": attack_type,
                "magnitude": magnitude,
                "threshold": threshold,
                "runs": len(group),
            }
            for field in ("precision", "recall", "f1", "false_positive_rate"):
                values = [float(getattr(row, field)) for row in group]
                item[f"{field}_mean"] = fmean(values)
                item[f"{field}_std"] = pstdev(values) if len(values) > 1 else 0.0
            delays = [row.mean_detection_delay for row in group if row.mean_detection_delay is not None]
            item["mean_detection_delay"] = fmean(delays) if delays else None
            item["episode_detection_rate"] = sum(
                row.detected_attack_episodes for row in group
            ) / max(1, sum(row.total_attack_episodes for row in group))
            aggregates.append(item)
        return aggregates

    def write_artifacts(self, output_dir: Path) -> dict[str, Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        rows = self.run()
        aggregates = self.aggregate(rows)
        raw_csv = output_dir / "experiment_runs.csv"
        summary_csv = output_dir / "experiment_summary.csv"
        report_json = output_dir / "experiment_report.json"

        with raw_csv.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(asdict(rows[0]).keys()))
            writer.writeheader()
            writer.writerows(asdict(row) for row in rows)

        with summary_csv.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(aggregates[0].keys()))
            writer.writeheader()
            writer.writerows(aggregates)

        report_json.write_text(
            json.dumps(
                {
                    "config": asdict(self.config),
                    "run_count": len(rows),
                    "runs": [asdict(row) for row in rows],
                    "aggregates": aggregates,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return {"runs_csv": raw_csv, "summary_csv": summary_csv, "report_json": report_json}
