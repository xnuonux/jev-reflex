# Jev Reflex

**Small decisions. More room to think.**

A portable decision sidecar for coding agents. Give Jev the bounded judgments around a task while your main model keeps the plan, the reasoning, and the tools.

**New in 0.5: stateful reflex controllers.** Keep an investigation direction or
semantic signal across changing evidence, damp rapid switching, preserve explicit
corrections and reject late results. Controllers read recorded Jev answers;
updating them makes no model call. Available through MCP, JSON CLI, Python and
the pi bridge. Try `jev-reflex controller-demo` for an offline walkthrough.
See [the controller contract and examples](docs/CONTROLLERS.md).

Works through **stdio MCP**, a **JSON CLI**, and a **Python API**. Includes a native **pi extension** and setup guides for Claude Code, Codex, OpenCode, and custom function-calling agents, including applications using DeepSeek.

Independent open-source project by **Eternities**. Not an official TypeSafe product. MIT licensed.

## What you get

| Agent question | Reflex workflow | What stays with the agent |
| --- | --- | --- |
| Which excerpts deserve attention now? | Source-bound context plan with required pins and recoverable pointers | Reading the evidence, keeping source bytes, changing context |
| Which approved model fits this step? | Advice among an explicit eligible roster | Choosing and switching the model |
| Which tool looks useful? | Advice among supplied eligible tools, or no tool | Arguments, permissions, execution |
| Where should I investigate this failure? | Implementation, test contract, fixture, environment, timing, or uncertain | Diagnosis, fixes, verification |
| What deserves extra review in this patch? | Interface, persistence, concurrency, presentation, tests, or uncertain | Full review and required checks |
| Does this evidence miss part of a claim? | Evidence-gap triage | Deciding whether the claim is established |
| Is this specific risk visible? | Probability-bearing risk flag | Safety policy and approval |

Seven versioned recipes, plus raw **Choice** and **Noul** batches. Uncertainty is a first-class result. Score is intentionally not exposed in this release.

## Why another Jev integration?

Plenty of projects expose Jev as a tool. Reflex concentrates on what happens **around the decision**:

- **Shared context, many questions.** Send one state packet once. Defaults allow up to 256 independent questions per request, constrained by size rather than an eight-question ceiling.
- **Bulk jobs up to 10,000 items.** Automatic packing, bounded concurrency, durable progress, cancellation, and paginated results. Raw items, shared-state questions and recipes use the same accounting.
- **Durable accounting before dispatch.** Multiple local processes share a SQLite ledger and atomically reserve against host limits.
- **Duplicate-call protection.** Replaying an operation ID never starts it again. Changed inputs under the same ID refuse.
- **Exact successful-result reuse.** Opt in per recipe; source, input, recipe, provider/model and thresholds must match. Each reuse has a new receipt pointing to its origin.
- **Source-bound context plans.** Hashes the exact supplied text, pointers and goal. Required evidence stays visible even if Jev calls it irrelevant. No file scanning or automatic compaction.
- **Inspectable evidence.** Full bounded distributions, model/route, elapsed time, known token usage, reported versus conservatively reserved cost, and caller-reported downstream outcomes.
- **No silent retries or provider fallback.** Uncertain attempts remain visible and accounted.
- **Offline shadow evaluation.** Per-route confusion matrices, precision/recall, abstentions and confidence bins. Measure correctness separately from valid output and speed.

This is an engineering contract, not a promise of universal speed or accuracy gains. The [evaluation guide](docs/EVALUATION.md) explains how to measure the whole workflow.

## Try it without a key

Python **3.11+**. Clone the repository and install into an isolated environment:

```sh
git clone https://github.com/xnuonux/jev-reflex.git
cd jev-reflex
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell instead: .\.venv\Scripts\Activate.ps1
python -m pip install ".[mcp]"
jev-reflex demo
```

The demo uses a fake provider and a temporary ledger. It demonstrates one dispatch, an exact replay, successful-result reuse, and mandatory context retention. It makes **zero network calls** and does not configure your account.

For a standalone executable on your PATH, install with `pipx install ".[mcp]"` from the clone. The CLI and Python API also work with `pip install .` without MCP dependencies. No PyPI or npm package is claimed by this repository; install from this source or its GitHub release.

## Enable your provider

Choose **one** route. No automatic fallback.

| Route | Environment | Model pin | Cost evidence |
| --- | --- | --- | --- |
| OpenRouter (default) | `OPENROUTER_API_KEY` | request `typesafe/jev-1.13`; returned `typesafe/jev-1.13-20260917`, provider `TypeSafe` | Reported USD cost when present; otherwise reservation retained |
| Direct TypeSafe | `JEV_REFLEX_PROVIDER=typesafe`, `TYPESAFE_API_KEY` | `jev-1.13.0` | Token counts; no USD cost field in the documented response. Reservation retained, never called a bill |

Set your credential privately in the environment of the process that launches Reflex. Never paste it into an agent conversation or commit it in config. Client environment inheritance varies; see [agent setup](docs/INTEGRATIONS.md).

Create an explicit local budget:

```sh
jev-reflex init --daily-usd 2 --enable
jev-reflex doctor
```

`init` refuses to overwrite a policy or coexist with a preexisting quota override. The default is disabled. State lives at `~/.local/share/jev-reflex-public/`; set `JEV_REFLEX_HOME` before launch to choose another host-owned directory. Agents sharing that directory share accounting. This public default is separate from the original personal plugin.

