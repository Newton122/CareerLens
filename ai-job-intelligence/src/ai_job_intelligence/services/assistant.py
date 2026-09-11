"""The CareerLens domain assistant.

Deliberately *not* "user question -> Gemini -> answer". That shape cannot cite
anything, cannot answer questions about this user's own data, and will happily
invent a salary. Instead the pipeline is:

    1. intent detection    what kind of question is this?
    2. retrieval           pull the facts that bear on it -- the user's parsed
                           CV profile, and job postings ranked by embedding
                           similarity to the question itself
    3. context building    render those facts as text the model may use
    4. grounded generation ask the model to answer *only* from that context
    5. sources             return what the answer was built from

Every step degrades safely. With no API key, or if the model call fails, the
deterministic responder answers from the same retrieved context, so the
assistant stays useful and still cites its sources.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np

from ai_job_intelligence.models.cv import CV
from ai_job_intelligence.models.job import Job
from ai_job_intelligence.schemas import CandidateProfile
from ai_job_intelligence.services import semantic_index, vector_store

logger = logging.getLogger(__name__)

# How many retrieved jobs are put in front of the model.
MAX_CONTEXT_JOBS = 5

# A retrieved job must be at least this close to the question to be cited.
RETRIEVAL_FLOOR = 0.20


@dataclass
class Source:
    """A fact the answer was allowed to use, surfaced to the user."""

    type: str          # "cv" | "job" | "market"
    label: str
    ref: int | None = None
    detail: str = ""

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "label": self.label,
            "ref": self.ref,
            "detail": self.detail,
        }


@dataclass
class Context:
    intent: str
    profile: CandidateProfile | None
    jobs: list[tuple[Job, float]] = field(default_factory=list)
    skill_demand: dict[str, int] = field(default_factory=dict)
    open_job_count: int = 0
    sources: list[Source] = field(default_factory=list)


# --- 1. intent -----------------------------------------------------------

# Ordered most specific first: "what skills am I missing" is a gap question,
# not a skills question, so `gaps` must get the chance to claim it. Ties are
# broken by the length of the matched keyword, so a long distinctive phrase
# outweighs an incidental short word.
_INTENTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("gaps", ("gap", "missing", "lack", "learn", "improve", "upskill",
              "should i study", "what should i", "get better", "weak")),
    ("salary", ("salary", "pay", "compensation", "earn", "money", "rate",
                "worth", "how much")),
    ("jobs", ("job", "role", "position", "opening", "vacancy", "hiring",
              "apply", "fit me", "suit me", "match me", "recommend")),
    ("experience", ("experience", "work history", "career path", "background")),
    ("cv", ("cv", "resume", "my profile", "document")),
    ("skills", ("skill", "strength", "good at", "tech stack", "know")),
)

# Intents where the answer is about *this candidate's* fit, so retrieval should
# be steered by their profile and not by the wording of the question alone.
_FIT_INTENTS = {"jobs", "gaps", "salary"}


def detect_intent(message: str) -> str:
    lowered = message.lower()
    best, best_score = "general", 0
    for intent, keywords in _INTENTS:
        score = sum(len(k) for k in keywords if k in lowered)
        if score > best_score:
            best, best_score = intent, score
    return best


# --- 2. retrieval --------------------------------------------------------


def build_context(
    db,
    message: str,
    cv: CV | None,
    profile: CandidateProfile | None,
) -> Context:
    """Gather the facts relevant to this question."""
    ctx = Context(intent=detect_intent(message), profile=profile)

    if profile is not None and cv is not None:
        ctx.sources.append(
            Source(
                type="cv",
                label=f"Your CV ({cv.filename})",
                ref=cv.id,
                detail=(
                    f"{len(profile.technical_skills)} skills, "
                    f"{len(profile.experience)} experience entries, "
                    f"{len(profile.education)} education entries"
                ),
            )
        )

    open_jobs = db.query(Job).filter(Job.status == "open").all()
    ctx.open_job_count = len(open_jobs)
    if not open_jobs:
        return ctx

    # Demand signal straight from the postings.
    for job in open_jobs:
        for skill in semantic_index._parse_skills(job.required_skills):
            key = skill.strip()
            if key:
                ctx.skill_demand[key] = ctx.skill_demand.get(key, 0) + 1

    # Retrieve against the question, so "who needs Kubernetes people" and
    # "what should I learn" pull different postings.
    query_vec = vector_store.encode(message)

    # For questions about the user's own fit, a bare question like "which jobs
    # suit me?" carries almost no domain signal and would retrieve noise. Blend
    # it with the candidate's profile vector so retrieval is steered by who
    # they actually are.
    if ctx.intent in _FIT_INTENTS and profile is not None:
        profile_vec = vector_store.encode(vector_store.profile_to_text(profile))
        blended = query_vec + profile_vec
        norm = float(np.linalg.norm(blended))
        if norm:
            query_vec = blended / norm

    vectors = semantic_index.get_job_vectors(db, open_jobs)
    by_id = {j.id: j for j in open_jobs}

    ranked = vector_store.rank(
        query_vec, vectors, top_k=MAX_CONTEXT_JOBS, min_score=RETRIEVAL_FLOOR
    )
    # A fit question should always come back with the best available options,
    # even when nothing clears the floor -- "here are the closest" beats
    # "I found nothing".
    if not ranked and ctx.intent in _FIT_INTENTS:
        ranked = vector_store.rank(query_vec, vectors, top_k=MAX_CONTEXT_JOBS)

    ctx.jobs = [(by_id[jid], score) for jid, score in ranked if jid in by_id]

    for job, score in ctx.jobs:
        ctx.sources.append(
            Source(
                type="job",
                label=f"{job.title}" + (f" at {job.company}" if job.company else ""),
                ref=job.id,
                detail=f"relevance {score:.2f}",
            )
        )

    if ctx.skill_demand:
        ctx.sources.append(
            Source(
                type="market",
                label=f"{len(open_jobs)} open job posting(s) on CareerLens",
                detail="used for skill demand and salary figures",
            )
        )

    return ctx


# --- 3. context rendering ------------------------------------------------


def render_context(ctx: Context) -> str:
    """Render retrieved facts as the only material the model may draw on."""
    blocks: list[str] = []

    if ctx.profile is not None:
        p = ctx.profile
        blocks.append(
            "CANDIDATE PROFILE (parsed from their CV)\n"
            f"- technical skills: {', '.join(p.technical_skills) or 'none detected'}\n"
            f"- soft skills: {', '.join(p.soft_skills) or 'none detected'}\n"
            f"- experience entries: {'; '.join(p.experience[:5]) or 'none detected'}\n"
            f"- education: {'; '.join(p.education[:3]) or 'none detected'}\n"
            f"- certifications: {', '.join(p.certifications) or 'none'}\n"
            f"- projects: {'; '.join(p.projects[:3]) or 'none'}"
        )
    else:
        blocks.append("CANDIDATE PROFILE: no CV uploaded yet.")

    if ctx.jobs:
        lines = ["RELEVANT OPEN JOBS (retrieved for this question)"]
        for job, score in ctx.jobs:
            skills = ", ".join(semantic_index._parse_skills(job.required_skills))
            salary = ""
            if job.salary_min or job.salary_max:
                salary = f", pay {job.salary_min or '?'}-{job.salary_max or '?'}"
            lines.append(
                f"- [job {job.id}] {job.title}"
                f"{f' at {job.company}' if job.company else ''}"
                f" ({job.location or 'location unspecified'}{salary})"
                f"\n  requires: {skills or 'not specified'}"
            )
        blocks.append("\n".join(lines))
    else:
        blocks.append("RELEVANT OPEN JOBS: none matched this question.")

    if ctx.skill_demand:
        top = sorted(ctx.skill_demand.items(), key=lambda kv: kv[1], reverse=True)[:10]
        blocks.append(
            "SKILL DEMAND (count of open postings requiring each)\n"
            + "\n".join(f"- {name}: {count}" for name, count in top)
        )

    return "\n\n".join(blocks)


# --- 4. generation -------------------------------------------------------

_SYSTEM_RULES = """You are CareerLens, a career assistant.

