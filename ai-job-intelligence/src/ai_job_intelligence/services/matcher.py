from __future__ import annotations

from ai_job_intelligence.schemas import CandidateProfile, JobRequirements
import re
from ai_job_intelligence.services.ai_service import _AMBIGUOUS_SKILLS
from ai_job_intelligence.services import skill_evidence
from ai_job_intelligence.services.embedding_service import (
    calculate_similarity,
    max_similarity,
)


def _phrase_in_text(phrase: str, text: str) -> bool:
    """True if ``phrase`` occurs in ``text`` on word boundaries."""
    if not phrase:
        return False
    return re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", text) is not None


def analyze_match(
    candidate: CandidateProfile,
    requirements: JobRequirements,
) -> dict:
    """Compare a structured candidate profile with job requirements."""

    candidate_text = " ".join(
        candidate.technical_skills
        + candidate.soft_skills
        + candidate.experience
        + candidate.education
        + candidate.certifications
        + candidate.projects
        + candidate.keywords
    )

    candidate_lower = candidate_text.lower()
    candidate_skills_lower = [s.lower() for s in candidate.technical_skills]

    # Where the extractor found each skill, so a requirement met by a
    # described project can be reported differently from one met by a word in
    # a list. Missing on profiles cached before evidence existed, in which
    # case everything reads as "declared" -- the previous behaviour.
    evidence_by_skill = {
        e.skill.lower(): e for e in (candidate.skill_evidence or [])
    }

    # Lines describing what the candidate actually did. Kept as separate
    # short strings rather than one blob: a cosine score against a whole CV
    # is meaningless, but against a single bullet it is informative.
    activity_lines = [
        line
        for line in (list(candidate.experience) + list(candidate.projects))
        if line and len(line.strip()) >= 12
    ]

    matched_skills: list[str] = []
    missing_skills: list[str] = []
    match_evidence: dict[str, dict] = {}

    threshold = 0.75
    # Calibrated against the expanded query used in step 4b: a genuinely
    # relevant bullet scores around 0.6 and an unrelated one below 0.1, so
    # this sits comfortably between them rather than at an arbitrary value.
    activity_threshold = 0.55

    # Skills the described work implies without naming, keyed by skill so a
    # requirement can be looked up directly.
    implied_lookup = {
        hit.skill: hit.context
        for hit in skill_evidence.implied_skills("\n".join(activity_lines))
    }

    def record(skill: str, how: str, detail: str = "") -> None:
        matched_skills.append(skill)
        match_evidence[skill] = {"how": how, "detail": detail[:220]}

    for skill in requirements.technical_skills:
        skill_lower = skill.lower()

        # 1. Exact match against an extracted candidate skill. Where the
        #    extractor recorded evidence, report the stronger fact -- that the
        #    candidate described using it, not merely that they listed it.
        if skill_lower in candidate_skills_lower:
            hit = evidence_by_skill.get(skill_lower)
            if hit is not None and hit.source in (
                "experience",
                "projects",
                "certifications",
            ):
                record(skill, hit.source, hit.context)
            else:
                record(skill, "declared", hit.context if hit else "")
            continue

        # 2. Whole-phrase, word-boundary match anywhere in the candidate text.
        #    A plain substring test would let one-or-two letter skills ("R",
        #    "Go", "C") match almost any CV, and would match "Machine Learning"
        #    on the stray word "learning". Skill names that are also ordinary
        #    English words are excluded from this step entirely -- for those,
        #    step 1 (an explicit extracted skill) is the only evidence we trust.
        if skill_lower not in _AMBIGUOUS_SKILLS and _phrase_in_text(
            skill_lower, candidate_lower
        ):
            record(skill, "mentioned")
            continue

        # 3. Semantic fallback, skill-to-skill. Comparing the skill against the
        #    entire CV blob dilutes the signal below any useful threshold, so
        #    compare it against each extracted candidate skill instead.
        if max_similarity(skill, candidate.technical_skills) >= threshold:
            record(skill, "related")
            continue

        # 4. What the candidate *described doing*. This catches the CV that
        #    never writes "Docker" but says "containerised twelve services".
        #    Two mechanisms, cheapest and most certain first.
        if activity_lines:
            # 4a. A curated phrase that implies this skill. Deterministic and
            #     explainable: the matching sentence is shown to the candidate.
            implied = implied_lookup.get(skill)
            if implied is not None:
                record(skill, "described", implied)
                continue

            # 4b. Semantic similarity against each described activity. The
            #     bare skill name is a poor query -- "Docker" against a full
            #     sentence scores 0.42 however well it fits -- so it is
            #     expanded into a phrase shaped like the text it is compared
            #     with. Relevant lines then reach ~0.6 while unrelated ones
            #     stay below 0.1, which is what makes this threshold safe.
            query = f"{skill} experience, used {skill} in production"
            best_line = ""
            best_score = 0.0
            for line in activity_lines:
                score = max_similarity(query, [line])
                if score > best_score:
                    best_score, best_line = score, line
            if best_score >= activity_threshold:
                record(skill, "described", best_line)
                continue

        missing_skills.append(skill)

    if requirements.technical_skills:
        skills_score = (len(matched_skills) / len(requirements.technical_skills)) * 100
    else:
        skills_score = 0

    if requirements.experience_requirements:
        if not candidate.experience:
            experience_match = 0
        else:
            def _years_from_list(lst: list[str]) -> int | None:
                for s in lst:
                    m = re.search(r"(\d+)\s*(?:\+|years|year)", s.lower())
                    if m:
                        try:
                            return int(m.group(1))
                        except Exception:
                            continue
                return None

            req_years = _years_from_list(requirements.experience_requirements)
            cand_years = _years_from_list(candidate.experience)

            if req_years is not None and cand_years is not None:
                if req_years > 0:
                    experience_match = min(100, round((cand_years / req_years) * 100))
                else:
                    experience_match = 100
            else:
                experience_text = " ".join(candidate.experience)
                experience_similarity = calculate_similarity(
                    " ".join(requirements.experience_requirements),
                    experience_text,
                )
                experience_match = min(100, round(experience_similarity * 100))
    else:
        # The posting states no experience requirement, so there is nothing to
        # score. Recorded as "not specified" and dropped from the weighting
        # below -- scoring it 100 would have inflated the overall match for a
        # dimension the job never asked about.
        experience_match = None

    if requirements.education_requirements_list:
        if not candidate.education:
            education_match = 0
        else:
            education_text = " ".join(candidate.education)
            education_similarity = calculate_similarity(
                " ".join(requirements.education_requirements_list),
                education_text,
            )
            education_match = min(100, round(education_similarity * 100))
    else:
        education_match = None

    match_ratio = len(matched_skills) / max(len(requirements.technical_skills), 1)
    if match_ratio < 0.5:
        skills_score = min(skills_score, 50.0)

    # Weight only the dimensions the posting actually specifies, renormalising
    # so they still sum to 1. A job that asks for skills alone is scored purely
    # on skills, rather than being handed free marks for unstated requirements.
    weighted: list[tuple[float, float]] = []
    if requirements.technical_skills:
        weighted.append((skills_score, 0.50))
    if experience_match is not None:
        weighted.append((float(experience_match), 0.30))
    if education_match is not None:
        weighted.append((float(education_match), 0.20))

    if weighted:
        total_weight = sum(w for _, w in weighted)
        final_score = round(sum(v * w for v, w in weighted) / total_weight)
    else:
        # Nothing measurable in the posting at all.
        final_score = 0

    recommendations = []
    for skill in missing_skills:
        recommendations.append(f"Add {skill} to your skills section or gain hands-on experience with it.")
        recommendations.append(f"Complete a project using {skill} and add it to your experience section.")

    if match_ratio < 0.5:
        recommendations.append(
            f"You are missing {len(missing_skills)} key technical skills. "
            f"Consider upskilling in {', '.join(missing_skills[:3])} to improve your fit for this role."
        )

    if experience_match is not None and experience_match < 50:
        recommendations.append(
            "Highlight more relevant work experience. Include metrics and achievements for each role."
        )

    if education_match is not None and education_match < 50:
        recommendations.append(
            "Consider adding relevant certifications or coursework to strengthen your education profile."
        )

    if candidate.projects:
        recommendations.append(
            "Add links to your GitHub or portfolio for the projects listed in your CV."
        )

    if not recommendations:
        recommendations.append("Your profile covers the identified technical requirements. Highlight your achievements with metrics.")

    measured = []
    if requirements.technical_skills:
        measured.append("skills")
    if experience_match is not None:
        measured.append("experience")
    if education_match is not None:
        measured.append("education")

    if requirements.technical_skills:
        summary = (
            f"The candidate matches {len(matched_skills)} of "
            f"{len(requirements.technical_skills)} identified technical "
            f"requirements. Overall compatibility score: {final_score}%"
        )
    else:
        summary = (
            f"This posting lists no specific technical requirements. "
            f"Overall compatibility score: {final_score}%"
        )

    if measured:
        summary += f", scored on {', '.join(measured)}."
    else:
        summary += ". The posting did not state requirements that could be scored."

    return {
        "match_score": final_score,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "experience_match": experience_match,
        "education_match": education_match,
        "recommendations": recommendations[:8],
        # How each requirement was met, so the candidate can be shown why a
        # skill counted -- and so "described" matches, which are the least
        # obvious, can be surfaced rather than looking like guesses.
        "match_evidence": match_evidence,
        "summary": summary,
    }