Each provider call reserves **$0.02** locally. This is a conservative envelope, **not the price of a call**. OpenRouter's validated reported cost can settle it downward. Direct TypeSafe retains the envelope because the API does not report USD cost. A local cap is not a provider billing cap; price changes, host changes or restoring old ledgers can invalidate assumptions. [Accounting details](docs/CONTRACT.md).

## Plug it into an agent

Once `jev-reflex` is on the host's PATH:

```sh
# Claude Code
claude mcp add --transport stdio jev-reflex -- jev-reflex serve

# Codex
codex mcp add jev-reflex -- jev-reflex serve

# Print configuration for another client without editing any files
jev-reflex config mcp
```

If using a virtual environment without activating it in the client, use the absolute path to that environment's `jev-reflex` executable. Copy the [agent skill](skills/jev-reflex/SKILL.md) into your host's supported skill location, or ask the agent to read it. It explains when a reflex is useful and when direct reasoning is cheaper.

**pi:** load `adapters/pi/jev-reflex.ts` with `pi --extension ./adapters/pi/jev-reflex.ts`. The extension invokes the CLI without a shell, forwards cancellation, and does not install dependencies or intercept unrelated tools.

**DeepSeek and other tool-capable models:** the surrounding application runs the tool. Use `jev_reflex.api.invoke` or the JSON CLI; a model API itself is not an MCP host. See [function-calling example](examples/function_calling.py).

See [compatibility and verification](docs/INTEGRATIONS.md) for tested boundaries. An MCP round trip does not prove every named host's complete workflow.

## One useful call

Send only selected, authorized text. On Windows PowerShell use `Get-Content -Raw examples/context.json | jev-reflex call context`.

```sh
jev-reflex call context < examples/context.json
```

```json
{
  "project": "widget",
  "task": "fix-build",
  "request_id": "context-001",
  "privacy_namespace": "widget-selected-source",
  "goal": "Find the cause of the failing build",
  "chunks": [
    {
      "id": "failure",
      "text": "Type error: string is not assignable to number.",
      "source_ref": "build-output:lines-10-12",
      "mandatory_pinned": true
    }
  ]
}
```

The context tool generates the snapshot from the actual supplied packet. It returns a receipt and a visibility plan with source hashes and pointers, not rewritten source or an automatic context mutation. The caller keeps the originals and checks they are still current. Pointer values remain local; selected text and the goal reach the provider.

## Tool surface

| MCP tool | CLI method | Purpose |
| --- | --- | --- |
| `jev_reflex_status` | `status` | Local readiness and accounting |
| `jev_reflex_context` | `context` | Source-bound reversible context plan |
| `jev_reflex_batch` | `batch` | Typed Choice/Noul questions |
| `jev_reflex_shared` | `shared` | One shared state, many independent questions |
| `jev_reflex_bulk` | `bulk` | Pack and advance up to 10,000 explicit items |
| `jev_reflex_controller_open` | `controller_open` | Bind a stable semantic question and temporal policy |
| `jev_reflex_controller_event` | `controller_event` | Apply recorded evidence, source updates, corrections or stop |
| `jev_reflex_controller_inspect` | `controller_inspect` | Read the held hint and its supporting evidence |
| `jev_reflex_inspect_job` | `inspect_job` | Durable progress and paginated results, no inference |
| `jev_reflex_cancel_job` | `cancel_job` | Stop further job admission; issued calls still settle |
| `jev_reflex_recipe` | `recipe` | One versioned workflow per batch |
| `jev_reflex_record_outcome` | `record_outcome` | Immutable typed caller feedback |
| `jev_reflex_recipe_metrics` | `metrics` | Known/unknown downstream measurements |

[Recipe schemas](docs/RECIPES.md) · [Security and data handling](SECURITY.md) · [Evaluation](docs/EVALUATION.md) · [Research and related work](docs/RESEARCH.md) · [Verification](docs/VERIFICATION.md)

## Shared state and bulk work

```sh
jev-reflex call shared < examples/shared.json
jev-reflex shadow-report < examples/shadow.json
```

Use `shared` when several questions inspect the same document: context appears once
in the request, rather than repeated inside each item. Questions evaluate independently.
Speculative questions can share a call if the host can discard irrelevant answers;
an answer-dependent question needs a later step with explicit updated state.

For a large job, pass raw items, shared questions, or one recipe's items to `bulk`.
It validates every item before inference, partitions by host capacity, then advances
the job during a bounded foreground run. Inspect `next_step`: `continue-same-input`
requires resubmitting the identical job later; paid children are never retried.
No background worker is installed. Inspect results in pages without sending source
text again. [Schemas, lifecycle and examples](docs/BULK.md).

Host-owned `capacity.json` configures count/concurrency/rate limits. Defaults: 256
questions per request, four concurrent calls, 60,000 request bytes and 30,000 bytes
for state plus the longest question. These byte guards are conservative packing
heuristics, **not exact token counts or a promise of provider acceptance**. Count
alone never overrides size, disclosure, daily spending or provider limits.

## Development

```sh
python -m unittest discover -s tests -v
node --test adapters/pi/bridge.test.mjs
python -m build
```

The test suite uses fake providers, real SQLite concurrency, real subprocesses, and an MCP client/server exchange. CI is configured for Windows, Linux and macOS. Read the current verification record for what has actually completed.

A subsequent [live TypeSafe corpus stress test](docs/LIVE-GODSKILLS-20260924.md)
submitted 452 typed questions in 25 requests, up to 64 questions per request.
The report preserves abstentions, an invalid provider response, independent
review disagreements and the distinction between tariff estimates and bills.

Your host owns actions. Reflex helps decide where to spend attention.
