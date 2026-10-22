# Issue Resolution Agent — evaluation and review extension

## Model comparison

See [EVALUATION.md](../EVALUATION.md) for the six-task paired model comparison and manual workflow. No live model results have been published yet.

This directory extends **mini-swe-agent** with a small, reproducible issue-resolution experiment. Upstream agent code is preserved unchanged. Its authors and MIT license remain authoritative for upstream code.

## What this extension adds

- Three public Python bug fixtures, each with separate fix and regression assertions.
- A grader that rejects a patch which resolves the reported edge case but breaks existing behavior.
- Candidate SHA-256, per-suite outcomes, elapsed time, JSON and HTML reports.
- A bounded Docker runner using upstream DefaultAgent and model adapters.
- No automatic PR creation or merge; patches remain in a disposable review workspace.

This is an early working extension, **not a new coding agent built from scratch**. Fixture demonstrations use hand-written reference repairs, not model-generated fixes. Live LLM performance and Docker execution have not been verified in the build environment.

## No-key demonstration

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install pytest typer
python -m pytest portfolio/tests -q
python -m portfolio.benchmark demo
```

Open `portfolio/results/demo.html`. The report labels all fixture candidates and does not claim an agent solve rate. Tests are separate from the task workspace but public in the repository: this is not a held-out benchmark.

## Live agent run (optional, not yet integration-tested)

Requires Docker and a configured model provider API key. The host calls the provider; the worker container has no network. Installing upstream dependencies may be substantial.

```bash
python -m pip install -e .
docker build -f portfolio/Dockerfile -t issue-agent-sandbox:local .
python -m portfolio.benchmark prepare empty_average ./work-empty-average
python -m portfolio.run_agent ./work-empty-average YOUR_PROVIDER_MODEL
python -m portfolio.benchmark grade empty_average ./work-empty-average/candidate.py
```

`python -m portfolio.run_agent --help` shows the command options. Configure the API credential expected by your selected upstream provider (for example OPENAI_API_KEY). Do not put keys in the workspace or commit them. A run has a 12-call limit, 180-second agent wall-time check and upstream $1 cost threshold; a billed call may overshoot that threshold, and provider timeouts may extend total wall time.

Docker restricts network, memory, CPUs, process count and capabilities. The agent sees only the disposable workspace mount; never point it at a valuable checkout. Its workspace is writable, and the worker currently runs as root inside the container. This is not a hardened hostile-code service. Only use reviewed code and fixtures; do not accept arbitrary public submissions. Tests can be bypassed by deliberately adversarial candidates. The grader does not inspect a complete repository patch.

The grader container reads a copied candidate and assertions through a read-only mount, has no host write mounts and runs as an unprivileged user. Missing Docker or timeout fails the command, rather than executing candidates on the host. Trusted, fixed reference fixtures run locally in isolated Python mode, which is **not** a security sandbox.

## Resume description after personal review

“Extended mini-swe-agent with a reproducible evaluation harness separating bug-fix checks from regression checks, structured candidate evidence and a constrained Docker execution path.”

Only claim model success, costs or deployment after recording real runs. Do not use upstream SWE-bench scores as your own.

## Attribution

Upstream: https://github.com/SWE-agent/mini-swe-agent

Base commit: `04d809ceab9df28f9adaed044884180159172930`.

Copyright upstream: Kilian A. Lieret and Carlos E. Jimenez. LICENSE.md is retained. This extension was authored with AI assistance for Suyash Patil. Its changes are in `portfolio/` and the repository landing README; upstream code, tests and documentation remain preserved.