Answer ONLY from the CONTEXT below. The context is the complete set of facts
you may use.

Rules:
- Never invent job titles, companies, salaries, or skills that are not in the context.
- If the context does not contain the answer, say so plainly and suggest what
  the user could do (upload a CV, browse jobs) instead of guessing.
- Refer to jobs by their title as written in the context.
- Never state a salary figure that is not in the context.
- Be concise: 2-4 sentences unless asked for a list.
- Address the user as "you". Do not mention "the context" or "the candidate".
"""


def _generate_with_llm(message: str, context_text: str) -> str | None:
    try:
        from google import genai  # type: ignore
        from ai_job_intelligence.config import GOOGLE_API_KEY

        if not GOOGLE_API_KEY:
            return None

        client = genai.Client(api_key=GOOGLE_API_KEY)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=(
                f"{_SYSTEM_RULES}\n\n"
                f"CONTEXT\n=======\n{context_text}\n\n"
                f"QUESTION\n========\n{message}"
            ),
        )
        text = (response.text or "").strip()
        return text or None
    except Exception:
        logger.exception("Assistant LLM call failed; falling back to deterministic answer")
        return None


def _display_skill(name: str) -> str:
    """The spelling a person expects to read.

    Skill demand is counted from raw posting text, so the keys arrive as
    whatever the employer typed -- usually lowercase. "python" in a sentence
    about your career reads as a typo.
    """
    from ai_job_intelligence.services.ai_service import _FRAMEWORK_MAP

    key = name.strip().lower()
    return _FRAMEWORK_MAP.get(key, name.strip().title())


def _generate_deterministic(message: str, ctx: Context) -> str:
    """Answer from retrieved facts without a model.

    Used when no API key is configured or the model call fails. It says only
    things that are true of the retrieved context.
    """
    p = ctx.profile
    if p is None:
        return (
            "I don't have a CV for you yet, so I can't give personalised advice. "
            "Upload your CV and I'll be able to talk about your skills, gaps, "
            "and which of the open roles fit you."
        )

    if ctx.intent == "skills":
        skills = ", ".join(p.technical_skills[:8]) or "no technical skills detected"
        reply = (
            f"Your CV shows {skills}. "
            f"That's {len(p.technical_skills)} technical skills across "
            f"{len(p.experience)} experience entries."
        )
        # Which skills are actually evidenced is the more useful number: a
        # reviewer discounts a list, but not a described project.
        demonstrated = [
            e.skill
            for e in (p.skill_evidence or [])
            if e.source in ("experience", "projects", "certifications")
        ]
        if demonstrated:
            reply += (
                f" {len(demonstrated)} of them are backed by work you "
                f"described, including {', '.join(demonstrated[:3])} — those "
                "are the ones worth leading with."
            )
        elif p.skill_evidence:
            reply += (
                " All of them appear only in a list, though. Skills described "
                "inside a role or project carry far more weight."
            )
        return reply

    if ctx.intent in ("jobs", "general") and ctx.jobs:
        listed = "; ".join(
            f"{job.title}" + (f" at {job.company}" if job.company else "")
            for job, _ in ctx.jobs[:3]
        )
        return (
            f"Based on your CV, the closest open roles are: {listed}. "
            f"Open the Jobs page to see the full match breakdown for each."
        )

    if ctx.intent == "gaps":
        have = {s.lower() for s in p.technical_skills}
        missing = [
            (name, count)
            for name, count in sorted(
                ctx.skill_demand.items(), key=lambda kv: kv[1], reverse=True
            )
            if name.lower() not in have
        ][:3]
        if missing:
            listed = ", ".join(
                f"{_display_skill(name)} ({count} role{'s' if count > 1 else ''})"
                for name, count in missing
            )
            reply = f"The most requested skills you're missing are {listed}."
            # Name where to start. A gap without a next step is just bad news.
            first = _display_skill(missing[0][0])
            reply += (
                f" Start with {first}: build one small thing with it and put "
                "it in your experience section, which counts for more than "
                "adding it to a skills list."
            )
            return reply
        return "You already cover the skills the current open roles ask for."

    if ctx.intent == "salary":
        paid = [
            j for j, _ in ctx.jobs if j.salary_min or j.salary_max
        ]
        if not paid:
            return (
                "None of the roles matching your question publish a salary, so "
                "I can't give you a figure. I only quote pay that's actually "
                "listed on a posting."
            )
        low = min(j.salary_min for j in paid if j.salary_min) if any(j.salary_min for j in paid) else None
        high = max(j.salary_max for j in paid if j.salary_max) if any(j.salary_max for j in paid) else None
        return (
            f"Across {len(paid)} matching role(s) that publish pay, the range is "
            f"${low:,} to ${high:,}." if low and high else
            f"{len(paid)} matching role(s) publish partial salary information."
        )

    if ctx.intent == "experience":
        if p.experience:
            return (
                f"Your CV shows {len(p.experience)} experience entries, starting with: "
                f"{p.experience[0]}."
            )
        return (
            "I couldn't detect a work experience section in your CV. Adding one "
            "with dated roles and measurable achievements would improve your matches."
        )

    if ctx.intent == "cv":
        return (
            f"Your CV has {len(p.technical_skills)} skills, "
            f"{len(p.experience)} experience entries, {len(p.education)} education "
            f"entries, {len(p.projects)} projects and {len(p.certifications)} "
            f"certifications detected."
        )

    return (
        "I can help with your skills, the gaps between your CV and open roles, "
        "which jobs fit you, and what's in your CV. What would you like to know?"
    )


# --- orchestration -------------------------------------------------------


def answer(
    db,
    message: str,
    cv: CV | None,
    profile: CandidateProfile | None,
) -> dict:
    """Answer a question, grounded in retrieved CareerLens data."""
    ctx = build_context(db, message, cv, profile)
    context_text = render_context(ctx)

    response = _generate_with_llm(message, context_text)
    grounded_by_model = response is not None
    if response is None:
        response = _generate_deterministic(message, ctx)

    # Documentation for the gaps just discussed. Taken from the curated map
    # only -- no network call, because a chat reply must stay instant.
    links: list[dict] = []
    if ctx.intent in ("gaps", "skills") and ctx.skill_demand and profile is not None:
        from ai_job_intelligence.services.learning_resources import OFFICIAL_DOCS

        have = {s.lower() for s in profile.technical_skills}
        for name, _count in sorted(
            ctx.skill_demand.items(), key=lambda kv: kv[1], reverse=True
        ):
            if name.lower() in have:
                continue
            entry = OFFICIAL_DOCS.get(name.lower())
            if entry:
                links.append(
                    {
                        "skill": _display_skill(name),
                        "title": entry[0],
                        "url": entry[1],
                    }
                )
            if len(links) == 3:
                break

    return {
        "response": response,
        "intent": ctx.intent,
        "sources": [s.to_dict() for s in ctx.sources],
        "generated_by": "model" if grounded_by_model else "rules",
        "links": links,
    }
