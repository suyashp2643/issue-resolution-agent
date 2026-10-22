# Real model evaluation

**Status: evaluation runner implemented; no real model results published yet.**
The existing demo reports verify fixtures. They do not measure an LLM's success rate.
A passing software test or the local HTTP protocol test below is not a real model run.

## Run a concrete comparison

1. Open this repository's **Settings → Secrets and variables → Actions**.
2. Add a repository secret named `LLM_API_KEY` with your provider API key. Never put it in code, a commit, an issue, or a chat.
3. Optional: set repository variable `LLM_BASE_URL` to your trusted provider's chat-completions base URL (ending in `/v1` where applicable). The default is `https://api.openai.com/v1`. Providers must support `messages`, `temperature`, and `max_tokens`; incompatible requests count as errors, with no fake fallback.
4. Open **Actions → Live model comparison → Run workflow**. Enter the provider's exact model ID and start with **1 case, 1 repeat**. This makes paid API calls to your account. Check provider billing before expanding the run.
5. Download the `live-model-comparison` artifact. It contains JSON and escaped HTML with per-attempt outcomes, model responses, paired comparisons, timings, hashes, and provider-reported token usage. Use only these live outputs for performance claims.

The workflow never runs on a push or a pull request. Unit-test CI needs no model key.
Artifacts contain synthetic inputs and model outputs; inspect them before making them public.
A provider request timeout or malformed response fails that attempt. Errors remain in the denominator;
raw worker stderr is deliberately omitted from reports to avoid credential disclosure.
A run with worker errors exits nonzero after saving its full report.
Runs checkpoint after every attempt and refuse to overwrite an existing report. Interrupted runs have
`complete: false`; do not present them as completed benchmarks. Failed workers may have consumed
provider tokens that are not available in the report; total observed calls/usage is a lower bound when errors occur.

## Local execution (Linux/macOS with `timeout`, or Linux container)

Set `LLM_API_KEY` securely in your shell, and optionally `LLM_BASE_URL`, then run from the repository root:

```bash
python -m pip install typer
docker build -t issue-agent-sandbox:local -f portfolio/Dockerfile .
python -m portfolio.evaluate --model YOUR_MODEL_ID --limit 6 --repeats 1 --output results/run-001.json
```

## Protocol and interpretation

Six additional programming tasks cover parsing, interval merging, nested lookups, event tie-breaking,
chunk boundaries, and dependency cycles. The original three toy bug fixtures are excluded.
Each task has a visible example and separate regression/edge-case assertions. Final assertions are
withheld from prompts and feedback, but are public in this repository: this is **not** an independently
held-out real-world issue benchmark. Freeze the dataset hash before tuning; add external issues
with reproducible environments before claiming generalization to unfamiliar repositories.

`single_shot` gets one repair call. `agent` uses the same model, initial prompt and visible tests,
with up to three repair calls receiving visible test feedback. Hidden tests grade only the final
candidate. The comparison measures the benefit and cost of feedback plus additional calls;
it does not isolate orchestration from compute. Method order alternates to reduce ordering effects.
Maximum calls per full six-case repeat: **24**, each requesting at most 1,600 output tokens.
Repeat runs report observed success rates, not guaranteed reliability or statistical significance.

All candidate execution uses a disposable Docker container with no network, a read-only mount,
non-root user, resource limits, and a command timeout. API credentials stay outside the container.
Docker is required; there is no host-execution fallback. This is a portfolio sandbox, not an audited
boundary for hostile submissions. The compact comparison loop is original portfolio code, separate
from the attributed upstream mini-SWE-agent runner.

## What to publish after running

Record the commit, dataset hash, provider/model ID, date, number of cases and repeats, success/error
counts for every method, paired wins/losses, latency, tool/model calls, available token usage,
and representative failures. Publish complete outcomes even if the agent loses to the baseline.
Do not convert a tiny benchmark percentage into a promise of job selection or production reliability.
