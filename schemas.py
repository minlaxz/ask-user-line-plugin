"""Schema for the ask_user_line tool — this is what the LLM sees and fills in.

Deliberately NARROWER than the ask-user-form plugin: LINE quick replies cannot
render multi-field forms, so this tool asks exactly ONE question per call.
The hard limits baked into the schema mirror the LINE Messaging API:
max 13 quick-reply items, each label at most 20 characters.
"""

ASK_USER_LINE_SCHEMA = {
    "name": "ask_user_line",
    "description": (
        "Pause and ask the LINE user ONE question. Rendered as native LINE "
        "quick-reply chips. Calling this ENDS YOUR TURN — output nothing "
        "further, never fabricate the answer. If you need several answers, "
        "ask them one at a time across turns."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "The question text shown in chat. Required.",
            },
            "kind": {
                "type": "string",
                "enum": ["choice", "confirm", "freetext"],
                "description": (
                    "choice = tappable options; confirm = yes/no; "
                    "freetext = user types the answer."
                ),
            },
            "options": {
                "type": "array",
                "items": {"type": "string", "maxLength": 20},
                "minItems": 2,
                "maxItems": 13,
                "description": (
                    "Required for kind=choice. Max 13 options, each label "
                    "<= 20 chars (hard LINE limits)."
                ),
            },
        },
        "required": ["message", "kind"],
    },
}
