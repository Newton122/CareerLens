"""Split a CV into its sections, whatever the writer called them.

The previous parser recognised a section only when a line *started* with the
exact word ("experience") and was under twenty characters. That silently lost
the entire employment history of any CV headed "PROFESSIONAL EXPERIENCE",
"Work Experience", "Employment History" or "Career Summary" -- five of the
eight headings people actually use. Nothing failed and nothing was logged; the
experience score simply came out at zero and every skill mentioned only in a
job description was invisible to matching.

Sections are therefore matched on a set of synonyms per section, anywhere in
a short line, in any case, with or without trailing punctuation or decoration.
"""
from __future__ import annotations

import re

# Order matters only for readability. A line is tested against every section.
SECTION_SYNONYMS: dict[str, tuple[str, ...]] = {
    "experience": (
        "experience", "work experience", "professional experience",
        "employment history", "employment", "work history", "career history",
        "professional background", "career summary", "relevant experience",
        "professional experience & achievements", "work",
    ),
    "education": (
        "education", "academic background", "academic qualifications",
        "qualifications", "academics", "educational background", "studies",
    ),
    "skills": (
        "skills", "technical skills", "core skills", "key skills",
        "competencies", "core competencies", "areas of expertise",
        "expertise", "technologies", "tech stack", "toolkit", "proficiencies",
        "skills & tools", "technical proficiencies",
    ),
    "projects": (
        "projects", "personal projects", "selected projects", "side projects",
        "portfolio", "notable projects", "open source",
    ),
    "certifications": (
        "certifications", "certificates", "licenses", "accreditations",
        "courses", "training", "professional development",
    ),
    "summary": (
        "summary", "profile", "professional summary", "about", "about me",
        "objective", "career objective", "personal statement", "overview",
        "profile summary",
    ),
}

# A heading is short, and is not a sentence. Both tests matter: "Experience"
# is a heading, "I have five years of experience building web services" is
# not, and only the length check separates them.
MAX_HEADING_LENGTH = 46

_DECORATION = re.compile(r"^[\s\-–—=*#•>|\[\(]+|[\s\-–—=*#•<|\]\):]+$")


def _normalise_heading(line: str) -> str:
    """Strip the decoration people put around headings."""
    return _DECORATION.sub("", line).strip().lower()


def heading_section(line: str) -> str | None:
    """The section this line introduces, or None if it is not a heading."""
    stripped = line.strip()
    if not stripped or len(stripped) > MAX_HEADING_LENGTH:
        return None

    cleaned = _normalise_heading(stripped)
    if not cleaned:
        return None

    # A heading may carry a trailing count or date range; drop anything after
    # a separator so "Experience (2019 - 2024)" still reads as a heading.
    cleaned = re.split(r"[(\[]|\s{2,}|\t", cleaned)[0].strip()

    for section, names in SECTION_SYNONYMS.items():
        for name in names:
            # Exact, or the heading plus a colon -- but never a substring
            # match, or "work" would fire on "Network Engineer".
            if cleaned == name or cleaned == f"{name}:":
                return section
    return None


def split_sections(text: str) -> dict[str, list[str]]:
    """Group a CV's lines under the heading that introduced them.

    Content appearing before any heading lands under "header", which is where
    a name and contact details normally are, and is also where a CV with no
    headings at all puts everything.
    """
    sections: dict[str, list[str]] = {"header": []}
    current = "header"

    for raw in text.split("\n"):
        section = heading_section(raw)
        if section is not None:
            current = section
            sections.setdefault(current, [])
            continue
        line = raw.strip()
        if line:
            sections.setdefault(current, []).append(line)

    return sections


def section_text(sections: dict[str, list[str]], name: str) -> str:
    """All the text under one section, as a single block."""
    return "\n".join(sections.get(name, []))


def prose_sections(sections: dict[str, list[str]]) -> str:
    """Everything that describes what the person actually did.

    This is the text worth mining for skills that were never listed: a
    "Skills" line can be padded with anything, but a sentence describing a
    delivered project is evidence.
    """
    parts = []
    for name in ("summary", "experience", "projects", "certifications", "header"):
        block = section_text(sections, name)
        if block:
            parts.append(block)
    return "\n".join(parts)
