from __future__ import annotations

from aegis.evaluation.benchmark import ResearchBenchmarkSuite


class BenchmarkComparator:
    """Generate comparative markdown & LaTeX tables for academic publication."""

    def __init__(self, benchmark_suite: ResearchBenchmarkSuite | None = None) -> None:
        self.suite = benchmark_suite or ResearchBenchmarkSuite()

    def generate_markdown_table(self, dataset_name: str = "ics_modbus_recon") -> str:
        data = self.suite.run_benchmark(dataset_name)
        rows = data["results"]

        lines = [
            f"### Comparative Evaluation Benchmark Results ({dataset_name})",
            "",
            "| Model / Architecture | Precision | Recall | F1 Score | MTTD (s) | MTTI (s) | Faithfulness |",
            "|---|---|---|---|---|---|---|",
        ]

        for r in rows:
            lines.append(
                f"| {r['model_name']} | {r['precision']:.3f} | {r['recall']:.3f} | {r['f1_score']:.3f} | {r['mttd_seconds']:.2f} | {r['mtti_seconds']:.2f} | {r['faithfulness_score']:.3f} |"
            )

        return "\n".join(lines)

    def generate_latex_table(self, dataset_name: str = "ics_modbus_recon") -> str:
        data = self.suite.run_benchmark(dataset_name)
        rows = data["results"]

        lines = [
            "\\begin{table}[h]",
            "\\centering",
            "\\caption{AEGIS-X Comparative Benchmark Performance}",
            "\\begin{tabular}{lcccccc}",
            "\\hline",
            "Model & Precision & Recall & F1 & MTTD (s) & MTTI (s) & Faithfulness \\\\",
            "\\hline",
        ]

        for r in rows:
            lines.append(
                f"{r['model_name']} & {r['precision']:.3f} & {r['recall']:.3f} & {r['f1_score']:.3f} & {r['mttd_seconds']:.2f} & {r['mtti_seconds']:.2f} & {r['faithfulness_score']:.3f} \\\\"
            )

        lines.extend([
            "\\hline",
            "\\end{tabular}",
            "\\end{table}",
        ])

        return "\n".join(lines)
