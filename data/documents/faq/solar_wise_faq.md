# Solar Wise — Frequently Asked Questions

*Starter FAQ set, grounded in this knowledge base's own sizing
methodology, standards summary, and Pakistan regulatory documents.
Extend this as real user questions surface during testing — per the
PRD (Section 5.3), the conversational panel should answer follow-ups
from this knowledge base and the calculation output, not from general
model knowledge, so keeping this file current directly improves answer
quality.*

**Q: Why does the recommended system size change so much between
winter and summer?**
Sizing is deliberately based on the worst month's peak sun hours (PSH),
not the annual average — see `sizing_methodology/`. This means the
system will produce more than enough energy in summer months, which is
intentional: it guarantees reliable output through winter, when solar
resource is lowest. The alternative (sizing to the annual average)
would leave the system under-producing for several winter months, which
is worse for a backup-focused user.

**Q: Do I need a battery if I just want to save money on my electricity
bill, not have backup during outages?**
Not necessarily. A grid-tied system without a battery can still offset
daytime grid consumption and reduce your bill through Pakistan's net
metering / net billing framework (see `pk_regulation_tariff/`). Battery
sizing in this project's methodology is driven specifically by a
declared backup requirement (essential loads vs. full house) and days
of autonomy — if backup during outages is not a priority, the battery
capacity and its added cost can be reduced or removed from the
recommendation.

**Q: Why did my export/net-metering credit come out lower than I
expected?**
Pakistan's regulatory framework shifted in 2025-2026 from one-to-one net
metering to a "net billing" mechanism, where exported surplus energy is
credited at a separate, generally lower reference rate than the retail
rate you pay for imported electricity — see `pk_regulation_tariff/` for
the detail and sourcing. This is a regulatory change, not a system
sizing issue, and it means self-consuming your own generation is now
relatively more valuable than exporting it, compared to the old regime.

**Q: The tool gave me a cost range instead of one number — why?**
Equipment pricing varies by brand, region, and installer margin, and
this project's cost dataset is a representative snapshot rather than a
live market feed (see PRD Section 10.1). A single point estimate would
imply more precision than the underlying data supports; a range is the
honest representation. Get an installer quote for a firm number before
purchasing.

**Q: Can the AI advisor just tell me a different, smaller system size if
my budget is fixed?**
No — per the project's core guardrail (PRD Section 6.2), the
conversational layer cannot alter or override a calculated number
directly. If your budget doesn't fit the recommended system, the
correct path is to change an input (e.g., a lower backup requirement,
different days of autonomy, or a smaller target load) so the Python
engine recalculates a genuinely smaller system — not to have the AI
adjust the displayed number without changing what it's based on.

**Q: What happens if the tool has no information on my specific
question?**
It should say so explicitly rather than answering from general
knowledge — this is a hard requirement (PRD Section 6.2 and Section 8's
"RAG groundedness" metric). If you hit a case where this doesn't happen,
that's a defect worth flagging during testing, not an acceptable
fallback behavior.

## How to extend this file

Add real questions as they surface during team testing and, later, from
actual users — particularly ones the conversational panel struggled to
answer well, since a documented FAQ answer is more reliable than hoping
the retrieval + generation pipeline improvises a good answer from
scattered context each time.
