from dataclasses import asdict, dataclass
from statistics import fmean


@dataclass(frozen=True)
class EvaluationMetrics:
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int
    precision: float
    recall: float
    f1: float
    false_positive_rate: float
    mean_detection_delay: float | None
    detected_attack_episodes: int
    total_attack_episodes: int

    def as_dict(self) -> dict[str, int | float | None]:
        return asdict(self)


def _safe_divide(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def classification_metrics(labels: list[bool], predictions: list[bool]) -> tuple[int, int, int, int, float, float, float, float]:
    if len(labels) != len(predictions):
        raise ValueError("labels and predictions must have equal length")
    tp = sum(label and prediction for label, prediction in zip(labels, predictions, strict=True))
    fp = sum(not label and prediction for label, prediction in zip(labels, predictions, strict=True))
    tn = sum(not label and not prediction for label, prediction in zip(labels, predictions, strict=True))
    fn = sum(label and not prediction for label, prediction in zip(labels, predictions, strict=True))
    precision = _safe_divide(tp, tp + fp)
    recall = _safe_divide(tp, tp + fn)
    f1 = _safe_divide(2 * precision * recall, precision + recall)
    fpr = _safe_divide(fp, fp + tn)
    return tp, fp, tn, fn, precision, recall, f1, fpr


def attack_episode_delays(labels: list[bool], predictions: list[bool]) -> tuple[list[int], int]:
    if len(labels) != len(predictions):
        raise ValueError("labels and predictions must have equal length")
    delays: list[int] = []
    total_episodes = 0
    index = 0
    while index < len(labels):
        if not labels[index]:
            index += 1
            continue
        total_episodes += 1
        start = index
        while index < len(labels) and labels[index]:
            index += 1
        end = index
        detection = next((i for i in range(start, end) if predictions[i]), None)
        if detection is not None:
            delays.append(detection - start)
    return delays, total_episodes


def evaluate_predictions(labels: list[bool], predictions: list[bool]) -> EvaluationMetrics:
    tp, fp, tn, fn, precision, recall, f1, fpr = classification_metrics(labels, predictions)
    delays, total_episodes = attack_episode_delays(labels, predictions)
    return EvaluationMetrics(
        true_positives=tp,
        false_positives=fp,
        true_negatives=tn,
        false_negatives=fn,
        precision=precision,
        recall=recall,
        f1=f1,
        false_positive_rate=fpr,
        mean_detection_delay=fmean(delays) if delays else None,
        detected_attack_episodes=len(delays),
        total_attack_episodes=total_episodes,
    )
