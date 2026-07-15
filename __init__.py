"""ask-user-line — a Hermes plugin that lets the agent ask the LINE user ONE
question and yield the turn, over the OpenAI Responses API.

On `/v1/responses` the question is delivered IN-BAND: when the agent calls
ask_user_line, the question spec is the `function_call` item's `arguments` in
the response the LINE backend (line-crm worker) reads. The backend renders it
as a LINE text message with native quick-reply chips. No webhook, no spool,
no backend round-trip to receive it.

    agent calls ask_user_line(message=..., kind=..., options=[...])
      -> appears as a function_call (arguments = the question) in the response
      -> tool returns a stop sentinel -> model ends its turn (status: completed)
         ... backend renders quick-reply chips, user taps one ...
      -> the tapped label arrives as a NORMAL text webhook event
      -> backend POSTs it as the next `input` with previous_response_id
      -> agent resumes

Because chips use `type: "message"` actions, the resume leg needs zero new
code — the tapped label is delivered as ordinary typed text.

Registers:
  * tool  `ask_user_line`   — the model calls this to ask ONE question
  * hook  `post_tool_call`  — audit log when ask_user_line fires
  * hook  `pre_tool_call`   — observer; optional hard-stop enforcement point

See README.md for the full backend contract.
"""

import logging

from .schemas import ASK_USER_LINE_SCHEMA
from .tools import handle_ask_user_line

logger = logging.getLogger("ask_user_line")


def register(ctx):
    # --- Tool: ask_user_line ---------------------------------------------------
    ctx.register_tool(
        name="ask_user_line",
        toolset="ask_user_line",
        schema=ASK_USER_LINE_SCHEMA,
        handler=handle_ask_user_line,
        description=(
            "Pause and ask the LINE user ONE question "
            "(renders as quick-reply chips). Ends your turn."
        ),
    )

    # --- Hook: audit ----------------------------------------------------------
    # post_tool_call signature per Hermes docs: (tool_name, params, result)
    def on_post_tool_call(tool_name, params, result):
        if tool_name == "ask_user_line":
            logger.info(
                "ask_user_line dispatched (kind=%s): %s",
                params.get("kind"),
                params.get("message"),
            )

    ctx.register_hook("post_tool_call", on_post_tool_call)

    # --- Hook: optional hard-stop enforcement ---------------------------------
    # The plugin is already correct WITHOUT this hook: the tool returns a terminal
    # sentinel that tells the model to end its turn. This is an extra, deterministic
    # safety net — if your Hermes build's `pre_tool_call` supports a block/deny
    # return, you can use it to reject any *further* tool call in the same turn
    # after an ask_user_line. Ships as an OBSERVER (returns None = allow); verify
    # the block contract for your version before enabling a block return.
    def on_pre_tool_call(tool_name, params, **kwargs):
        return None  # observer-only

    ctx.register_hook("pre_tool_call", on_pre_tool_call)

    logger.info("ask-user-line plugin registered (tool=ask_user_line, toolset=ask_user_line)")
