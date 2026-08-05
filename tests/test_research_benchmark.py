from aegis.evaluation.benchmark import ResearchBenchmarkSuite
from aegis.evaluation.comparator import BenchmarkComparator


def test_research_benchmark_suite() -> None:
    suite = ResearchBenchmarkSuite()
    res = suite.run_benchmark("test_dataset")

    assert res["models_evaluated"] == 3
    assert res["summary"]["top_f1_score"] > 0.90
    assert res["summary"]["mttd_reduction_percent"] > 50.0


def test_benchmark_comparator() -> None:
    comparator = BenchmarkComparator()
    md = comparator.generate_markdown_table("test_dataset")
    latex = comparator.generate_latex_table("test_dataset")

    assert "| AEGIS-X Grounded Multi-Agent Pipeline |" in md
    assert "\\begin{table}" in latex
    assert "\\end{table}" in latex
