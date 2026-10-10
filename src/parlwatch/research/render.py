from parlwatch.research.coverage import coverage
from parlwatch.research.schema import Research, Source

ICON = {"supported": "✅ supported", "partly_supported": "🟡 partly supported", "contradicted": "❌ contradicted", "outdated": "🕓 outdated",
        "unverifiable": "❔ unverifiable", "pending": "⏳ pending", "not_checked": "⬜ not checked"}
TIER = {"primary": "primary", "secondary": "secondary", "weak": "weak"}


def _src(s: Source) -> str:
    return f"[{s.title}]({s.url}) ({TIER[s.tier]}, {s.accessed})"


def to_markdown(r: Research) -> str:
    md = [f"# Context and follow-up: {r.title}", "",
          f"*Meeting {r.meeting_date} · researched {r.researched_on} · {r.method}*", "",
          "> **How to read this.** Each assertion is checked against what was known before the meeting and what happened after. Verdicts: "
          + ", ".join(ICON.values()) + ". Source tiers: **primary** = official or original document, **secondary** = reputable press or law firm, "
          "**weak** = aggregator or blog (treat as a lead, not evidence). Follow-ups are due 3, 6 and 12 months after the meeting.", ""]
    md += ["## Follow-up schedule", "", "| checkpoint | due | status |", "|---|---|---|"]
    for c in r.checkpoints:
        md.append(f"| {c.label} | {c.due} | {('done ' + c.done_on) if c.done_on else 'open'}{(' · ' + c.note) if c.note else ''} |")
    md += ["", "## Context coverage", "", "A hearing is researched from every side, not only the witness's: supply, demand, regulation, finance, energy and resources, "
           "geopolitics and security, technology.", "", "| dimension | status | topics | findings before / after |", "|---|---|---|---|"]
    for c in coverage(r):
        md.append(f"| {c['dimension']} | {c['status'].replace('_', ' ')} | {', '.join(c['topics']) or '-'} | {c['findings_before']} / {c['findings_after']} |"
                  + (f" {c['note']}" if c["note"] else ""))
    md += ["", "## Topics: before and after", ""]
    for t in r.topics:
        md += [f"### {t.title}" + (f" · *{t.dimension.replace('_', ' ')}*" if t.dimension else ""), f"*Why it matters:* {t.why_it_matters}", ""]
        if t.before:
            md += ["**Before the meeting (what it builds on)**", ""]
            for f in t.before:
                md.append(f"- **{f.date}** · {f.summary} " + " ".join(f"[{i + 1}]" for i in range(0)) + (" — " + "; ".join(_src(s) for s in f.sources) if f.sources else ""))
            md.append("")
        if t.after:
            md += ["**After the meeting**", ""]
            for f in t.after:
                md.append(f"- **{f.date}** · {f.summary}" + (" — " + "; ".join(_src(s) for s in f.sources) if f.sources else ""))
            md.append("")
    md += ["## Assertions checked", ""]
    for c in r.claims:
        md += [f"### {c.id} · {c.speaker} [{c.time}] · {c.kind}", f"**Claim:** {c.text}"]
        if c.quote_fr:
            md.append(f"> « {c.quote_fr} »")
        md.append("")
        for k in c.checks:
            who = f" by {k.by}" + (f" v{k.agent_version}" if k.agent_version else "") if k.by else ""
            conf = f", confidence {k.confidence}" if k.confidence != "unrated" else ""
            md += [f"- **{k.checkpoint}** (checked {k.checked_on}{who}{conf}): {ICON[k.verdict]}. {k.evidence}"
                   + (" Sources: " + "; ".join(_src(s) for s in k.sources) if k.sources else "")]
        if c.next_step:
            md.append(f"- *Next:* {c.next_step}")
        md.append("")
    if r.queue:
        md += ["## Research queue (noticed, not yet checked)", "", *[f"- {q}" for q in r.queue], ""]
    return "\n".join(md)
