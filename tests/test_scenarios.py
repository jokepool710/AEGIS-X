import pytest

from aegis.evaluation.scenarios import AttackEpisode, CPSAttackScenarioGenerator


@pytest.mark.parametrize(
    "attack_type",
    [
        "sensor_spoofing",
        "drift_injection",
        "spike",
        "replay",
        "stuck_at_value",
        "gradual_degradation",
    ],
)
def test_generates_labelled_attack_episode(attack_type: str) -> None:
    generator = CPSAttackScenarioGenerator(seed=7)
    samples = generator.generate(
        length=50,
        episodes=[AttackEpisode(attack_type, start=20, end=30, magnitude=5.0)],
    )

    assert len(samples) == 50
    assert sum(sample.is_attack for sample in samples) == 10
    assert all(sample.attack_type == attack_type for sample in samples[20:30])
    assert all(sample.attack_type == "normal" for sample in samples[:20])


def test_seed_makes_scenario_reproducible() -> None:
    episodes = [AttackEpisode("drift_injection", 10, 20, 3.0)]
    first = CPSAttackScenarioGenerator(seed=42).generate(30, episodes)
    second = CPSAttackScenarioGenerator(seed=42).generate(30, episodes)

    assert [sample.event.value for sample in first] == [sample.event.value for sample in second]


def test_stuck_at_value_is_constant_during_episode() -> None:
    samples = CPSAttackScenarioGenerator(seed=1).generate(
        30, [AttackEpisode("stuck_at_value", 10, 20)]
    )
    values = [sample.event.value for sample in samples[10:20]]

    assert len(set(values)) == 1


def test_invalid_episode_bounds_are_rejected() -> None:
    with pytest.raises(ValueError):
        CPSAttackScenarioGenerator().generate(
            20, [AttackEpisode("spike", start=15, end=25, magnitude=10.0)]
        )
