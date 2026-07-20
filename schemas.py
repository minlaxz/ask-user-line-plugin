"""Schema for the ask_user_line tool — this is what the LLM sees and fills in.

Deliberately NARROWER than the ask-user-form plugin: LINE messages cannot
render multi-field forms, so this tool asks exactly ONE question per call.
The hard limits baked into the schema mirror the LINE Messaging API:
max 13 quick-reply items, each label at most 20 characters. (Rendering is the
worker's concern: confirm/buttons templates for confirm and choice<=4,
quick-reply chips for choice 5-13.)
"""

SEND_LINE_FLEX_SCHEMA = {
    "name": "send_line_flex",
    "description": (
        "Send a rich LINE Flex Message (card) or Flex Carousel to the user. "
        "Build the full Flex container JSON yourself: contents.type='bubble' for "
        "one card, or contents.type='carousel' with contents.contents = 1-12 "
        "bubbles. Delivered when your turn ends, in the order called, before any "
        "ask_user_line question. Do NOT repeat the card content as plain text."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "alt_text": {
                "type": "string",
                "maxLength": 400,
                "description": (
                    "Plain-text summary shown in push notifications / chat "
                    "list. Required, <= 400 chars."
                ),
            },
            "contents": {
                "type": "object",
                "description": (
                    "LINE Flex container JSON. Either a bubble "
                    "({type:'bubble', body:{type:'box', layout:'vertical', "
                    "contents:[...]}, ...}) or a carousel ({type:'carousel', "
                    "contents:[bubble, ...]}, max 12 bubbles). Total JSON "
                    "<= 50KB (hard LINE limits)."
                ),
            },
        },
        "required": ["alt_text", "contents"],
    },
}

ASK_USER_LINE_SCHEMA = {
    "name": "ask_user_line",
    "description": (
        "Pause and ask the LINE user ONE question. Rendered natively in LINE "
        "as tappable buttons or chips. Calling this ENDS YOUR TURN — output nothing "
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
