# ask-user-line

A Hermes plugin that lets the agent **pause mid-task and ask the LINE user ONE
question**, rendered as native **LINE quick-reply chips**, for the LINE-dedicated
Hermes instance behind the OpenAI **Responses** API (`/v1/responses`). The API
server ships a restricted toolset that drops the built-in interactive tools
(`clarify`, `send_message`); this plugin restores that capability in a form the
LINE backend (line-crm worker) can render.

On the Responses API the question is delivered **in-band**: when the agent calls
`ask_user_line`, the question spec appears as the `function_call` item's
`arguments` in the response the backend already reads. **No webhook, no spool
file, no backend round-trip is needed to receive the question.**

```
LINE user message → webhook → maybeSendOpenAIAutoReply → POST /responses
Hermes calls ask_user_line({message, kind, options}) → stop sentinel → turn ends
backend scans response.output for function_call name === "ask_user_line"
  → builds LINE text message with quickReply chips → replyMessage / pushMessage
user taps a chip (message action) → arrives as a NORMAL text webhook event
  → existing flow sends it as next `input` + previous_response_id → agent resumes
```

**Key insight:** the resume leg needs zero new code. Chips use `type: "message"`
actions, so the tapped label is delivered as ordinary typed text and flows into
the existing `previous_response_id` session chain.

> Deliberately NARROWER than [ask-user-form](../ask-user-form-plugin/): LINE
> quick replies cannot render multi-field forms. **One question per call.** If
> the agent needs several answers, it asks them one at a time across turns.

## Files

| File | Runs in | Purpose |
|------|---------|---------|
| `plugin.yaml` | Hermes | Manifest |
| `__init__.py` | Hermes | `register()` — wires the tool + audit hook |
| `schemas.py` | Hermes | `ask_user_line` tool schema (what the LLM fills in) |
| `tools.py` | Hermes | Handler — validate the ask, return the stop sentinel |

## Install

1. Copy this directory to `~/.hermes/plugins/ask-user-line/`.

2. Enable the plugin:
   ```bash
   hermes plugins enable ask-user-line
   ```
   or add it under `plugins.enabled` in `~/.hermes/config.yaml`:
   ```yaml
   plugins:
     enabled:
       - ask-user-line
   ```

3. **Enable the `ask_user_line` toolset for the API-server platform.** This is
   the step people miss. The API server ships a *restricted* toolset by design,
   and the plugin registers `ask_user_line` under its own toolset, which is
   **not** included automatically:
   ```yaml
   # config.yaml — add ask_user_line to whatever the API server platform uses
   toolsets:
     - hermes-api      # or your platform preset
     - ask_user_line
   ```
   Confirm over REST (deterministic — no need to ask the model):
   ```bash
   curl -s http://localhost:8642/v1/toolsets \
     -H "Authorization: Bearer $API_SERVER_KEY" | grep ask_user_line
   ```

4. Restart the API server.

5. (Recommended) Reinforce usage so the model reaches for the tool instead of
   guessing. Add a line to `SOUL.md`, your system prompt, or a skill:
   > When you need information, a choice, or confirmation from the LINE user,
   > call `ask_user_line`. One question per call. Never assume or fabricate
   > answers.

## The ask (what the backend reads)

The model fills in the `ask_user_line` schema; that object is exactly what
arrives as the `function_call.arguments`:

```json
{
  "message": "Which branch should I deploy?",
  "kind": "choice",
  "options": ["main", "develop", "release/2.1"]
}
```

### `kind` semantics

| kind | `options` | Rendered as |
|------|-----------|-------------|
| `choice` | **required**, 2–13 items, each ≤ 20 chars after trim, no duplicates | question text + one quick-reply chip per option |
| `confirm` | must be absent (`{"error": …}` if present) | question text + fixed **Yes** / **No** chips (labels hardcoded for v1; localize later via plugin config) |
| `freetext` | must be absent | plain text question, no chips — user types the answer |

Validation failures are returned as `{"error": "..."}` (never raised) so the
model can fix the call and retry. The backend re-validates everything
server-side anyway — it never trusts model output.

### Hard LINE limits (why the schema is shaped this way)

- Max **13** quick-reply items per message.
- Each chip label max **20** characters.
- `quickReply` is only honored on the **last** message of a send — the backend
  places the question last when narration text is also present.
- Chips are **ephemeral**: if the user types something else instead of tapping,
  that text flows into the chain as the answer. Acceptable by design.

## Reading the ask from a Responses stream

Watch the SSE `output_item` events (or read the final `response.output` array).
The `ask_user_line` call is a `function_call` item; its `arguments` is a JSON
**string**:

```jsonc
{ "type": "function_call", "name": "ask_user_line", "call_id": "chatcmpl-tool-…",
  "arguments": "{\"message\":\"…\",\"kind\":\"choice\",\"options\":[…]}" }
```

1. Find the `function_call` whose `name === "ask_user_line"`.
2. `const ask = JSON.parse(item.arguments)` → render `ask.message` (+ chips).
3. Keep the response `id` (`resp_…`) for the resume call.

The turn ends with `response.completed` / `status: "completed"`. The assistant
may emit a short "waiting for your reply" narration message — the backend sends
it as a separate text message BEFORE the question (so `quickReply` stays on the
last message).

> The tool's own result (the `function_call_output`) only carries a stop
> sentinel to end the turn. You don't need to read it — render from `arguments`.

## Resuming

The tapped chip arrives as a normal text webhook event. The existing backend
flow sends the label as the next `input` with `previous_response_id` — no
prefix, no JSON envelope; the plugin asks single flat questions, so plain text
answers are fine:

```jsonc
POST /v1/responses
{
  "model": "hermes-agent",
  "input": "develop",
  "previous_response_id": "resp_abc123",
  "store": true
}
```

Add an `Idempotency-Key` header keyed on the webhook event id if the Hermes
endpoint honors it — LINE may redeliver webhook events (optional for v1).

## How the "stop" works

The tool returns a sentinel result with no answer data and an explicit
stop-instruction, and the tool description states that calling it ends the
turn. With a capable model that reliably halts the loop (a scripted
`/v1/responses` test confirms it: `status: "completed"`, no fabricated answer).
For a deterministic guarantee, the `pre_tool_call` hook stub in `__init__.py`
shows where to block any further tool call once an ask is pending — enable it
once you've confirmed the block contract for your Hermes version.

## Deferred kinds (NOT implemented in v1)

- **`kind: "datetime"`** — needs LINE `datetimepicker` postback wiring: the
  picker result arrives as a *postback* webhook event, not a text message, so
  webhook.ts would need postback → Hermes session routing.
  <!-- TODO(v2): datetimepicker — add postback handling in line-crm webhook.ts,
       then add "datetime" to _VALID_KINDS + schema enum. -->
- **`kind: "form"`** — multi-field intake → LIFF form link fallback. Quick
  replies can't render forms; a LIFF page could, with its own submit → resume
  wiring.
  <!-- TODO(v2): form — render a LIFF link message, POST answers from the LIFF
       app as the resume input. -->

## Notes / limits

- **No out-of-band delivery.** The question rides in the response; there is no
  webhook and no spool.
- Reply tokens are single-use with ~1 min expiry — the backend's existing
  `pushMessage` fallback covers expiry.
- Flex-message rendering of choices is out of scope for v1 (quick replies only).
- Pure standard library — zero third-party dependencies.
