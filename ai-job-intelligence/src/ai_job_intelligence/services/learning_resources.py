"""Find real places to learn a skill the candidate is missing.

Telling someone they lack Kubernetes is not advice. This module turns each
skill gap into things they can actually open: official documentation, a
well-regarded repository, a recent article, a community thread.

**On scraping.** Three of the four sources are public JSON APIs rather than
HTML scrapes. That is deliberate: an HTML scrape of a site like dev.to breaks
the first time they rename a CSS class, and it breaks silently -- the request
still returns 200 and you get an empty list. A documented JSON endpoint has a
stable contract, is far cheaper to parse, and is what these sites publish for
exactly this purpose. The fourth source is a curated map of official docs,
because no API can tell you that the canonical place to learn React is
react.dev.

Everything here degrades rather than fails. A source that times out, rate
limits, or changes shape contributes nothing and is logged; the caller still
gets whatever the other sources returned. A skills panel must never be the
reason an analysis page will not load.
"""
from __future__ import annotations

import logging
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from typing import Callable

import httpx

logger = logging.getLogger(__name__)

# Short: this runs inside a request. A slow source is worth dropping rather
# than making the whole panel wait for it.
REQUEST_TIMEOUT_SECONDS = 6.0

# Results change on the order of days, not seconds, and these are shared
# public endpoints -- caching is both faster for us and politer to them.
CACHE_TTL_SECONDS = 60 * 60 * 6  # 6 hours

MAX_PER_SOURCE = 3
MAX_TOTAL = 8

USER_AGENT = "CareerLens/0.1 (learning-resource lookup)"


@dataclass
class Resource:
    """One thing a person can open and learn from."""

    title: str
    url: str
    source: str
    # "docs" | "course" | "repo" | "article" | "discussion"
    kind: str
    description: str = ""
    # Free-form signal of quality: stars, reactions, points.
    signal: str = ""


@dataclass
class SkillResources:
    skill: str
    resources: list[Resource] = field(default_factory=list)
    # True when every network source failed, so the UI can say so honestly
    # instead of implying nothing exists for this skill.
    degraded: bool = False


