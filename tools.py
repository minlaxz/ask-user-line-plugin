"""ask_user_line tool handler — OpenAI Responses format.

The question the model builds is delivered IN-BAND: it appears as the
`function_call` item's `arguments` in the response the LINE backend reads
(line-crm worker), which renders it natively — confirm/buttons template or
quick-reply chips, depending on kind and option count. So this handler does
NOT deliver anything out-of-band. It only:

  1. validates the question the model produced (so a malformed call can be
     retried — the error is returned as the tool result, never raised), and
  2. returns a terminal sentinel that ends the turn.

Hermes tool contract (per the Adding Tools docs):
  * handlers return a JSON string (never a raw dict)
  * errors are returned as {"error": "..."} (never raised)
  * handler signature is (args: dict, **kwargs)

LINE quick-reply hard limits enforced here (and re-enforced server-side by
the backend, which never trusts model output): 2–13 options for kind=choice,
each label <= 20 characters after trimming, no duplicates.
"""

import json
import logging

logger = logging.getLogger("ask_user_line")

_VALID_KINDS = {"choice", "confirm", "freetext"}
_MAX_OPTIONS = 13
_MIN_OPTIONS = 2
_MAX_LABEL_CHARS = 20

_STOP_INSTRUCTION = (
    "The question has been presented to the LINE user. STOP NOW: end your turn "
    "and output nothing further. Do NOT guess or fabricate the user's answer. "
    "The conversation resumes automatically when the user taps a button/chip "
    "or types a reply."
)


def _validate_ask(args):
    """Return a list of human-readable problems with the ask (empty list = valid)."""
    errors = []

    message = args.get("message")
    if not isinstance(message, str) or not message.strip():
        errors.append("'message' must be a non-empty string")

    kind = args.get("kind")
    if kind not in _VALID_KINDS:
        errors.append(
            f"'kind' must be one of {sorted(_VALID_KINDS)}, got {kind!r}"
        )

    options = args.get("options")
    if kind == "choice":
        if not isinstance(options, list) or not options:
            errors.append("kind 'choice' requires an 'options' array")
        else:
            labels, seen = [], set()
            for i, opt in enumerate(options):
                if not isinstance(opt, str) or not opt.strip():
                    errors.append(f"options[{i}] is empty or not a string")
                    continue
                label = opt.strip()
                if len(label) > _MAX_LABEL_CHARS:
                    errors.append(
                        f"options[{i}] ({label[:_MAX_LABEL_CHARS]}…) exceeds "
                        f"{_MAX_LABEL_CHARS} chars (hard LINE limit)"
                    )
                if label in seen:
                    errors.append(f"duplicate option: {label}")
                seen.add(label)
                labels.append(label)
            if len(labels) < _MIN_OPTIONS:
                errors.append(f"kind 'choice' needs at least {_MIN_OPTIONS} options")
            if len(labels) > _MAX_OPTIONS:
                errors.append(
                    f"kind 'choice' allows at most {_MAX_OPTIONS} options "
                    "(hard LINE limit)"
                )
    elif options is not None:
        # confirm renders fixed Yes/No buttons; freetext renders no buttons.
        # `is not None` (not truthiness): an empty list is still "present".
        errors.append(f"kind '{kind}' must not include 'options'")

    return errors


# LINE Flex hard limits (re-enforced server-side by the backend).
_FLEX_MAX_ALT_TEXT_CHARS = 400
_FLEX_CAROUSEL_MAX_BUBBLES = 12
_FLEX_MAX_JSON_BYTES = 50 * 1024


def _validate_flex(args):
    """Return a list of human-readable problems with the flex call (empty = valid)."""
    errors = []

    alt_text = args.get("alt_text")
    if not isinstance(alt_text, str) or not alt_text.strip():
        errors.append("'alt_text' must be a non-empty string")
    elif len(alt_text.strip()) > _FLEX_MAX_ALT_TEXT_CHARS:
        errors.append(f"'alt_text' exceeds {_FLEX_MAX_ALT_TEXT_CHARS} chars (hard LINE limit)")

    contents = args.get("contents")
    if not isinstance(contents, dict):
        errors.append("'contents' must be a Flex container object")
        return errors

    ctype = contents.get("type")
    if ctype == "carousel":
        bubbles = contents.get("contents")
        if not isinstance(bubbles, list) or not bubbles:
            errors.append("carousel requires a non-empty 'contents' array of bubbles")
        else:
            if len(bubbles) > _FLEX_CAROUSEL_MAX_BUBBLES:
                errors.append(
                    f"carousel allows at most {_FLEX_CAROUSEL_MAX_BUBBLES} bubbles "
                    "(hard LINE limit)"
                )
            for i, bubble in enumerate(bubbles):
                if not isinstance(bubble, dict) or bubble.get("type") != "bubble":
                    errors.append(f"carousel contents[{i}] must be a bubble object")
    elif ctype != "bubble":
        errors.append(f"contents.type must be 'bubble' or 'carousel', got {ctype!r}")

    if len(json.dumps(contents, ensure_ascii=False).encode()) > _FLEX_MAX_JSON_BYTES:
        errors.append("contents JSON exceeds 50KB (hard LINE limit)")

    return errors


def handle_send_line_flex(args, **kwargs):
    # Never raise, even on a non-dict payload (never trust model output).
    args = args if isinstance(args, dict) else {}

    errors = _validate_flex(args)
    if errors:
        # Actionable error so the model can fix the call and retry.
        return json.dumps({"error": "invalid flex message: " + "; ".join(errors)})

    contents = args.get("contents", {})
    logger.info(
        "send_line_flex queued (type=%s): %s",
        contents.get("type"),
        args.get("alt_text"),
    )

    # Delivery is IN-BAND: the backend renders from this function_call's
    # `arguments` when the turn ends. Non-terminal — the model may add
    # narration text or an ask_user_line call in the same turn.
    return json.dumps({
        "status": "queued",
        "note": "Flex message will be delivered to the LINE user when your turn ends.",
    })


def handle_ask_user_line(args, **kwargs):
    # Never raise, even on a non-dict payload (never trust model output).
    args = args if isinstance(args, dict) else {}

    errors = _validate_ask(args)
    if errors:
        # Actionable error so the model can fix the call and retry.
        return json.dumps({"error": "invalid ask: " + "; ".join(errors)})

    logger.info(
        "ask_user_line presented (kind=%s): %s",
        args.get("kind"),
        args.get("message"),
    )

    # Terminal sentinel. This is the tool RESULT (the function_call_output). It
    # carries no answer data — its only job is to end the turn. The backend does
    # not need to read it; it renders from the function_call's `arguments`.
    return json.dumps({"status": "awaiting_user_reply", "instruction": _STOP_INSTRUCTION})
