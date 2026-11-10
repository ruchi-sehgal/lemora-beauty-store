import os
from pathlib import Path

from pydantic_ai import Agent

from lemora.schemas import AssistantReply, SearchFilters
from lemora.search import search_with_relaxing

PROMPT = (Path(__file__).parent / "prompts" / "v1.md").read_text(encoding="utf-8")

agent = Agent(
    "groq:" + os.environ["GROQ_MODEL"],
    output_type=AssistantReply,
    instructions=PROMPT,
)


@agent.tool_plain
def find_products(filters: SearchFilters) -> dict:
    """Search the Lemora catalogue with filters. Returns matching products and
    relaxed_filters, the list of filters that had to be dropped to find any."""
    rows, relaxed = search_with_relaxing(filters)
    return {"products": rows, "relaxed_filters": relaxed}