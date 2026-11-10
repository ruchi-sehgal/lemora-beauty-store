from lemora.db import query
from lemora.embeddings import embed_query, to_pgvector
from lemora.schemas import SearchFilters


def search_products(f: SearchFilters, query_vec=None) -> list[dict]:
    rows = query(
        "SELECT sku_id, brand, name, category, product_type, price_sgd, benefit, "
        "key_ingredients, fragrance_notes, skin_types, concerns, gender "
        "FROM products WHERE is_active "
        "AND (%(category)s::text IS NULL OR category = %(category)s::text) "
        "AND (%(brands)s::text[] IS NULL OR brand = ANY(%(brands)s::text[])) "
        "AND (%(product_type)s::text IS NULL OR product_type = %(product_type)s::text) "
        "AND (%(skin_types)s::text[] IS NULL OR skin_types && %(skin_types)s::text[] "
        "     OR 'all' = ANY(skin_types)) "
        "AND (%(concerns)s::text[] IS NULL OR concerns && %(concerns)s::text[]) "
        "AND (%(gender)s::text IS NULL OR gender IS NULL OR gender = 'unisex' "
        "     OR gender = %(gender)s::text) "
        "AND (%(max_price)s::numeric IS NULL OR price_sgd <= %(max_price)s::numeric) "
        "AND (%(exclude_skus)s::text[] IS NULL OR NOT (sku_id = ANY(%(exclude_skus)s::text[]))) "
        "AND (%(exclude_brands)s::text[] IS NULL OR NOT (brand = ANY(%(exclude_brands)s::text[]))) "
        "ORDER BY (CASE WHEN %(qv)s::vector IS NULL THEN 0 "
        "               ELSE embedding <=> %(qv)s::vector END), price_sgd, brand, name "
        "LIMIT %(limit)s",
        {
            "category": f.category,
            "brands": f.brands,
            "product_type": f.product_type,
            "skin_types": f.skin_types,
            "concerns": f.concerns,
            "gender": f.gender,
            "max_price": f.max_price_sgd,
            "exclude_skus": f.exclude_skus,
            "exclude_brands": f.exclude_brands,
            "qv": query_vec,
            "limit": f.limit,
        },
    )
    for r in rows:
        r["price_sgd"] = float(r["price_sgd"])
    return rows


RELAX_ORDER = [
    ("max_price_sgd", "the price limit"),
    ("concerns", "the concern"),
    ("skin_types", "the skin type"),
    ("product_type", "the product type"),
    ("brands", "the brand"),
]


def vector_for(f: SearchFilters):
    if not f.semantic_query:
        return None
    try:
        return to_pgvector(embed_query(f.semantic_query))
    except Exception as error:                       # never let search fail because of this
        print("embedding failed, using filters only:", repr(error))
        return None


def search_with_relaxing(f: SearchFilters) -> tuple[list[dict], list[str]]:
    qv = vector_for(f)                               # embed once, reuse for every relaxed retry
    relaxed = []
    rows = search_products(f, qv)
    for field, label in RELAX_ORDER:
        if rows:
            break
        if getattr(f, field) is None:
            continue
        f = f.model_copy(update={field: None})
        relaxed.append(label)
        rows = search_products(f, qv)
    return rows, relaxed