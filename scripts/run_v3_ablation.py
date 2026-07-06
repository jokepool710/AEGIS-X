import csv
from dataclasses import asdict
from pathlib import Path

from aegis.detection.pipeline import DetectionPipeline
from aegis.evaluation.experiments import ExperimentConfig, ExperimentRow
from aegis.evaluation.harness import DetectionEvaluationHarness
from aegis.evaluation.scenarios import AttackEpisode, CPSAttackScenarioGenerator

VARIANTS = {
    "v1_point": (False, False),
    "v2_point_temporal": (True, False),
    "v3_full": (True, True),
}


def main() -> None:
    config = ExperimentConfig()
    output = Path("artifacts/ablation")
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for variant, (temporal, contextual) in VARIANTS.items():
        for seed in config.seeds:
            for attack_type in config.attack_types:
                for magnitude in config.magnitudes:
                    for threshold in config.thresholds:
                        samples = CPSAttackScenarioGenerator(seed=seed).generate(
                            config.length,
                            [AttackEpisode(attack_type, config.attack_start, config.attack_end, magnitude)],
                        )
                        pipeline = DetectionPipeline(
                            window_size=config.window_size, warmup=config.warmup,
                            threshold=threshold, retrain_interval=config.retrain_interval,
                            enable_temporal=temporal, enable_contextual=contextual,
                        )
                        metrics = DetectionEvaluationHarness(pipeline).run(samples).metrics
                        row = asdict(ExperimentRow(
                            seed, attack_type, magnitude, threshold, metrics.precision,
                            metrics.recall, metrics.f1, metrics.false_positive_rate,
                            metrics.mean_detection_delay, metrics.detected_attack_episodes,
                            metrics.total_attack_episodes,
                        ))
                        row["variant"] = variant
                        rows.append(row)

    raw = output / "ablation_runs.csv"
    fields = ["variant"] + [key for key in rows[0] if key != "variant"]
    with raw.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    summary = output / "ablation_summary.csv"
    summary_rows = []
    for variant in VARIANTS:
        for attack_type in config.attack_types:
            group = [r for r in rows if r["variant"] == variant and r["attack_type"] == attack_type]
            summary_rows.append({
                "variant": variant,
                "attack_type": attack_type,
                "runs": len(group),
                "precision": sum(r["precision"] for r in group) / len(group),
                "recall": sum(r["recall"] for r in group) / len(group),
                "f1": sum(r["f1"] for r in group) / len(group),
                "false_positive_rate": sum(r["false_positive_rate"] for r in group) / len(group),
                "mean_detection_delay": sum(r["mean_detection_delay"] for r in group if r["mean_detection_delay"] is not None) / max(1, sum(r["mean_detection_delay"] is not None for r in group)),
                "episode_detection_rate": sum(r["detected_attack_episodes"] for r in group) / max(1, sum(r["total_attack_episodes"] for r in group)),
            })
    with summary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"ablation complete: {len(rows)} runs")
    print(summary.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
