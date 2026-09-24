# Security and data handling

Jev Reflex is a local advisory service. It does not authorize or execute shell, browser, filesystem, credential, payment or deployment operations. Model output is untrusted evidence, including when its confidence is high.

Only text explicitly provided by the caller is sent to the selected fixed provider endpoint. Each native batch shares one state and therefore one disclosure boundary. Labels do not isolate hostile tenants. Do not send secrets or mix confidential projects. Prompts reduce ambiguity; they do not defeat prompt injection.

Credentials are read from the process environment. No key is written by setup, included in generated client configuration, passed as a CLI argument or returned by status. The transport rejects redirects and disables implicit environment HTTP proxies. Enterprise proxy deployments need an explicitly reviewed adapter; changing the endpoint is not a supported tool argument.

The ledger records hashes, bounded decisions, accounting and optional typed feedback, not raw input excerpts. Context pointers are returned to the calling client but not sent to Jev or retained in the ledger. IDs, hashes, distributions and pointers may still be sensitive. This is not encryption or anonymity. Client logs and provider retention are outside this guarantee.

Use a state directory owned by the local user. SQLite accounting is shared local state, not authenticated multi-tenant isolation or rollback protection. Do not delete or restore a ledger to evade a budget or repeat an uncertain call. An interrupted process can leave a pending reservation; status exposes it. There is deliberately no model-callable reset, refund or budget-edit tool.

The transport child has a 20-second wall deadline and no retries. Killing a local child does not prove a provider cancelled its billable operation. HTTP errors expose only numeric status, never provider response bodies. Respect provider billing/rate refusals. Source snapshots describe supplied content, not the authenticity or continued state of external files.

Report a vulnerability through GitHub's private vulnerability reporting feature when available. If unavailable, open an issue containing only a minimal non-sensitive description and request a private channel. Do not post credentials or private source data.
