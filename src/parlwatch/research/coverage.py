"""Context coverage: which dimensions of the context have been researched for a meeting, before and after it."""

from parlwatch.research.schema import DIMENSIONS, Research


def coverage(r: Research) -> list[dict]:
    """One row per dimension: the topics covering it, how many findings before/after the meeting, and a status.

    covered = at least one topic with findings before AND after the meeting (or before only, when the meeting is too recent for 'after');
    partial = topics exist but findings are missing on one side; missing = no topic; not_relevant = explicitly marked in `dimension_notes`.
    """
    rows = []
    for dim in DIMENSIONS:
        topics = [t for t in r.topics if t.dimension == dim]
        nb, na = sum(len(t.before) for t in topics), sum(len(t.after) for t in topics)
        note = r.dimension_notes.get(dim, "")
        if note.lower().startswith("not relevant"):
            status = "not_relevant"
        elif not topics:
            status = "missing"
        elif nb == 0:
            status = "partial"
        else:
            status = "covered"
        rows.append({"dimension": dim, "status": status, "topics": [t.id for t in topics], "findings_before": nb, "findings_after": na, "note": note})
    return rows


def gaps(r: Research) -> list[str]:
    return [x["dimension"] for x in coverage(r) if x["status"] in ("missing", "partial")]