# --- Curated official documentation ---------------------------------------
# No API knows that the canonical home of Django is docs.djangoproject.com.
# Keys are matched case-insensitively against the skill name.
OFFICIAL_DOCS: dict[str, tuple[str, str]] = {
    "python": ("Python documentation", "https://docs.python.org/3/"),
    "javascript": ("MDN JavaScript guide", "https://developer.mozilla.org/en-US/docs/Web/JavaScript"),
    "typescript": ("TypeScript handbook", "https://www.typescriptlang.org/docs/"),
    "react": ("React documentation", "https://react.dev/learn"),
    "next.js": ("Next.js documentation", "https://nextjs.org/docs"),
    "nextjs": ("Next.js documentation", "https://nextjs.org/docs"),
    "vue": ("Vue documentation", "https://vuejs.org/guide/introduction.html"),
    "angular": ("Angular documentation", "https://angular.dev/overview"),
    "node.js": ("Node.js learning path", "https://nodejs.org/en/learn"),
    "nodejs": ("Node.js learning path", "https://nodejs.org/en/learn"),
    "django": ("Django documentation", "https://docs.djangoproject.com/en/stable/"),
    "flask": ("Flask documentation", "https://flask.palletsprojects.com/"),
    "fastapi": ("FastAPI documentation", "https://fastapi.tiangolo.com/"),
    "postgresql": ("PostgreSQL documentation", "https://www.postgresql.org/docs/current/"),
    "postgres": ("PostgreSQL documentation", "https://www.postgresql.org/docs/current/"),
    "mysql": ("MySQL documentation", "https://dev.mysql.com/doc/"),
    "mongodb": ("MongoDB manual", "https://www.mongodb.com/docs/manual/"),
    "redis": ("Redis documentation", "https://redis.io/docs/latest/"),
    "sql": ("SQL tutorial (Mode)", "https://mode.com/sql-tutorial/"),
    "docker": ("Docker documentation", "https://docs.docker.com/get-started/"),
    "kubernetes": ("Kubernetes basics", "https://kubernetes.io/docs/tutorials/kubernetes-basics/"),
    "terraform": ("Terraform tutorials", "https://developer.hashicorp.com/terraform/tutorials"),
    "ansible": ("Ansible documentation", "https://docs.ansible.com/"),
    "aws": ("AWS Skill Builder", "https://skillbuilder.aws/"),
    "azure": ("Microsoft Learn: Azure", "https://learn.microsoft.com/en-us/training/azure/"),
    "gcp": ("Google Cloud Skills Boost", "https://www.cloudskillsboost.google/"),
    "google cloud": ("Google Cloud Skills Boost", "https://www.cloudskillsboost.google/"),
    "git": ("Pro Git (free book)", "https://git-scm.com/book/en/v2"),
    "linux": ("Linux Journey", "https://linuxjourney.com/"),
    "go": ("A Tour of Go", "https://go.dev/tour/"),
    "golang": ("A Tour of Go", "https://go.dev/tour/"),
    "rust": ("The Rust Book", "https://doc.rust-lang.org/book/"),
    "java": ("Java tutorials", "https://dev.java/learn/"),
    "c#": ("C# documentation", "https://learn.microsoft.com/en-us/dotnet/csharp/"),
    "csharp": ("C# documentation", "https://learn.microsoft.com/en-us/dotnet/csharp/"),
    "php": ("PHP manual", "https://www.php.net/manual/en/"),
    "ruby": ("Ruby documentation", "https://www.ruby-lang.org/en/documentation/"),
    "kotlin": ("Kotlin documentation", "https://kotlinlang.org/docs/home.html"),
    "swift": ("Swift documentation", "https://www.swift.org/documentation/"),
    "html": ("MDN HTML guide", "https://developer.mozilla.org/en-US/docs/Web/HTML"),
    "css": ("MDN CSS guide", "https://developer.mozilla.org/en-US/docs/Web/CSS"),
    "tailwind": ("Tailwind CSS documentation", "https://tailwindcss.com/docs"),
    "graphql": ("GraphQL learn", "https://graphql.org/learn/"),
    "pandas": ("pandas user guide", "https://pandas.pydata.org/docs/user_guide/"),
    "numpy": ("NumPy absolute beginners", "https://numpy.org/doc/stable/user/absolute_beginners.html"),
    "pytorch": ("PyTorch tutorials", "https://pytorch.org/tutorials/"),
    "tensorflow": ("TensorFlow tutorials", "https://www.tensorflow.org/tutorials"),
    "scikit-learn": ("scikit-learn user guide", "https://scikit-learn.org/stable/user_guide.html"),
    "machine learning": ("Google ML Crash Course", "https://developers.google.com/machine-learning/crash-course"),
    "excel": ("Excel training", "https://support.microsoft.com/en-us/office/excel-video-training-9bc05390-e94c-46af-a5b3-d7c22f6990bb"),
    "power bi": ("Microsoft Learn: Power BI", "https://learn.microsoft.com/en-us/training/powerplatform/power-bi"),
    "figma": ("Figma learn", "https://help.figma.com/hc/en-us/categories/360002051613"),
}

# Skill names the content APIs know under a different tag.
TAG_ALIASES = {
    "c#": "csharp",
    "c++": "cpp",
    "node.js": "node",
    "nodejs": "node",
    "next.js": "nextjs",
    "scikit-learn": "scikitlearn",
    "google cloud": "gcp",
    "machine learning": "machinelearning",
    "power bi": "powerbi",
}


def _tag_for(skill: str) -> str:
    """A content-API tag for a skill name.

    Tags are lowercase and alphanumeric on every source used here, so
    punctuation and spaces are stripped rather than escaped.
    """
    key = skill.strip().lower()
    key = TAG_ALIASES.get(key, key)
    return re.sub(r"[^a-z0-9]", "", key)


# --- Cache ----------------------------------------------------------------
# Process-local and bounded by the number of distinct skills asked about,
# which is small. A shared cache (Redis) would be the next step if this ever
# runs on more than one worker; the interface here would not change.
_cache: dict[str, tuple[float, list[Resource]]] = {}
_cache_lock = threading.Lock()


