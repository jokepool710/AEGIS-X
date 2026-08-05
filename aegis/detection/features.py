from dataclasses import asdict, dataclass
from statistics import fmean, median, pstdev

import numpy as np


@dataclass(frozen=True)
class WindowFeatures:
    current_value: float
    mean: float
    std: float
    minimum: float
    maximum: float
    median: float
    range: float
    slope: float
    delta: float
    mean_abs_change: float
    rms: float
    sample_count: int

    def as_vector(self) -> list[float]:
        return [
            self.current_value,
            self.mean,
            self.std,
            self.minimum,
            self.maximum,
            self.median,
            self.range,
            self.slope,
            self.delta,
            self.mean_abs_change,
            self.rms,
        ]

    def as_dict(self) -> dict[str, float | int]:
        return asdict(self)


class FeatureExtractor:
    def extract(self, history: list[float], current_value: float) -> WindowFeatures:
        if not history:
            return WindowFeatures(
                current_value=current_value,
                mean=current_value,
                std=0.0,
                minimum=current_value,
                maximum=current_value,
                median=current_value,
                range=0.0,
                slope=0.0,
                delta=0.0,
                mean_abs_change=0.0,
                rms=abs(current_value),
                sample_count=1,
            )

        values = np.asarray(history, dtype=float)
        mean = fmean(history)
        std = pstdev(history) if len(history) > 1 else 0.0
        minimum = float(np.min(values))
        maximum = float(np.max(values))
        delta = current_value - history[-1]

        if len(history) > 1:
            x = np.arange(len(history), dtype=float)
            slope = float(np.polyfit(x, values, 1)[0])
            mean_abs_change = float(np.mean(np.abs(np.diff(values))))
        else:
            slope = 0.0
            mean_abs_change = 0.0

        return WindowFeatures(
            current_value=current_value,
            mean=mean,
            std=std,
            minimum=minimum,
            maximum=maximum,
            median=median(history),
            range=maximum - minimum,
            slope=slope,
            delta=delta,
            mean_abs_change=mean_abs_change,
            rms=float(np.sqrt(np.mean(np.square(values)))),
            sample_count=len(history),
        )
