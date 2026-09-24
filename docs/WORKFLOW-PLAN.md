# Workflow integration release

User approved the ecosystem roadmap and global Codex integration on 2026-09-24.

Goal: working bounded workflow tools, installed Codex integration, real selected-input use, and an evidence-bearing handoff back to Resident engineering.

Architecture: reuse Service.shared and its existing accounting, provenance and immutable call identities. New workflow orchestration validates complete caller packets before inference, binds the full packet to an event identity, composes independent signals and performs a separate second stage only for skill selection. Critical worker statuses remain visible deterministically. No new executor or authority.

Tasks:
- [x] Add workflows.py: progress_watch, skill_shortlist, swarm_inbox, patch_review, handoff_check, memory_conflict and conditional decision packs. Reject unknown fields, pin full input and maintain same-ID replay.
- [x] Add tests distinguishing high-confidence progress, useful negative evidence, uncertain/unavailable, critical reports, selected-candidate fit, stale inputs and dependent second-stage replay.
- [x] Add explicit local content-addressed artifacts and offline grouped calibration audit; no automatic source acquisition, context deletion, threshold promotion or model training.
- [x] Wire workflow/artifact/audit through Python/CLI/MCP/pi and document actual host event coverage. No unsupported global before-tool interception claim.
- [x] Update private Codex launch/skill atomically with backups; preserve existing quota policy, credentials and ledger. Verify installed runtime and MCP from outside source tree.
- [x] Run selected non-secret real-work packets through pinned Jev with a bounded test allowance inside existing authorization; report abstentions/failures and no general accuracy claim.
- [x] Independent Sol review and exact-source verification; installed and live receipts saved.
- Publication: v0.6.0 source and assets are released together; check the GitHub release for final commit and asset digests.
- Resident continuation is tracked privately in the owner checkpoint; no Resident claim follows from this product release.

Additional research: ReallyArtificial/jev-by-example (memory scope, handoff integrity, semantic postconditions; repository explicitly labels runtime examples unverified) and altryne/jevify (task-driven opportunity discovery). See ecosystem REPORT.md for original pinned sources. This implementation is original; no upstream code copied.

Acceptance: no duplicate paid work on replay, no quota reset, full-source identity, no suppressed hard worker status, second-stage selected fit, no mutation/permission authority. Tests and live observations remain distinct.