def _cached(key: str) -> list[Resource] | None:
    with _cache_lock:
        hit = _cache.get(key)
        if hit and time.time() - hit[0] < CACHE_TTL_SECONDS:
            return hit[1]
        if hit:
            del _cache[key]
    return None


def _store(key: str, value: list[Resource]) -> None:
    with _cache_lock:
        _cache[key] = (time.time(), value)


def clear_cache() -> None:
    """Drop everything cached. Used by tests."""
    with _cache_lock:
        _cache.clear()


# --- Sources --------------------------------------------------------------


def _fetch_json(client: httpx.Client, url: str, params: dict) -> object | None:
    try:
        r = client.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        if r.status_code != 200:
            logger.info("Resource source %s returned %s", url, r.status_code)
            return None
        return r.json()
    except Exception as exc:
        # Includes timeouts, DNS failures, and malformed JSON. Every one of
        # them means "this source contributed nothing", never "fail the page".
        logger.info("Resource source %s unavailable: %s", url, exc)
        return None


# Words that distinguish "teach me this" from "opinion piece that mentions
# this". Tag search alone returns whatever is popular this week, which for a
# panel headed "Where to learn this" is close to useless.
_TEACHING_WORDS = (
    "tutorial", "guide", "how to", "how i", "introduction", "intro to",
    "getting started", "beginner", "learn", "explained", "basics",
    "step by step", "walkthrough", "crash course", "from scratch",
    "cheat sheet", "deep dive", "understanding", "fundamentals", "101",
)


def _teaching_rank(title: str, description: str) -> int:
    """Lower sorts first. 0 means the text promises to teach something."""
    haystack = f"{title} {description}".lower()
    return 0 if any(w in haystack for w in _TEACHING_WORDS) else 1


def _from_devto(client: httpx.Client, skill: str) -> list[Resource]:
    """Community write-ups, ranked so tutorials beat commentary.

    A wider page is requested than is returned: the ranking below needs
    candidates to choose from, and the tag feed alone is ordered by
    popularity, which surfaces opinion pieces that merely mention the skill.
    """
    data = _fetch_json(
        client,
        "https://dev.to/api/articles",
        {"tag": _tag_for(skill), "per_page": 30, "top": "365"},
    )
    if not isinstance(data, list):
        return []

    candidates = []
    for a in data:
        if not isinstance(a, dict) or not a.get("url"):
            continue
        title = str(a.get("title", "")).strip()
        description = str(a.get("description", "") or "").strip()
        if not title:
            continue
        reactions = a.get("positive_reactions_count") or 0
        candidates.append(
            (
                _teaching_rank(title, description),
                -reactions,
                Resource(
                    title=title[:180],
                    url=str(a["url"]),
                    source="DEV",
                    kind="article",
                    description=description[:200],
                    signal=f"{reactions} reactions" if reactions else "",
                ),
            )
        )

    # Teaching content first, then by reactions within each band.
    candidates.sort(key=lambda c: (c[0], c[1]))
    return [c[2] for c in candidates[:MAX_PER_SOURCE]]


def _from_github(client: httpx.Client, skill: str) -> list[Resource]:
    """Highly-starred repositories for the topic.

    Sorted by stars because the question is "what should I learn from", and
    on GitHub stars are the cheapest available proxy for that.
    """
    data = _fetch_json(
        client,
        "https://api.github.com/search/repositories",
        {
            "q": f"topic:{_tag_for(skill)}",
            "sort": "stars",
            "order": "desc",
            "per_page": MAX_PER_SOURCE,
        },
    )
    if not isinstance(data, dict):
        return []

    out = []
    for repo in (data.get("items") or [])[:MAX_PER_SOURCE]:
        if not isinstance(repo, dict) or not repo.get("html_url"):
            continue
        stars = repo.get("stargazers_count") or 0
        out.append(
            Resource(
                title=str(repo.get("full_name", "")).strip()[:180],
                url=str(repo["html_url"]),
                source="GitHub",
                kind="repo",
                description=str(repo.get("description", "") or "").strip()[:200],
                signal=f"{stars:,} stars" if stars else "",
            )
        )
    return out


