# Contributing to AEGIS-X

Thank you for your interest in contributing to AEGIS-X! We welcome contributions from researchers, software engineers, cybersecurity professionals, and industrial automation experts.

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## Getting Started

1. **Fork the Repository** on GitHub.
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/AEGIS-X.git
   cd AEGIS-X
   ```
3. **Set up a Python 3.11+ virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -e ".[dev]"
   ```

## Development Workflow

- Maintain strict separation between deterministic evidence and generative reasoning.
- Ensure all disruptive response actions require human approval gates.
- Write unit tests for new functionality in `tests/`.
- Ensure all tests pass and code style adheres to Ruff:
  ```bash
  ruff check .
  pytest
  ```

## Pull Request Guidelines

1. Create a feature branch off `main`: `git checkout -b feat/my-feature`.
2. Keep commits atomic, well-described, and passing CI.
3. Open a Pull Request against `main` with a clear explanation of changes and verification steps.
4. Ensure GitHub Actions CI checks pass.
