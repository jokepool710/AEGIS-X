import csv
import json

from aegis.evaluation.experiments import ExperimentConfig, ExperimentRunner


def small_config() -> ExperimentConfig:
    return ExperimentConfig(
        seeds=(1, 2),
        attack_types=("sensor_spoofing",),
        magnitudes=(5.0,),
        thresholds=(0.60,),
        length=80,
        attack_start=35,
        attack_end=55,
        warmup=10,
        window_size=30,
        retrain_interval=10,
    )


def test_experiment_matrix_produces_one_row_per_combination() -> None:
    rows = ExperimentRunner(small_config()).run()

    assert len(rows) == 2
    assert {row.seed for row in rows} == {1, 2}
    assert all(row.attack_type == "sensor_spoofing" for row in rows)


def test_aggregation_reports_mean_and_variability() -> None:
    runner = ExperimentRunner(small_config())
    summary = runner.aggregate(runner.run())

    assert len(summary) == 1
    assert summary[0]["runs"] == 2
    assert 0.0 <= summary[0]["f1_mean"] <= 1.0
    assert summary[0]["f1_std"] >= 0.0
    assert 0.0 <= summary[0]["episode_detection_rate"] <= 1.0


def test_result_artifacts_are_machine_readable(tmp_path) -> None:
    paths = ExperimentRunner(small_config()).write_artifacts(tmp_path)

    assert all(path.exists() for path in paths.values())
    with paths["runs_csv"].open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    report = json.loads(paths["report_json"].read_text(encoding="utf-8"))

    assert len(rows) == 2
    assert report["run_count"] == 2
    assert len(report["aggregates"]) == 1
