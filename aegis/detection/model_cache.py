from dataclasses import dataclass

import numpy as np
from sklearn.ensemble import IsolationForest

StreamKey = tuple[str, str]


@dataclass
class CachedIsolationModel:
    model: IsolationForest
    trained_at_sample: int
    training_size: int
    generation: int


class IsolationForestModelCache:
    def __init__(
        self,
        retrain_interval: int = 20,
        n_estimators: int = 100,
        random_state: int = 42,
    ) -> None:
        if retrain_interval < 1:
            raise ValueError("retrain_interval must be at least 1")
        self.retrain_interval = retrain_interval
        self.n_estimators = n_estimators
        self.random_state = random_state
        self._models: dict[StreamKey, CachedIsolationModel] = {}
        self._fit_counts: dict[StreamKey, int] = {}

    def _needs_retrain(self, key: StreamKey, sample_count: int) -> bool:
        cached = self._models.get(key)
        if cached is None:
            return True
        return sample_count - cached.trained_at_sample >= self.retrain_interval

    def get_or_train(
        self,
        key: StreamKey,
        history: list[float],
        sample_count: int,
    ) -> CachedIsolationModel:
        if not history:
            raise ValueError("history is required to train Isolation Forest")

        if not self._needs_retrain(key, sample_count):
            return self._models[key]

        training = np.asarray(history, dtype=float).reshape(-1, 1)
        model = IsolationForest(
            n_estimators=self.n_estimators,
            contamination="auto",
            random_state=self.random_state,
        )
        model.fit(training)

        generation = self._models[key].generation + 1 if key in self._models else 1
        cached = CachedIsolationModel(
            model=model,
            trained_at_sample=sample_count,
            training_size=len(history),
            generation=generation,
        )
        self._models[key] = cached
        self._fit_counts[key] = self._fit_counts.get(key, 0) + 1
        return cached

    def score(
        self,
        key: StreamKey,
        history: list[float],
        current_value: float,
        sample_count: int,
    ) -> tuple[float, CachedIsolationModel]:
        cached = self.get_or_train(key, history, sample_count)
        decision = float(cached.model.decision_function([[current_value]])[0])
        return decision, cached

    def fit_count(self, key: StreamKey) -> int:
        return self._fit_counts.get(key, 0)

    def metadata(self, key: StreamKey) -> dict[str, int] | None:
        cached = self._models.get(key)
        if cached is None:
            return None
        return {
            "trained_at_sample": cached.trained_at_sample,
            "training_size": cached.training_size,
            "generation": cached.generation,
            "fit_count": self.fit_count(key),
        }
