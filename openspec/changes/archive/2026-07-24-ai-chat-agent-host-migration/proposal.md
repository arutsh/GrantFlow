# Proposal: AI Chat Migration to Chat-Service (Agent Host) Architecture

> Approved plan: `/home/noro/.claude/plans/discuss-few-bits-d-tender-marble.md`. Architecture, decisions, and chunking are final; GitHub tickets #87–#97 (arutsh/GrantFlow) exist, one PR per ticket, merged sequentially.

## Why

The AI chat flow has a circular dependency: the frontend reaches ai through a users-service proxy, and ai calls back into budget over REST to execute actions (`ai → budget` via `chat_agent.py` REST helpers; `budget → ai` via the parse flow). Budget-domain knowledge (intent schemas, REST dispatchers) and conversation state live inside the ai service. This makes the system hard to test, blocks adding AI-enabled domains (reports), and couples services so tightly that no service can evolve — or be rewritten in another stack — independently.

## What Changes

- **New `services/chat`** (agent host): owns conversations/messages server-side (any-device history), the tool registry, and the dispatch loop; serves `POST /chat/stream` with the SSE protocol the frontend already speaks.
- **ai becomes pure stateless reasoning**: new `POST /ai/decide` (message + history + tool JSON schemas + domain_context → tool-call decision | reply). BYOK model resolution and rate limiting stay in ai.
- **New `shared/ai_client`** in-process library: request building, retries, timeouts, decision parsing for any service calling ai.
- **Frontend**: chat context derived from the current URL (`/budgets/:id`); after AI creates a budget the app navigates to it instead of surfacing the id in chat; payload renamed to generic `context_id` + `page`; chat API cut over to `/chat/stream`.
- **BREAKING (internal only, staged)**: users-service chat proxy retired; ai's old chat stack (`/ai/chat/stream`, orchestrator, intent schemas, session tables) deleted; `BUDGET_SERVICE_URL` removed from ai; `/budgets/ai/stream` + `ai_service_url` removed from budget (parse flow relocates to chat). Old chat history is dropped (fresh start — decided).
- **Tool registry is MCP-shaped from day one** (`list_tools()`/`call_tool()`); after cutover its internals swap to an in-process FastMCP `from_openapi` bridge over budget's OpenAPI spec.
- Resulting dependency DAG: `frontend → chat`, `chat → ai`, `chat → domain REST`. No ai → domain, no domain → domain, no domain → ai.

## Capabilities

### New Capabilities
- `ai-decide`: ai's stateless decision endpoint — request/response contract, provider resolution (BYOK), rate limiting, no domain knowledge or outbound domain calls.
- `ai-client`: shared library contract for calling ai — decision parsing, error taxonomy (unavailable/rate-limited), retry semantics.
- `chat-conversations`: server-side conversation persistence and retrieval — provider-neutral messages, per-user any-device access, history cap, get-or-create semantics.
- `chat-streaming`: `POST /chat/stream` behavior — SSE event protocol, orchestration guards (context required for targeted tools), tool dispatch and error relay.
- `chat-tool-registry`: MCP-shaped registry interface, curated budget toolset (model never supplies resource IDs), and the OpenAPI→MCP bridge equivalence requirement.
- `chat-parse-budget`: parse-text-to-budget flow served by chat — consumes ai's parse stream, creates via budget's public REST, re-emits progress events.
- `chat-url-context`: frontend chat context derived from the current route; navigation to newly created budgets; generic `context_id`/`page` payload.

### Modified Capabilities
None — `openspec/specs/` is empty (first OpenSpec change in this repo). Removals of legacy behavior are captured inside the new capabilities' requirements.

## Impact

- **Services**: new `services/chat` (FastAPI + Postgres + alembic + compose + CI + nginx route); ai gains `/ai/decide`, loses its chat stack and session tables; users loses the chat proxy; budget loses `/budgets/ai/stream` and all AI config — ends with zero AI references.
- **Shared**: new `shared/ai_client` package (triggers all service CI via `shared/**` path filters).
- **Frontend**: `AIChatPanel`/`AiChatContext` slimmed; `streamAiChat` moves to `src/api/chatApi.ts` pointing at `/chat/stream`; `streamAiCreateBudget` repointed to `/chat/parse-budget/stream`.
- **Infra**: nginx locations added (`/api/v1/chat/`) and removed (users chat stream); docker-compose entries; `.github/workflows/chat.yml`; budget CI fixed to run its full test suite.
- **Data**: new chat-service `conversations`/`messages` tables; `ai_chat_sessions`/`ai_chat_messages` dropped without migration (approved).
- **Sequencing/rollback**: 11 sequential PRs (tickets #87–#97); the legacy path stays deployed until the frontend cutover has soaked, so every step is revertible in isolation.
