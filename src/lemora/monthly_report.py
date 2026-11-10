import sys
from datetime import date
from pathlib import Path

from lemora.db import query
from lemora.metrics import collect

WINDOW = "created_at >= %(s)s::date AND created_at < (%(s)s::date + interval '1 month')"
WINDOW_F = "f.created_at >= %(s)s::date AND f.created_at < (%(s)s::date + interval '1 month')"

def table(title, rows, columns):
    out = [f"## {title}", ""]
    if not rows:
        return out + ["None this month.", ""]
    out.append("| " + " | ".join(columns) + " |")
    out.append("|" + "---|" * len(columns))
    for r in rows:
        out.append("| " + " | ".join(str(r[c]).replace("|", "/").replace("\n", " ") for c in columns) + " |")
    return out + [""]


def run(month=None):
    month = month or date.today().strftime("%Y-%m")
    p = {"s": f"{month}-01"}
    answers = query(f"SELECT count(*) AS n FROM messages WHERE role = 'assistant' AND {WINDOW}", p)[0]["n"]

    lines = [f"# Lemora failure report: {month}", "",
             f"Assistant answers this month: **{answers}**", ""]

    lines += table("Answers shoppers corrected or rejected", query(f"""
        SELECT f.verdict AS verdict,
               (SELECT u.content FROM messages u WHERE u.conversation_id = m.conversation_id
                  AND u.role = 'user' AND u.message_id < m.message_id
                ORDER BY u.message_id DESC LIMIT 1) AS question,
               left(m.content, 160) AS answer,
               coalesce(f.correction_text, '') AS correction
        FROM feedback f JOIN messages m ON m.message_id = f.message_id
        WHERE f.verdict IN ('corrected', 'rejected') AND {WINDOW_F}
        ORDER BY f.created_at""", p), ["verdict", "question", "answer", "correction"])

    lines += table("Unmet demand: searches that found nothing or needed relaxing", query(f"""
        SELECT filters::text AS filters, array_to_string(relaxed, ', ') AS relaxed,
               result_count, count(*) AS times
        FROM search_log WHERE {WINDOW}
          AND (result_count = 0 OR cardinality(relaxed) > 0)
        GROUP BY filters::text, relaxed, result_count ORDER BY times DESC LIMIT 20""", p),
        ["filters", "relaxed", "result_count", "times"])

    lines += table("System events (failures, blocks, rate limits)", query(f"""
        SELECT kind, count(*) AS times, max(left(detail, 120)) AS example
        FROM error_log WHERE {WINDOW} GROUP BY kind ORDER BY times DESC""", p),
        ["kind", "times", "example"])

    lines += table("Slowest answers", query(f"""
        SELECT message_id, latency_ms, coalesce(input_tokens, 0) AS input_tokens,
               left(content, 100) AS answer
        FROM messages WHERE role = 'assistant' AND latency_ms IS NOT NULL AND {WINDOW}
        ORDER BY latency_ms DESC LIMIT 5""", p),
        ["message_id", "latency_ms", "input_tokens", "answer"])

    lines += table("Repeat failures by brand (all time)", collect()["failures_by_brand"],
                   ["brand", "failures"])

    Path("reports").mkdir(exist_ok=True)
    path = Path("reports") / f"failures-{month}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    print("wrote", path)


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else None)