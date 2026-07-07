import math
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from aegis.common.models import TelemetryEvent
from aegis.evaluation.harness import LabelledTelemetry


@dataclass(frozen=True)
class AttackEpisode:
    attack_type: str
    start: int
    end: int
    magnitude: float = 1.0


class CPSAttackScenarioGenerator:
    def __init__(self, seed: int = 42) -> None:
        self.random = random.Random(seed)

    def baseline(self, length: int, base_value: float = 24.0, noise_std: float = 0.08,
                 device_id: str = "pump-eval-01", metric: str = "temperature",
                 unit: str = "celsius") -> list[TelemetryEvent]:
        started = datetime.now(timezone.utc)
        events = []
        for index in range(length):
            seasonal = 0.15 * math.sin(index / 12.0)
            value = base_value + seasonal + self.random.gauss(0.0, noise_std)
            events.append(TelemetryEvent(
                event_id=f"eval-{device_id}-{metric}-{index}", device_id=device_id,
                device_type="industrial_pump", site_id="evaluation-lab",
                timestamp=started + timedelta(seconds=index), sequence=index, metric=metric,
                value=value, unit=unit, quality="good",
                source_topic=f"evaluation/{device_id}/{metric}",
                ingested_at=started + timedelta(seconds=index),
            ))
        return events

    def generate(self, length: int, episodes: list[AttackEpisode], base_value: float = 24.0,
                 noise_std: float = 0.08) -> list[LabelledTelemetry]:
        events = self.baseline(length, base_value, noise_std)
        labels = [False] * length
        attack_types = ["normal"] * length

        for episode in episodes:
            if not 0 <= episode.start < episode.end <= length:
                raise ValueError(f"invalid episode bounds: {episode}")
            replay_pattern = [event.value for event in events[max(0, episode.start - 5):episode.start]]
            stuck_value = events[episode.start].value
            duration = max(1, episode.end - episode.start - 1)

            for index in range(episode.start, episode.end):
                original = events[index]
                progress = (index - episode.start) / duration
                if episode.attack_type == "sensor_spoofing":
                    value = original.value + episode.magnitude
                elif episode.attack_type == "drift_injection":
                    value = original.value + episode.magnitude * progress
                elif episode.attack_type == "spike":
                    value = original.value + episode.magnitude if index == episode.start else original.value
                elif episode.attack_type == "replay":
                    value = replay_pattern[(index - episode.start) % len(replay_pattern)]
                elif episode.attack_type == "stuck_at_value":
                    value = stuck_value
                elif episode.attack_type == "gradual_degradation":
                    value = original.value + episode.magnitude * (progress**2)
                else:
                    raise ValueError(f"unsupported attack type: {episode.attack_type}")

                events[index] = original.model_copy(update={"value": value})
                labels[index] = True
                attack_types[index] = episode.attack_type

        return [LabelledTelemetry(event=event, is_attack=label, attack_type=attack_type)
                for event, label, attack_type in zip(events, labels, attack_types, strict=True)]
