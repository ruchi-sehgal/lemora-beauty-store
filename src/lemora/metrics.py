from lemora.db import query


def one(sql):
    return query(sql)[0]


def pct(n, d):
    return f"{100 * n / d:.0f}%" if d else "no data yet"


def collect():
    answers = one("""
        SELECT count(*) AS answers,
               coalesce(round(avg(latency_ms)), 0) AS avg_latency_ms,
               coalesce(round(avg(input_tokens)), 0) AS avg_input_tokens,
               coalesce(round(avg(output_tokens)), 0) AS avg_output_tokens
        FROM messages WHERE role = 'assistant'""")
    fb = one("""
        SELECT count(*) FILTER (WHERE verdict = 'accepted') AS accepted,
               count(*) FILTER (WHERE verdict = 'corrected') AS corrected,
               count(*) FILTER (WHERE verdict = 'rejected') AS rejected,
               round(avg(csat_score)::numeric, 2) AS avg_csat,
               count(csat_score) AS csat_count
        FROM feedback""")
    rated = fb["accepted"] + fb["corrected"] + fb["rejected"]
    searches = one("""
        SELECT count(*) AS total,
               count(*) FILTER (WHERE result_count = 0 OR cardinality(relaxed) > 0) AS unmet
        FROM search_log""")
    catalogue = one("""
        SELECT count(*) FILTER (WHERE is_active) AS active,
               count(*) FILTER (WHERE is_active AND embedding IS NOT NULL) AS with_vector
        FROM products""")
    return {
        "tiles": [
            ("Accepted unchanged", pct(fb["accepted"], rated), f"{rated} answers rated"),
            ("Corrected (manual overrides)", pct(fb["corrected"], rated), ""),
            ("Rejected", pct(fb["rejected"], rated), ""),
            ("Satisfaction (1-5)", fb["avg_csat"] or "no ratings yet", f"{fb['csat_count']} ratings"),
            ("Answers given", answers["answers"], ""),
            ("Conversations", one("SELECT count(*) AS n FROM conversations")["n"], "history kept"),
            ("Average answer time", f"{answers['avg_latency_ms'] / 1000:.1f}s", ""),
            ("Average tokens per answer", f"{answers['avg_input_tokens']} in / {answers['avg_output_tokens']} out", ""),
            ("Searches needing relaxing or empty", pct(searches["unmet"], searches["total"]), f"{searches['unmet']} of {searches['total']}"),
            ("Products with fresh embedding", f"{catalogue['with_vector']} / {catalogue['active']}", ""),
        ],
        "by_version": query("""
            SELECT m.prompt_version AS version,
                   count(DISTINCT m.message_id) AS answers,
                   count(DISTINCT m.message_id) FILTER (WHERE f.verdict = 'accepted') AS accepted,
                   count(DISTINCT m.message_id) FILTER (WHERE f.verdict IN ('corrected', 'rejected')) AS not_ok
            FROM messages m LEFT JOIN feedback f ON f.message_id = m.message_id
            WHERE m.role = 'assistant' GROUP BY m.prompt_version ORDER BY m.prompt_version"""),
        "failures_by_brand": query("""
            SELECT p.brand, count(*) AS failures
            FROM feedback f
            JOIN messages m ON m.message_id = f.message_id
            CROSS JOIN LATERAL unnest(m.recommended_skus) AS s(sku)
            JOIN products p ON p.sku_id = s.sku
            WHERE f.verdict IN ('corrected', 'rejected')
            GROUP BY p.brand ORDER BY failures DESC LIMIT 10"""),
        "unmet": query("""
            SELECT filters::text AS filters, count(*) AS times
            FROM search_log WHERE result_count = 0 OR cardinality(relaxed) > 0
            GROUP BY filters::text ORDER BY times DESC LIMIT 10"""),
        "corrections": query("""
            SELECT f.correction_text, left(m.content, 120) AS answer, f.created_at
            FROM feedback f JOIN messages m ON m.message_id = f.message_id
            WHERE f.verdict = 'corrected' AND f.correction_text IS NOT NULL
            ORDER BY f.created_at DESC LIMIT 10"""),
        "ingest": query(
            "SELECT started_at, embedded, already_fresh, seconds FROM ingest_runs ORDER BY run_id DESC LIMIT 5"),
    }