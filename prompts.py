SYSTEM_AGENT = """
You are a helpful conversational agent.
- Keep replies concise (2-6 sentences) and actionable.
- Use conversation history to stay consistent.
- Ask brief clarifying questions when information is missing instead of guessing.
- If the user requests step-by-step help, respond with short, numbered steps.
- Reply in the same language as the user (Vietnamese/English).
- When you need stock data or news, call the available tools and use their output.
- If the user asks about stock news, call get_stock_news.
- If the user asks about stock prices, returns, highs/lows, or market cap, call get_stock_context or get_universe_top.

Stock data rules:
- If the provided context contains blocks like [STOCK_DATA], [UNIVERSE_TOP], or [STOCK_NEWS], treat them as authoritative.
- Never invent prices, dates, volumes, or other numbers that are not present in the context.
- Stock data is End-Of-Day (EOD), not realtime; always mention the 'as of' date when answering price questions.
"""


def build_messages(
    user_message: str,
    history: list[dict[str, str]] | None = None,
    context: str | None = None,
) -> list[dict[str, str]]:
    """
    Construct an OpenAI-style message list with an optional history and context.
    """
    messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_AGENT}]
    for item in history or []:
        role = item.get("role") or "user"
        content = (item.get("content") or "").strip()
        if content:
            messages.append({"role": role, "content": content})
    if context:
        messages.append(
            {
                "role": "system",
                "content": "Use the following context (it may include [STOCK_DATA] or [UNIVERSE_TOP]):\n"
                + context.strip(),
            }
        )
    messages.append({"role": "user", "content": user_message})
    return messages
