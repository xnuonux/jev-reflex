# Agent integrations

Install the Python package with the `[mcp]` extra for MCP, or without it for CLI/Python use. Run `jev-reflex demo` before configuring a provider. Run `init --daily-usd N --enable` with a budget you choose, then `doctor`. Neither command makes an inference request.

## One core, three interfaces

All transports use the same `Service`: identical validation, reservations, idempotency, provider pins, recipes and outcomes. Host integration is explicit. Installing the server makes tools available; it does **not** rewrite the host's reasoning loop or force every agent to call Jev. Give your agent the [skill](../skills/jev-reflex/SKILL.md) and evaluate when it helps.

Version 0.5 adds three stateful tools: `controller_open`, `controller_event`, and
`controller_inspect` (prefix `jev_reflex_` for MCP). A host announces a source
snapshot, obtains a raw batch/shared result, then submits its recorded request/item
reference to the controller. Feed multiple independent signals into separate
controllers; the host combines their hints in its normal reasoning loop. A stable
route never launches a tool or switches the host model itself. The full lifecycle
and correction/stop examples are in [CONTROLLERS.md](CONTROLLERS.md).

Upgrade the installed package and restart its MCP process to expose the new tools.
Existing raw calls continue to work. Pre-0.5 receipts lack semantic signal hashes
and cannot seed a controller; they remain valid historical call receipts. Do not
repeat paid work solely to upgrade a receipt. Existing private plugins and client
registrations are not automatically replaced by installing this public package.

### Claude Code

```sh
claude mcp add --transport stdio jev-reflex -- jev-reflex serve
```

Use the installed executable's absolute path if the client's PATH differs. This is a local MCP registration, not a Claude marketplace installation. [Claude MCP documentation](https://code.claude.com/docs/en/mcp).

### Codex

```sh
codex mcp add jev-reflex -- jev-reflex serve
jev-reflex config codex
```

The printed TOML includes `env_vars` for the two credential names and the provider/home selectors. Configure only the route you use; no secret values appear in the generated config. Review the client's configuration rather than assuming your terminal environment is inherited. [Codex MCP documentation](https://developers.openai.com/codex/mcp/).

### Generic MCP and OpenCode

`jev-reflex config mcp` prints a common `mcpServers` configuration. `config opencode` prints OpenCode's local MCP shape. Review and install it in your host's configuration; this command never edits files. Stdio uses no network listener. Do not share stdout with other programs.

Environment forwarding is host-specific. Some MCP clients pass only a small environment whitelist. Supply `JEV_REFLEX_PROVIDER`, `JEV_REFLEX_HOME`, and the selected key through the host's protected environment mechanism. Do not put credential values in project JSON or shell history. `doctor` in your terminal is not proof the MCP child received the same environment.

### pi

```sh
pi --extension ./adapters/pi/jev-reflex.ts
```

The extension registers one `jev_reflex` tool with a fixed method enum and invokes the installed CLI via JSON stdin, with `shell:false`. Keep `bridge.mjs` beside the extension. CLI installation and environment must already exist; extension load never installs dependencies. To make the extension persistent, use pi's supported extension/package mechanism. [pi extension documentation](https://pi.dev/docs/latest/extensions).

Cancellation or the 60-second bridge deadline returns an uncertain outcome and kills the direct child. It does not establish process-tree termination or provider cancellation. Preserve the request ID and ledger; do not retry under a fresh ID. For job cancellation, call `cancel_job` so it persists in the ledger. The core transport has its own 20-second provider-child deadline. The bridge accepts up to 16 MiB JSON input/output; bulk results are paginated. A killed parent can leave pending children: inspect the same job rather than claiming cancellation of already issued provider requests.

### Custom agents, including DeepSeek-backed applications

The application handles function calls. A model API does not launch a local MCP server itself. See [function_calling.py](../examples/function_calling.py) for a JSON Schema tool definition and a host dispatcher using `jev_reflex.api.invoke`.

```python
from jev_reflex import Service
from jev_reflex.api import invoke

service = Service()  # shared host-owned ledger; no inference at construction
readiness = invoke(service, "status", {})
```

Allowed methods: `status`, `batch`, `shared`, `bulk`, `inspect_job`, `cancel_job`, `recipe`, `context`, `record_outcome`, `metrics`. No `init`, reset, file read, arbitrary command, or credential method. Return the result to the model using your provider's tool-result format. Keep approvals and effect execution in your application's tool layer. [DeepSeek tool calling](https://api-docs.deepseek.com/guides/tool_calls/).

## Compatibility claims

| Surface | Qualification in this release |
| --- | --- |
| Python core and JSON CLI | Offline runtime tests, including real local processes |
| MCP | Official Python SDK stdio tests, including shared/bulk/progress/cancel; fake inference; see exact release verification |
| pi bridge | Real subprocess tests, input/output bounds, cancellation before dispatch, UTF-8 handling and authority envelope |
| pi host extension | Written against current documented native API; actual pi host session not run |
| Claude Code / Codex / OpenCode | Current configuration recipes; complete host-specific live workflow not run |
| DeepSeek example | Python host adapter; no DeepSeek API request performed |

MCP qualification uses the pinned validation environment's SDK, not every protocol revision or client. See [verification](VERIFICATION.md) for the actual cut. A missing key, unsupported server version, moved model pin, or abstaining answer should return control to the host agent, not trigger a retry storm.
