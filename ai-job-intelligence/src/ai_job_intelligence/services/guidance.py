"""Turn an analysis into advice someone can act on.

The previous output was a flat list built by appending two sentences per
missing skill -- "Add Kubernetes to your skills section", "Complete a project
using Kubernetes" -- so a candidate missing eight skills got sixteen bullets
that all said the same two things. Volume read as thoroughness while carrying
almost no information, and nothing indicated what to do first.

What replaces it is a small number of grouped, ordered actions. Each one
names the thing to do, says why it matters for *this* posting, and carries
the skills it refers to so the UI can attach learning resources to it.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field


# Lower sorts first. The order encodes a judgement: a missing hard requirement
# costs more interviews than an unpolished CV, and both cost more than
# formatting. Effort is the tie-breaker -- among equally important actions,
# the one done this afternoon comes first.
PRIORITY_BLOCKING = 1   # the reason this application gets filtered out
PRIORITY_IMPORTANT = 2  # materially improves the odds
PRIORITY_POLISH = 3     # worth doing, not why you were rejected


@dataclass
class Action:
    """One thing to do, and why."""

    title: str
    detail: str
    group: str
    priority: int
    # Skills this action is about, so the UI can offer resources for them.
    skills: list[str] = field(default_factory=list)
    # Roughly how long it takes, to make the list schedulable rather than
    # aspirational.
    effort: str = ""


GROUP_LABELS = {
    "gap": "Close the gap",
    "cv": "Strengthen your CV",
    "experience": "Frame your experience",
    "positioning": "Position yourself",
}


def _plural(n: int, one: str, many: str) -> str:
    return one if n == 1 else many


def build_guidance(
    *,
    matched_skills: list[str],
    missing_skills: list[str],
    experience_match: int | None,
    education_match: int | None,
    match_score: int,
    has_projects: bool = False,
    job_title: str = "",
) -> list[dict]:
    """Ordered, deduplicated advice for one analysis.

    Returns plain dicts so this can be serialised straight into a response.
    """
    actions: list[Action] = []
    missing = [s for s in (missing_skills or []) if s and s.strip()]
    matched = [s for s in (matched_skills or []) if s and s.strip()]

    # --- The gap ---------------------------------------------------------
    if missing:
        # The first two or three are where the return is. Naming them beats
        # one bullet per skill, and it tells the reader where to start.
        focus = missing[:3]
        rest = len(missing) - len(focus)
        detail = (
            f"This posting asks for {len(missing)} "
            f"{_plural(len(missing), 'skill', 'skills')} your CV does not "
            f"mention. Start with {', '.join(focus)}"
        )
        detail += (
            f" — the remaining {rest} matter less on their own."
            if rest > 0
            else "."
        )
        actions.append(
            Action(
                title=f"Learn {focus[0]}" if len(focus) == 1 else f"Start with {focus[0]} and {focus[1]}",
                detail=detail,
                group="gap",
                priority=PRIORITY_BLOCKING if len(missing) > 2 else PRIORITY_IMPORTANT,
                skills=focus,
                effort="Weeks, not days",
            )
        )

        actions.append(
            Action(
                title="Build one small thing with it, then write it down",
                detail=(
                    f"A reviewer believes a project they can open more than a "
                    f"line in a skills list. One deployed page, script or "
                    f"repository using {focus[0]} is worth more than a course "
                    f"certificate."
                ),
                group="gap",
                priority=PRIORITY_IMPORTANT,
                skills=focus[:1],
                effort="A weekend",
            )
        )

    # --- The CV itself ---------------------------------------------------
    if matched:
        shown = ", ".join(matched[:4])
        actions.append(
            Action(
                title="Move what already matches to the top",
                detail=(
                    f"You match on {shown}"
                    + (f" and {len(matched) - 4} more" if len(matched) > 4 else "")
                    + ". Most reviewers decide in seconds, so these belong in "
                    "the first third of the page, not the skills list at the "
                    "bottom."
                ),
                group="cv",
                priority=PRIORITY_IMPORTANT,
                skills=matched[:4],
                effort="An hour",
            )
        )

    if experience_match is not None and experience_match < 50:
        actions.append(
            Action(
                title="Rewrite your bullets around outcomes",
                detail=(
                    "Your experience scored low against what this posting asks "
                    "for. Replace duty descriptions with results: what changed, "
                    "by how much, and over what period. \"Cut deployment time "
                    "from 40 to 8 minutes\" outranks \"responsible for CI/CD\"."
                ),
                group="experience",
                priority=PRIORITY_BLOCKING if experience_match < 25 else PRIORITY_IMPORTANT,
                effort="An evening",
            )
        )

    if education_match is not None and education_match < 50:
        actions.append(
            Action(
                title="Add the credential that answers this requirement",
                detail=(
                    "The posting states an education requirement your CV does "
                    "not clearly meet. A named certification or relevant "
                    "coursework, with the year, closes this faster than a "
                    "degree does."
                ),
                group="cv",
                priority=PRIORITY_IMPORTANT,
                effort="Varies",
            )
        )

    if has_projects:
        actions.append(
            Action(
                title="Link the projects you already list",
                detail=(
                    "Your CV names projects but a reader cannot open them. A "
                    "GitHub or live URL next to each one turns a claim into "
                    "evidence at no cost to you."
                ),
                group="cv",
                priority=PRIORITY_POLISH,
                effort="Ten minutes",
            )
        )

    # --- Whether to apply at all ----------------------------------------
    if match_score >= 75:
        actions.append(
            Action(
                title="Apply now, and say why you fit in the first line",
                detail=(
                    f"At {match_score}% this is a strong match"
                    + (f" for {job_title}" if job_title else "")
                    + ". Open your message with the two requirements you meet "
                    "best rather than a summary of your career."
                ),
                group="positioning",
                priority=PRIORITY_BLOCKING,
                effort="Twenty minutes",
            )
        )
    elif match_score < 40 and missing:
        actions.append(
            Action(
                title="Treat this posting as a target, not today's application",
                detail=(
                    f"At {match_score}% the gap is real. Use this list to "
                    "choose what to learn, then look for roles asking for what "
                    "you already have while you close it."
                ),
                group="positioning",
                priority=PRIORITY_IMPORTANT,
                effort="Ongoing",
            )
        )

    if not actions:
        actions.append(
            Action(
                title="You cover what this posting asks for",
                detail=(
                    "Nothing in the requirements is missing from your CV. Spend "
                    "your effort on the covering message instead: name the two "
                    "things you have done that map most directly to this role."
                ),
                group="positioning",
                priority=PRIORITY_IMPORTANT,
                effort="Twenty minutes",
            )
        )

    actions.sort(key=lambda a: a.priority)
    return [asdict(a) for a in actions]
