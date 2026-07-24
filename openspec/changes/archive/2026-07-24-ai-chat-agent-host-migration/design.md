# Design: AI Chat Migration to Chat-Service (Agent Host) Architecture

> Source of truth for full investigation detail: `/home/noro/.claude/plans/discuss-few-bits-d-tender-marble.md`. This document condenses the decisions and how-to; tickets #87–#97 carry per-PR scope.

## Context

Current flow: frontend → nginx → users-service proxy (`services/users/app/api/ai_settings_routes.py:66`) → ai `/ai/chat/stream` → intent agent + orchestrator inside ai → REST calls back into budget (`services/ai/app/services/chat_agent.py:69-179`, wired by `BUDGET_SERVICE_URL`). A second edge runs budget → ai for the parse flow (`/budgets/ai/stream`). Conversation state lives in ai's Postgres as PydanticAI-serialized blobs. Budget-domain knowledge (intent schemas, dispatchers) lives in ai. Today's SSE `text` "streaming" is synthetic — one delta per turn emitted after completion.

Constraints: system must stay deployable after every PR; frontend↔backend SSE contract stays byte-identical through cutover for independent rollback; BYOK keys and rate limiting must remain in ai; user requires server-side any-device chat history and polyglot-safe domain services ("budget could move to .NET").

## Goals / Non-Goals

**Goals:**
- Dependency DAG: `frontend → chat`, `chat → ai`, `chat → domain REST`; no ai → domain, no domain → domain, no domain → ai.
- ai = pure stateless reasoning (`POST /ai/decide`); domain services carry zero AI/chat knowledge.
- Server-side, provider-neutral conversation history (any-device).
- Incremental: 11 sequential PR-sized tickets (#87–#97), each independently revertible.

**Non-Goals:**
- Fixing the superuser owner_id FIXME (`budget_services.py:40`) — explicitly kept per user decision.
- Migrating existing chat history (fresh start approved).
- Vercel AI SDK adoption, token-level streaming, conversation-restore UI — deferred with defined triggers.
- A cross-domain workflow orchestrator — build only when a genuine cross-domain need appears.

## Decisions

1. **chat↔ai is plain JSON, not SSE.** Today's stream is synthetic (single delta), so nothing is lost; chat re-emits the identical SSE frames to the frontend. Alternative (proxying PydanticAI partial-output streams through two hops) adds complexity for zero UX gain.
2. **Dedicated chat service over the alternatives.** Client-held history fails any-device; ai-owned threads keeps ai stateful and forces every domain to carry chat plumbing (Python-locked); per-domain chat tables rejected by user. The chat service is the "agent host" (VS Code Copilot model): conversation owner + tool registry + dispatch loop.
3. **`/ai/decide` implementation**: per-request PydanticAI Agent (key isolation), external/deferred toolset from `available_tools`, `output_type=[str, DeferredToolRequests]`. Fallback if the pinned pydantic-ai version fights this: generic structured output `{tool_name|null, params, reply|null}` validated against the supplied schema — endpoint contract identical either way.
4. **Tool registry MCP-shaped from day one** (`list_tools()` / `call_tool(name, params, token)`), hand-curated during migration; internals swap to an in-process FastMCP `from_openapi` bridge post-cutover (ticket #97). Rationale: raw OpenAPI schemas are poor LLM tool interfaces (would expose `owner_id`, require model-supplied `budget_id`) — curation is needed either way, and the newest dependency stays out of the riskiest chunk. The 5b test suite passing unchanged is the bridge's acceptance gate.
5. **Fresh-start history**: chat's `conversations`/`messages` use provider-neutral role/content (+ tool_name/tool_params/tool_result); ai's PydanticAI-blob tables are dropped, not migrated.
6. **Deterministic guards stay in code** (ported from ai's `chat_orchestrator.py`): targeted tools require `context_id`; params validated against per-tool Pydantic models; the model never supplies resource IDs (`budget_id` injected from `context_id`).
7. **Frontend context is the URL**: `matchPath("/budgets/:id")` at the layout-mounted panel; navigate to new budgets; generic `context_id`/`page` payload lands at cutover so old/new backends are never spoken to with mixed contracts.
8. **Chat scaffold (#91) touches all three routing layers, not two.** `nginx.conf`/`nginx-dev.conf` are the obvious pair, but prod runs Caddy (`Caddyfile`), not nginx — it needs its own `/api/v1/chat/*` block in the same PR rather than being deferred, since #91 is already the one PR touching routing infra for chat's introduction. Plain `docker-compose.yml` (unlike `.dev/.local/.prod.yml`) is dead — no script runs it, CI only checks it parses — so it's excluded from scope rather than propagating a fourth chat entry into unused config. `/health` is a first for this codebase (no existing service has one); kept to plain liveness (no DB check) matching the scaffold's zero-user-traffic, zero-dependency intent.

## Risks / Trade-offs

- [Pinned pydantic-ai toolset ergonomics unknown] → decision 3's fallback keeps the endpoint contract fixed; only `decide_service.py` internals differ.
- [Chat service is a new deployable] → scaffold ships dark (ticket #91, `/health` only); zero user traffic until cutover.
- [Cutover breaks live sessions] → get-or-create conversation semantics: stale ids silently start fresh conversations; old path stays deployed until soak completes.
- [Tool defs live in chat, not budget] → accepted; they are JSON schemas of budget's public REST API, and the OpenAPI bridge (#97) restores budget-as-source-of-truth via its spec.
- [Refactor seams have no existing coverage] → ticket #87 lands safety-net tests (ai chat route, users proxy, budget ai-stream proxy) and fixes budget CI (currently runs 1 of 5 test files) before anything moves.

## Migration Plan

Strictly sequential, one PR per ticket, merged before the next starts (branch `<Service>/Issue-<n>/<desc>`):

| Ticket | Chunk | Risk |
|---|---|---|
| #87 | Safety-net tests + budget CI full suite | none |
| #88 | Frontend URL-derived context + navigate-on-create | low |
| #89 | `shared/ai_client` library | none |
| #90 | ai `POST /ai/decide` (additive) | HIGH |
| #91 | chat service scaffold (infra, `/health` only) | low |
| #92 | conversations + tool registry + `/chat/stream` dark launch | HIGH |
| #93 | Frontend cutover to `/chat/stream` | HIGH |
| #94 | Retire users-service chat proxy | low |
| #95 | Retire ai chat stack; drop session tables; DAG complete | HIGH |
| #96 | parse-budget flow → chat; budget AI-free | med |
| #97 | OpenAPI→MCP bridge behind the registry interface | low |

Rollback: every ticket is a single revert; until #94/#95 land, reverting the frontend commit (#93) restores the fully-working legacy path. Worst case after #95: redeploy previous ai image + revert #94.

## Open Questions

None blocking. To resolve during implementation: exact pydantic-ai deferred-toolset API on the pinned version (#90, has fallback); whether the compose smoke script with Ollama is worth adding in #92 (optional).
