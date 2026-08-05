from aegis.evaluation.benchmark import ResearchBenchmarkSuite
from aegis.evaluation.comparator import BenchmarkComparator


def test_phase8_research_benchmark_e2e() -> None:
    suite = ResearchBenchmarkSuite()
    report = suite.run_benchmark("synthetic_water_treatment_attack")

    assert report["total_scenarios_evaluated"] == 150
    assert len(report["results"]) == 3

    top = report["summary"]["top_performing_model"]
    assert "AEGIS-X" in top

    comparator = BenchmarkComparator(suite)
    md_table = comparator.generate_markdown_table("synthetic_water_treatment_attack")
    latex_table = comparator.generate_latex_table("synthetic_water_treatment_attack")

    assert md_table.startswith("### Comparative Evaluation Benchmark Results")
    assert "\\caption{AEGIS-X Comparative Benchmark Performance}" in latex_table
