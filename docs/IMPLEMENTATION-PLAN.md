# Jev Reflex public implementation plan

> Execute dependent packaging steps sequentially. Research and independent review own separate output paths.

**Goal:** Publish a usable, source-installable public agent decision plugin.
**Architecture:** One Python Service, JSON dispatcher, CLI and stdio MCP; thin client adapters.
**Tech stack:** Python 3.11+, SQLite standard library, official MCP SDK, setuptools wheel.
**Spec:** [DESIGN.md](DESIGN.md).

1. Package the reviewed core and inherited tests. Replace implicit sibling imports with package imports and machine-specific paths with public configuration. Verify inherited tests before feature additions.
2. Add strict JSON dispatch and CLI: init, status/doctor, call, serve, config, demo. Exercise invalid JSON/extra fields, disabled defaults, no-overwrite policy, portable subprocesses and no-secret diagnostics.
3. Add three coding recipes with explicit eligible alternatives and uncertainty. Test allowlists, malformed options, abstention and non-authority; preserve existing reuse bindings.
4. Add interoperability examples, skill, native pi adapter where the actual host API is verified, and reproducible offline evaluation with measurement limits. Validate generated configurations and example requests.
5. Build/install wheel in isolation, run CLI and MCP from outside the source tree, independently review runtime/publication scope, correct defects, then publish a fresh public GitHub history. No global installation or private source mutation.
