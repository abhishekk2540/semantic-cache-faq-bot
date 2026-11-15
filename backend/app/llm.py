import time

from .config import LLM_MODE, LLM_MODEL, MOCK_LLM_MS

SYSTEM_PROMPT = (
    "You are a support assistant for an Indian e-commerce store. "
    "Answer in 2-3 short sentences, in the same language as the customer (English or Hinglish). "
    "Do not invent order details."
)


def _mock(question):
    time.sleep(MOCK_LLM_MS / 1000)
    answer = f"[mock LLM] Here is a detailed support reply to: {question}"
    tokens = len(question.split()) * 4 + 120  # rough estimate
    return answer, tokens


def _anthropic(question):
    import anthropic  # lazy import so mock mode needs no extra package

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    msg = client.messages.create(
        model=LLM_MODEL,
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": question}],
    )
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    return text, msg.usage.input_tokens + msg.usage.output_tokens


def ask_llm(question):
    """Returns (answer, tokens_used)."""
    if LLM_MODE == "anthropic":
        return _anthropic(question)
    return _mock(question)
