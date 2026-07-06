from dataclasses import dataclass

from aegis.common.models import TelemetryEvent
from aegis.detection.pipeline import DetectionPipeline
from aegis.evaluation.metrics import EvaluationMetrics, evaluate_predictions


@dataclass(frozen=True)
class LabelledTelemetry:
    event: TelemetryEvent
    is_attack: bool
    attack_type: str = "normal"


@dataclass(frozen=True)
class EvaluationRun:
    metrics: EvaluationMetrics
    labels: list[bool]
    predictions: list[bool]
    scores: list[float]
    attack_types: list[str]


class DetectionEvaluationHarness:
    def __init__(self, pipeline: DetectionPipeline) -> None:
        self.pipeline = pipeline

    def run(self, samples: list[LabelledTelemetry]) -> EvaluationRun:
        labels: list[bool] = []
        predictions: list[bool] = []
        scores: list[float] = []
        attack_types: list[str] = []

        for sample in samples:
            result = self.pipeline.process(sample.event)
            labels.append(sample.is_attack)
            predictions.append(result.anomalous)
            scores.append(result.unified_score)
            attack_types.append(sample.attack_type)

        return EvaluationRun(
            metrics=evaluate_predictions(labels, predictions),
            labels=labels,
            predictions=predictions,
            scores=scores,
            attack_types=attack_types,
        )
