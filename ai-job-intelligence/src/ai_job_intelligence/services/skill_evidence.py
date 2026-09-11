"""Find the skills a CV demonstrates, not only the ones it lists.

A skills list is the weakest claim in a CV: anyone can type "Kubernetes".
The strongest is a sentence describing something delivered -- "owned the
Kubernetes migration and wrote the Helm charts". Previously only the first
kind was really used, so a candidate who wrote about their work in prose
rather than keeping a keyword list scored as though they had no skills at all.

Every hit records *where* it was found and the sentence that evidenced it.
That does three things: it lets matching weigh demonstrated skills above
declared ones, it lets the UI show the candidate why a skill counted, and it
gives an honest answer to "the skill is in my CV, why did it not match?".
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from ai_job_intelligence.services.cv_sections import section_text, split_sections

# How much each location is trusted. A skills list is a claim; a project
# description is a demonstration.
SOURCE_WEIGHT = {
    "experience": 1.0,
    "projects": 0.95,
    "certifications": 0.9,
    "summary": 0.7,
    "declared": 0.6,
    "other": 0.5,
}

# Sections mined for demonstrated skills, mapped to the label recorded.
PROSE_SECTIONS = {
    "experience": "experience",
    "projects": "projects",
    "summary": "summary",
    "certifications": "certifications",
    "header": "other",
}


@dataclass
class SkillHit:
    """One skill, where it was found, and the words that evidenced it."""

    skill: str
    source: str
    context: str = ""

    @property
    def weight(self) -> float:
        return SOURCE_WEIGHT.get(self.source, 0.5)

    @property
    def demonstrated(self) -> bool:
        """True when the skill was used in a described activity."""
        return self.source in ("experience", "projects", "certifications")


def _sentence_around(text: str, index: int) -> str:
    """The sentence containing the character at ``index``.

    Bullet points and newlines end a sentence as surely as a full stop does,
    which matters because CV prose is mostly fragments.
    """
    start = max(
        text.rfind(".", 0, index),
        text.rfind("\n", 0, index),
        text.rfind("•", 0, index),
        text.rfind(";", 0, index),
    )
    ends = [
        i
        for i in (
            text.find(".", index),
            text.find("\n", index),
            text.find("•", index),
            text.find(";", index),
        )
        if i != -1
    ]
    end = min(ends) if ends else len(text)
    return text[start + 1 : end].strip(" -–—•\t")


def _find_all(needle: str, haystack_lower: str) -> list[int]:
    """Every word-boundary occurrence of ``needle``.

    Word boundaries rather than a substring search: without them "r" and "go"
    match nearly every CV, and "java" matches "javascript".
    """
    if not needle:
        return []
    pattern = rf"(?<!\w){re.escape(needle)}(?!\w)"
    return [m.start() for m in re.finditer(pattern, haystack_lower)]


def collect_evidence(
    text: str,
    vocabulary: list[str],
    canonical: dict[str, str],
    ambiguous: set[str],
    ambiguity_test,
) -> list[SkillHit]:
    """Every skill in ``vocabulary`` that the CV evidences.

    ``ambiguity_test`` decides whether a skill name that is also an ordinary
    English word ("go", "r", "excel") is being used as a skill here. It is
    passed in rather than imported so this module does not depend on the
    heuristics living in ai_service.
    """
    sections = split_sections(text)

    # Longest first so "apache spark" is claimed before bare "spark", and the
    # parts of a multi-word skill are not then matched again on their own.
    ordered = sorted({v.lower() for v in vocabulary}, key=len, reverse=True)

    hits: dict[tuple[str, str], SkillHit] = {}
    claimed_words: set[str] = set()

    def scan(block: str, source: str) -> None:
        if not block.strip():
            return
        lower = block.lower()
        for term in ordered:
            if term in claimed_words:
                continue
            positions = _find_all(term, lower)
            if not positions:
                continue
            if term in ambiguous and not ambiguity_test(term, lower, block):
                continue

            name = canonical.get(term, term.title())
            key = (name, source)
            if key not in hits:
                hits[key] = SkillHit(
                    skill=name,
                    source=source,
                    context=_sentence_around(block, positions[0])[:220],
                )
            if " " in term:
                claimed_words.update(term.split())

    # The declared list first, so its terms are attributed to "declared"
    # rather than being picked up later as prose.
    scan(section_text(sections, "skills"), "declared")
    for section, label in PROSE_SECTIONS.items():
        scan(section_text(sections, section), label)

    # Skills the CV demonstrates without naming: "containerised our services"
    # is Docker, whether or not the word appears anywhere.
    activity = "\n".join(
        section_text(sections, name) for name in ("experience", "projects", "summary")
    )
    for hit in implied_skills(activity):
        key = (hit.skill, hit.source)
        if key not in hits:
            hits[key] = hit

    # A CV with no recognisable headings puts everything under "header",
    # which the loop above already covers as "other".
    return list(hits.values())


def best_hit_per_skill(hits: list[SkillHit]) -> dict[str, SkillHit]:
    """The strongest evidence for each skill.

    A skill both listed and described keeps the description, because that is
    the evidence worth showing the candidate and worth weighting in a match.
    """
    best: dict[str, SkillHit] = {}
    for hit in hits:
        current = best.get(hit.skill)
        if current is None or hit.weight > current.weight:
            best[hit.skill] = hit
    return best


def rank_skills(hits: list[SkillHit]) -> list[str]:
    """Skill names, strongest evidence first.

    Replaces an arbitrary cap that used to truncate the list at twelve: a CV
    listing seventeen skills lost five of them with no indication which. If a
    caller must limit the list, it should now cut the weakest rather than
    whatever happened to be scanned last.
    """
    best = best_hit_per_skill(hits)
    return [
        name
        for name, _ in sorted(
            best.items(),
            key=lambda kv: (-kv[1].weight, kv[0].lower()),
        )
    ]


# --- Implied skills -------------------------------------------------------
# What someone *describes doing* usually names the outcome, not the tool:
# "containerised our services", "automated the release pipeline", "rebuilt
# environments from definitions". A keyword scan finds none of those, so a
# strong candidate reads as having no relevant skills at all.
#
# These phrases are the vocabulary of the work itself. They are curated rather
# than learned because the result has to be explainable -- when a skill counts,
# the candidate is shown the sentence that earned it -- and because a wrong
# implication is worse than a missed one: it tells someone they have a skill
# they do not.
SKILL_IMPLICATIONS: dict[str, tuple[str, ...]] = {
    "Docker": (
        "containeris", "containeriz", "container image", "dockerfile",
        "container registry", "packaged as containers",
    ),
    "Kubernetes": (
        "orchestrat", "k8s", "cluster in production", "managed cluster",
        "pod ", "helm chart", "container orchestration",
    ),
    "Terraform": (
        "infrastructure as code", "infrastructure definitions",
        "provisioned infrastructure", "rebuilt from scratch",
        "declarative infrastructure",
    ),
    "CI/CD": (
        "release pipeline", "deployment pipeline", "build pipeline",
        "continuous integration", "continuous delivery", "continuous deployment",
        "automated deploy", "automated the release", "automated releases",
    ),
    "REST": (
        "rest api", "restful", "http api", "json api", "public api",
        "api endpoint",
    ),
    "SQL": (
        "wrote queries", "query optimis", "query optimiz", "database queries",
        "stored procedure", "joins across",
    ),
    "ETL": (
        "data pipeline", "batch pipeline", "ingestion pipeline",
        "extract transform", "transformed raw data",
    ),
    "Machine Learning": (
        "trained a model", "trained models", "predictive model",
        "classification model", "recommendation engine", "model accuracy",
    ),
    "Agile": (
        "sprint", "stand-up", "standup", "backlog grooming", "retrospective",
        "scrum ceremon",
    ),
    "Leadership": (
        "led a team", "managed a team", "mentored", "line managed",
        "hired and onboarded", "team lead",
    ),
    "Observability": (
        "monitoring and alert", "dashboards and alert", "on-call",
        "incident response", "reduced mttr", "instrumented",
    ),
    "Testing": (
        "test coverage", "wrote tests", "automated tests", "unit tests",
        "integration tests", "regression suite",
    ),
    "Accessibility": (
        "wcag", "screen reader", "accessible to", "a11y",
    ),
    "Data Analysis": (
        "analysed data", "analyzed data", "reporting dashboards",
        "insights from data", "cohort analysis",
    ),
    "Project Management": (
        "delivered on schedule", "managed the roadmap", "coordinated across",
        "stakeholder", "ran the project",
    ),
}


def implied_skills(activity_text: str) -> list[SkillHit]:
    """Skills evidenced by described work rather than named outright.

    Matched on lowercase substrings deliberately: these are phrase stems
    ("containeris" covering both spellings and every inflection), which is
    exactly the case where a word-boundary match is too strict.
    """
    lower = activity_text.lower()
    found: list[SkillHit] = []
    for skill, phrases in SKILL_IMPLICATIONS.items():
        for phrase in phrases:
            index = lower.find(phrase)
            if index == -1:
                continue
            found.append(
                SkillHit(
                    skill=skill,
                    source="experience",
                    context=_sentence_around(activity_text, index)[:220],
                )
            )
            break
    return found
