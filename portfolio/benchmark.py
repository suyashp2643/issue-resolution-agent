import hashlib
import html
import json
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import typer

app = typer.Typer()


@dataclass(frozen=True)
class Task:
    name: str
    issue: str
    buggy: str
    tests: str
    regression: str
    repair: str


TASKS = [
    Task("empty_average", "average([]) must return None; non-empty averages must remain correct.",
         "def average(values):\n    return sum(values) / len(values)\n",
         "assert m.average([]) is None\nassert m.average([0]) == 0\n",
         "assert m.average([2, 4]) == 3\nassert m.average([-4, 2]) == -1\n",
         "def average(values):\n    return sum(values) / len(values) if values else None\n"),
    Task("inclusive_overlap", "overlaps(a,b) uses closed intervals: touching endpoints overlap.",
         "def overlaps(a, b):\n    return max(a[0], b[0]) < min(a[1], b[1])\n",
         "assert m.overlaps((1, 2), (2, 3)) is True\nassert m.overlaps((1, 1), (1, 1)) is True\n",
         "assert m.overlaps((1, 4), (2, 3)) is True\nassert m.overlaps((1, 2), (3, 4)) is False\n",
         "def overlaps(a, b):\n    return max(a[0], b[0]) <= min(a[1], b[1])\n"),
    Task("stable_unique", "unique(values) must remove duplicates while preserving first-seen order.",
         "def unique(values):\n    return sorted(set(values))\n",
         "assert m.unique([3, 1, 3, 2]) == [3, 1, 2]\nassert m.unique(['z', 'a', 'z']) == ['z', 'a']\n",
         "assert m.unique([]) == []\nassert m.unique([1, 1]) == [1]\nassert m.unique([1, 2]) == [1, 2]\n",
         "def unique(values):\n    return list(dict.fromkeys(values))\n"),
]


def get_task(name: str) -> Task:
    return next(task for task in TASKS if task.name == name)


def evaluate_source(source: str, task: Task, *, trusted_fixture: bool = False, timeout: int = 5) -> dict:
    """Only fixed, reviewed fixture code may run locally. External candidates use Docker."""
    if not trusted_fixture:
        raise ValueError("External candidate execution requires the Docker grader")
    started = time.monotonic()
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "candidate.py").write_text(source)
        outcomes = {}
        for suite, assertions in [("fix", task.tests), ("regression", task.regression)]:
            script = "import importlib.util\ns = importlib.util.spec_from_file_location('candidate', " + repr(str(root / "candidate.py")) + ")\nm = importlib.util.module_from_spec(s)\ns.loader.exec_module(m)\n" + assertions
            (root / "check.py").write_text(script)
            result = subprocess.run([sys.executable, "-I", str(root / "check.py")], capture_output=True, text=True, timeout=timeout)
            outcomes[suite] = {"passed": result.returncode == 0, "output": (result.stdout + result.stderr)[-4000:]}
    return {"task": task.name, "candidate_hash": hashlib.sha256(source.encode()).hexdigest(), "resolved": all(item["passed"] for item in outcomes.values()), "suites": outcomes, "seconds": round(time.monotonic() - started, 4)}


def save_report(report: dict, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    output.with_suffix(".html").write_text("<!doctype html><meta charset='utf-8'><title>Issue resolution evaluation</title><style>body{max-width:1000px;margin:40px auto;font:16px system-ui;background:#101827;color:#e2e8f0}pre{white-space:pre-wrap;background:#1e293b;padding:24px;border-radius:12px}</style><h1>Issue resolution evaluation</h1><pre>" + html.escape(json.dumps(report, indent=2)) + "</pre>")


@app.command()
def demo(output: Path = Path("portfolio/results/demo.json")):
    """Verify grader behavior using reviewed fixtures, NOT model-generated fixes."""
    results = []
    for task in TASKS:
        for label, source in [("unchanged", task.buggy), ("reference_repair", task.repair)]:
            results.append({"candidate": label, **evaluate_source(source, task, trusted_fixture=True)})
    task = TASKS[0]
    results.append({"candidate": "regression_introducing_patch", **evaluate_source("def average(values):\n    return None if not values else 0\n", task, trusted_fixture=True)})
    report = {"mode": "grader_fixture_verification_NOT_agent_benchmark", "results": results, "llm_calls": 0, "note": "Reference repairs are hand-written. No model success rate is claimed. Tests are public, so this fixture set is not a held-out benchmark."}
    save_report(report, output)
    typer.echo(f"Saved {len(results)} candidate checks to {output}")


@app.command()
def prepare(task: str, destination: Path):
    """Create a fresh agent workspace without grader assertions."""
    selected = get_task(task)
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "candidate.py").write_text(selected.buggy)
    (destination / "ISSUE.md").write_text(selected.issue + "\n")
    typer.echo(destination)


@app.command()
def grade(task: str, candidate: Path, output: Path = Path("portfolio/results/candidate.json")):
    """Grade an external candidate inside Docker with no network or host write mounts."""
    selected = get_task(task)
    if candidate.is_symlink() or not candidate.is_file() or candidate.stat().st_size > 100_000:
        raise ValueError("Expected a regular Python file under 100KB")
    source = candidate.read_text()
    results = {}
    started = time.monotonic()
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        root.chmod(0o755)
        (root / "candidate.py").write_text(source)
        for suite, assertions in [("fix", selected.tests), ("regression", selected.regression)]:
            (root / "check.py").write_text("import candidate as m\n" + assertions)
            result = subprocess.run([
                "docker", "run", "--rm", "--network=none", "--read-only", "--cap-drop=ALL",
                "--security-opt=no-new-privileges", "--pids-limit=64", "--memory=256m", "--cpus=1",
                "--user=65534:65534", "--mount", f"type=bind,src={root},dst=/grade,readonly",
                "--workdir=/grade", "--tmpfs=/tmp:rw,noexec,nosuid,size=16m", "issue-agent-sandbox:local",
                "timeout", "10", "python", "-B", "check.py",
            ], capture_output=True, text=True, timeout=20)
            results[suite] = {"passed": result.returncode == 0, "returncode": result.returncode, "output": (result.stdout + result.stderr)[-4000:]}
    save_report({"task": task, "candidate_hash": hashlib.sha256(source.encode()).hexdigest(), "resolved": all(row["passed"] for row in results.values()), "suites": results, "seconds": round(time.monotonic() - started, 4), "note": "Public fixture assertions. Not a security boundary against adversarial code; use independent evaluation infrastructure for untrusted third-party submissions."}, output)
    typer.echo(output)


if __name__ == "__main__":
    app()