def _from_hackernews(client: httpx.Client, skill: str) -> list[Resource]:
    """Threads where people argue about how to learn this.

    Often more useful than a tutorial: the comments say which resources are
    actually worth the time.
    """
    data = _fetch_json(
        client,
        "https://hn.algolia.com/api/v1/search",
        {
            "query": f"learn {skill}",
            "tags": "story",
            "hitsPerPage": MAX_PER_SOURCE,
        },
    )
    if not isinstance(data, dict):
        return []

    out = []
    for hit in (data.get("hits") or [])[:MAX_PER_SOURCE]:
        if not isinstance(hit, dict):
            continue
        title = str(hit.get("title") or "").strip()
        object_id = hit.get("objectID")
        if not title or not object_id:
            continue
        points = hit.get("points") or 0
        # Link the discussion, not the story: the comments are the value.
        out.append(
            Resource(
                title=title[:180],
                url=f"https://news.ycombinator.com/item?id={object_id}",
                source="Hacker News",
                kind="discussion",
                description="",
                signal=f"{points} points" if points else "",
            )
        )
    return out


def _official_doc(skill: str) -> list[Resource]:
    entry = OFFICIAL_DOCS.get(skill.strip().lower())
    if not entry:
        return []
    title, url = entry
    return [
        Resource(
            title=title,
            url=url,
            source="Official",
            kind="docs",
            description="The maintainers' own guide — start here.",
            signal="",
        )
    ]


NETWORK_SOURCES: list[Callable[[httpx.Client, str], list[Resource]]] = [
    _from_github,
    _from_devto,
    _from_hackernews,
]


def resources_for_skill(skill: str) -> SkillResources:
    """Everything worth opening in order to learn ``skill``.

    Official documentation leads when it exists, because it is the one source
    that is always correct and never stale.
    """
    skill = (skill or "").strip()
    if not skill:
        return SkillResources(skill="", resources=[])

    cache_key = skill.lower()
    hit = _cached(cache_key)
    if hit is not None:
        return SkillResources(skill=skill, resources=hit)

    collected = _official_doc(skill)
    failures = 0

    # Fetched in parallel: three sequential six-second timeouts would be a
    # visible stall on a page that is otherwise instant. The guard matters
    # because ThreadPoolExecutor rejects max_workers=0, so a build with every
    # source disabled would raise here rather than fall back to the curated
    # documentation.
    sources = list(NETWORK_SOURCES)
    if sources:
        with httpx.Client(headers={"User-Agent": USER_AGENT}) as client:
            with ThreadPoolExecutor(max_workers=len(sources)) as pool:
                futures = {pool.submit(fn, client, skill): fn for fn in sources}
                for fut in as_completed(futures):
                    try:
                        found = fut.result()
                    except Exception as exc:
                        logger.info("Resource source raised: %s", exc)
                        found = []
                    if not found:
                        failures += 1
                    collected.extend(found)

    # Same URL from two sources is one resource.
    seen: set[str] = set()
    deduped: list[Resource] = []
    for r in collected:
        if r.url in seen:
            continue
        seen.add(r.url)
        deduped.append(r)

    # Docs first, then something to read, then something to build from.
    order = {"docs": 0, "course": 1, "article": 2, "repo": 3, "discussion": 4}
    deduped.sort(key=lambda r: order.get(r.kind, 9))
    deduped = deduped[:MAX_TOTAL]

    # "Degraded" means the network sources were tried and all failed. With no
    # sources configured nothing failed, so the curated result is complete.
    degraded = bool(sources) and failures == len(sources)
    # A fully degraded lookup is not cached: the next request should retry
    # rather than serve an empty panel for six hours.
    if not degraded:
        _store(cache_key, deduped)

    return SkillResources(skill=skill, resources=deduped, degraded=degraded)


def resources_for_skills(skills: list[str], limit: int = 4) -> list[dict]:
    """Resources for several skills, in the order given.

    ``limit`` caps how many skills are looked up. Someone missing fifteen
    skills does not need fifteen panels, and each one costs network calls.
    """
    out = []
    for skill in [s for s in skills if s and s.strip()][:limit]:
        found = resources_for_skill(skill)
        out.append(
            {
                "skill": found.skill,
                "degraded": found.degraded,
                "resources": [asdict(r) for r in found.resources],
            }
        )
    return out
