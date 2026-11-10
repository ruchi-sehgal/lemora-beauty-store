import os
from dataclasses import dataclass
from pathlib import Path

from pydantic_ai import Agent, RunContext

from lemora.schemas import AssistantReply, SearchFilters
from lemora.search import search_with_relaxing

PROMPT = (Path(__file__).parent / "prompts" / "v3.md").read_text(encoding="utf-8")


@dataclass
class ChatDeps:
    shown_skus: list[str]


agent = Agent(
    "groq:" + os.environ["GROQ_MODEL"],
    output_type=AssistantReply,
    instructions=PROMPT,
    deps_type=ChatDeps,
    retries={"output": 3, "tools": 2},
    model_settings={"groq_reasoning_effort": "none", "max_tokens": 400},
)

KEEP = ("sku_id", "brand", "name", "product_type", "price_sgd", "benefit",
        "key_ingredients", "fragrance_notes", "skin_types", "concerns")


@agent.tool
def find_products(
    ctx: RunContext[ChatDeps],
    filters: SearchFilters,
    include_already_shown: bool = False,
) -> dict:
    """Search the Lemora catalogue with filters. Returns matching products and
    relaxed_filters, the list of filters that had to be dropped to find any.
    Products already shown to this shopper are skipped automatically. Set
    include_already_shown=true only if the shopper asks about one of them again."""
    if not include_already_shown and ctx.deps.shown_skus:
        skip = sorted(set((filters.exclude_skus or []) + ctx.deps.shown_skus))
        filters = filters.model_copy(update={"exclude_skus": skip})
    rows, relaxed = search_with_relaxing(filters)
    products = [{k: r[k] for k in KEEP if r.get(k)} for r in rows[:6]]
    return {"products": products, "relaxed_filters": relaxed}