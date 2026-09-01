---
agent: 'agent'
description: 'Review code, a diff, or a codebase against the Fastapi-Template layered architecture'
---

## Task

Review the selected code, diff, or codebase against this repo's layered architecture
(see `.github/copilot-instructions.md` for the condensed rules, or
`docs/backend-architecture.md` for the full detail). This is a strict,
findings-first review — **never modify code as part of this review** unless
separately asked to apply the fixes. Hand back a clear, honest account of what's
wrong and what to do about it, and let the person decide what to fix.

For every issue found:

1. **Name the anti-pattern plainly** — cite the specific rule/anti-pattern it violates.
   Don't soften an actual violation into "you might consider..." — say it's wrong and
   why.
2. **Point at the exact location** — file, line/function.
3. **State the concrete consequence** — what breaks, what becomes untestable, what
   fails silently (e.g. "this is silent data loss," not "this could be improved").
4. **Give the specific suggested fix** — real code or a concrete instruction, not a
   vague direction.

Structure the response as a numbered list of findings, worst/most-structural first,
and close by asking which of these to fix (by number, "all", or "none") — do not edit
anything until that's answered. If the code genuinely checks out, say so plainly too;
don't manufacture findings to look thorough.

Common things to check: business logic leaking into endpoints, services querying the
DB directly instead of through a repository, domain exceptions vs `HTTPException`
mixing across layers, services returning raw ORM models instead of `TypedDict`
contracts, more than 5 repositories injected into one service, an `auto_commit=False`
repo call with no paired `commit()`/`rollback()`, missing exception-to-HTTP mapping
for something a called service can raise, and SQLAlchemy relationship mistakes
(untyped `relationship()`, writable `secondary=` on a many-to-many, mismatched
`Mapped[T | None]` vs `nullable`, unscoped bidirectional cascades, unguarded N+1
access in a loop).

Scope: `${selection}`
