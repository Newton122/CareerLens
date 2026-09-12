from __future__ import annotations

import re
from functools import lru_cache

from ai_job_intelligence.schemas import (
    CandidateProfile,
    JobRequirements,
    SkillEvidence,
)
from ai_job_intelligence.services.cv_sections import split_sections
from ai_job_intelligence.services import skill_evidence

# Bump whenever the extraction logic below changes in a way that would produce
# a different CandidateProfile for the same CV text. Profiles cached on CV rows
# record the version that produced them and are rebuilt when it no longer
# matches, so a logic change cannot leave stale profiles behind.
PROFILE_VERSION = 4

_TECH_VOCAB = [
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust",
    "php", "ruby", "swift", "kotlin", "scala", "r", "matlab", "groovy",
    "fastapi", "django", "flask", "spring", "node.js", "express", "laravel",
    "rails", "nestjs", "aiohttp", "tornado", "bottle",
    "react", "vue", "angular", "svelte", "next.js", "nuxt", "ember",
    "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "dynamodb",
    "cassandra", "sqlite", "oracle", "sql server", "firestore", "memcached",
    "aws", "azure", "gcp", "google cloud", "docker", "kubernetes", "terraform",
    "jenkins", "gitlab", "github", "circleci", "travis", "heroku", "firebase",
    "git", "graphql", "sql", "linux", "windows", "macos", "unix",
    "apache", "nginx", "rabbitmq", "kafka", "grpc", "soap", "microservices",
    "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy", "spark",
    "hadoop", "hive", "presto", "airflow", "dbt", "openai", "gemini",
    "html", "css", "json", "xml", "yaml", "docker compose",
    "machine learning", "deep learning", "nlp", "computer vision",
    "data engineering", "etl", "ci/cd", "devops",
    "agile", "scrum", "kanban", "jira", "figma", "photoshop", "illustrator",
    "apache spark", "amazon web services", "google cloud platform",
    "continuous integration", "continuous deployment",

    # --- Added after CVs were found naming skills the vocabulary did not
    # know. Anything absent here is invisible no matter how plainly it is
    # written, so breadth matters more than precision: a false positive costs
    # one wrong chip, a false negative costs the candidate a match.
    "perl", "haskell", "elixir", "erlang", "clojure", "lua", "dart", "julia",
    "objective-c", "visual basic", "vba", "assembly", "fortran", "cobol",
    "solidity", "zig",

    "solidjs", "remix", "astro", "gatsby", "backbone", "jquery",
    "htmx", "alpine.js", "lit", "qwik",
    "tailwind", "tailwind css", "bootstrap", "material ui", "chakra ui",
    "sass", "scss", "less", "styled-components",
    "redux", "zustand", "mobx", "react query", "tanstack",

    "spring boot", "quarkus", "micronaut", "symfony", "codeigniter",
    "asp.net", ".net", "dotnet", "blazor", "phoenix", "gin", "echo", "fiber",
    "koa", "hapi", "adonis", "strapi", "sanity", "contentful",

    "snowflake", "databricks", "bigquery", "redshift", "clickhouse",
    "cockroachdb", "mariadb", "neo4j", "influxdb", "timescaledb",
    "couchdb", "supabase", "planetscale", "prisma", "sqlalchemy",
    "hibernate", "typeorm", "sequelize", "drizzle", "mongoose",

    "ansible", "puppet", "chef", "vagrant", "packer", "helm", "argocd",
    "flux", "istio", "linkerd", "consul", "vault", "nomad", "openshift",
    "cloudformation", "pulumi", "serverless", "lambda", "ecs", "eks", "s3",
    "cloudflare", "vercel", "netlify", "digitalocean", "linode", "render",
    "fly.io", "railway",

    "prometheus", "grafana", "datadog", "new relic", "sentry", "splunk",
    "elk", "logstash", "kibana", "opentelemetry", "jaeger", "pagerduty",
    "observability", "sre", "site reliability",

    "pytest", "jest", "vitest", "mocha", "chai", "cypress", "playwright",
    "selenium", "junit", "testng", "rspec", "phpunit", "cucumber",
    "unit testing", "integration testing", "test automation", "tdd", "bdd",

    "rest", "rest api", "restful", "websocket", "webhooks", "oauth",
    "jwt", "saml", "openid", "protobuf", "trpc", "openapi", "swagger",

    "celery", "sidekiq", "bullmq", "sqs", "sns", "pubsub", "nats", "activemq",
    "flink", "beam", "dagster", "prefect", "luigi", "nifi",

    "keras", "xgboost", "lightgbm", "huggingface", "transformers", "langchain",
    "llamaindex", "opencv", "spacy", "nltk", "matplotlib", "seaborn", "plotly",
    "streamlit", "jupyter", "anaconda", "mlflow", "kubeflow", "sagemaker",
    "llm", "rag", "prompt engineering", "fine-tuning", "vector database",
    "pinecone", "weaviate", "qdrant", "chroma", "faiss",
    "data science", "data visualization", "statistics", "a/b testing",
    "time series", "reinforcement learning", "generative ai",

    "react native", "flutter", "ionic", "xamarin", "swiftui", "jetpack compose",
    "android", "ios", "expo",

    "bash", "shell scripting", "powershell", "zsh", "make", "cmake",
    "webpack", "vite", "rollup", "esbuild", "babel", "turbopack", "parcel",
    "npm", "yarn", "pnpm", "poetry", "pipenv", "maven", "gradle", "cargo",

    "bitbucket", "azure devops", "teamcity", "bamboo", "argo", "spinnaker",
    "github actions", "gitlab ci",

    "sketch", "adobe xd", "invision", "framer", "webflow",
    "wireframing", "prototyping", "design systems", "accessibility", "wcag",
    "responsive design", "user research", "usability testing",

    "penetration testing", "threat modeling", "owasp", "siem", "iso 27001",
    "soc 2", "gdpr", "cryptography", "network security", "incident response",

    "power bi", "tableau", "looker", "qlik", "dax", "sap", "salesforce",
    "workday", "servicenow", "sharepoint", "dynamics",
]

_SOFT_SKILLS = [
    "communication", "leadership", "teamwork", "problem solving",
    "critical thinking", "project management", "agile", "scrum",
    "collaboration", "time management", "analytical", "adaptability",
    "creativity", "negotiation", "presentation", "mentoring",
]

_GENERAL_SKILLS = [
    "social media marketing", "content creation", "seo", "sem", "google analytics",
    "email marketing", "copywriting", "brand management", "public relations",
    "event planning", "market research", "sales", "customer service",
    "crm", "salesforce", "hubspot", "mailchimp", "canva",
    "video editing", "graphic design", "ux research", "product management",
    "business analysis", "financial modeling", "accounting", "bookkeeping",
    "quickbooks", "excel", "powerpoint", "word", "google workspace",
    "notion", "asana", "trello", "monday.com", "slack", "zoom",
    "data analysis", "data analytics",
]

_FRAMEWORK_MAP = {
    "react": "React", "vue": "Vue", "angular": "Angular", "django": "Django",
    "fastapi": "FastAPI", "flask": "Flask", "spring": "Spring",
    "kubernetes": "Kubernetes", "docker": "Docker", "redis": "Redis",
    "mongodb": "MongoDB", "postgresql": "PostgreSQL", "aws": "AWS",
    "azure": "Azure", "gcp": "GCP", "terraform": "Terraform",
    "ansible": "Ansible", "jenkins": "Jenkins", "gitlab": "GitLab",
    "github": "GitHub", "node.js": "Node.js", "express": "Express",
    "nestjs": "Nestjs", "typescript": "TypeScript", "python": "Python",
    "go": "Go", "rust": "Rust", "java": "Java", "c++": "C++",
    "c#": "C#", "php": "PHP", "ruby": "Ruby", "scala": "Scala",
    "apache": "Apache", "nginx": "Nginx", "kafka": "Kafka",
    "rabbitmq": "RabbitMQ", "elasticsearch": "ElasticSearch",
    "spark": "Spark", "hadoop": "Hadoop", "sql": "SQL",

    # Acronyms and product names that .title() renders wrongly -- "Ecs",
    # "Rest", "Graphql". The displayed spelling is what a recruiter scans for,
    # so it is worth being exact about.
    "ecs": "ECS", "eks": "EKS", "s3": "S3", "sqs": "SQS", "sns": "SNS",
    "rest": "REST", "rest api": "REST", "restful": "REST",
    "graphql": "GraphQL", "grpc": "gRPC", "api": "API",
    "ci/cd": "CI/CD", "html": "HTML", "css": "CSS", "json": "JSON",
    "xml": "XML", "yaml": "YAML", "jwt": "JWT", "oauth": "OAuth",
    "saml": "SAML", "openid": "OpenID", "openapi": "OpenAPI",
    "nlp": "NLP", "llm": "LLM", "rag": "RAG", "etl": "ETL",
    "sre": "SRE", "tdd": "TDD", "bdd": "BDD", "vba": "VBA",
    "dax": "DAX", "sap": "SAP", "elk": "ELK", "siem": "SIEM",
    "owasp": "OWASP", "gdpr": "GDPR", "wcag": "WCAG",
    "soc 2": "SOC 2", "iso 27001": "ISO 27001", "a/b testing": "A/B Testing",
    ".net": ".NET", "dotnet": ".NET", "asp.net": "ASP.NET",
    "nodejs": "Node.js", "next.js": "Next.js", "nuxt": "Nuxt",
    "vue": "Vue", "svelte": "Svelte", "solidjs": "SolidJS",
    "jquery": "jQuery", "htmx": "htmx", "sass": "Sass", "scss": "SCSS",
    "tailwind": "Tailwind CSS", "tailwind css": "Tailwind CSS",
    "material ui": "Material UI", "chakra ui": "Chakra UI",
    "spring boot": "Spring Boot", "argocd": "ArgoCD", "opentelemetry": "OpenTelemetry",
    "mysql": "MySQL", "mariadb": "MariaDB", "sqlite": "SQLite",
    "dynamodb": "DynamoDB", "cockroachdb": "CockroachDB", "couchdb": "CouchDB",
    "influxdb": "InfluxDB", "timescaledb": "TimescaleDB", "bigquery": "BigQuery",
    "clickhouse": "ClickHouse", "planetscale": "PlanetScale",
    "sqlalchemy": "SQLAlchemy", "typeorm": "TypeORM", "pytest": "pytest",
    "junit": "JUnit", "testng": "TestNG", "rspec": "RSpec", "phpunit": "PHPUnit",
    "xgboost": "XGBoost", "lightgbm": "LightGBM", "huggingface": "Hugging Face",
    "llamaindex": "LlamaIndex", "langchain": "LangChain", "opencv": "OpenCV",
    "spacy": "spaCy", "nltk": "NLTK", "matplotlib": "Matplotlib",
    "mlflow": "MLflow", "kubeflow": "Kubeflow", "sagemaker": "SageMaker",
    "react native": "React Native", "swiftui": "SwiftUI", "ios": "iOS",
    "npm": "npm", "pnpm": "pnpm", "esbuild": "esbuild", "vite": "Vite",
    "github actions": "GitHub Actions", "gitlab ci": "GitLab CI",
    "azure devops": "Azure DevOps", "power bi": "Power BI",
    "adobe xd": "Adobe XD", "invision": "InVision", "fly.io": "Fly.io",
    "digitalocean": "DigitalOcean", "new relic": "New Relic",
    "objective-c": "Objective-C", "visual basic": "Visual Basic",

    "social media marketing": "Social Media Marketing",
    "content creation": "Content Creation",
    "seo": "SEO",
    "sem": "SEM",
    "google analytics": "Google Analytics",
    "email marketing": "Email Marketing",
    "copywriting": "Copywriting",
    "brand management": "Brand Management",
    "public relations": "Public Relations",
    "event planning": "Event Planning",
    "market research": "Market Research",
    "sales": "Sales",
    "customer service": "Customer Service",
    "crm": "CRM",
    "salesforce": "Salesforce",
    "hubspot": "HubSpot",
    "mailchimp": "Mailchimp",
    "canva": "Canva",
    "video editing": "Video Editing",
    "graphic design": "Graphic Design",
    "ux research": "UX Research",
    "product management": "Product Management",
    "business analysis": "Business Analysis",
    "financial modeling": "Financial Modeling",
    "accounting": "Accounting",
    "bookkeeping": "Bookkeeping",
    "quickbooks": "QuickBooks",
    "excel": "Excel",
    "powerpoint": "PowerPoint",
    "word": "Word",
    "google workspace": "Google Workspace",
    "notion": "Notion",
    "asana": "Asana",
    "trello": "Trello",
    "monday.com": "Monday.com",
    "slack": "Slack",
    "zoom": "Zoom",
}


# Skill names that are also ordinary English words. Matching these on a bare
# word occurrence produces false positives ("ready to go the extra mile" ->
# Go; "always learning" -> Machine Learning), which inflates every match score.
# They are only accepted with a disambiguating signal: a known alias, or an
# appearance as a discrete item in a delimited skills list.
_AMBIGUOUS_SKILLS = {
    "go", "r", "c", "d", "rust", "swift", "scala", "spark", "word", "excel",
    "sales", "agile", "kanban", "canva", "notion", "asana", "trello", "slack",
    "zoom", "express", "spring",
}

_SKILL_ALIASES = {
    "go": ("golang", "go programming", "go language", "go lang"),
    "r": ("r programming", "r language", "rstudio", "r studio"),
    "c": ("c programming", "c language"),
    "d": ("d programming", "d language"),
    "rust": ("rust programming", "rust language", "rustlang"),
    "swift": ("swiftui", "swift programming", "ios"),
    "scala": ("scala programming",),
    "spark": ("apache spark", "pyspark"),
    "word": ("microsoft word", "ms word"),
    "excel": ("microsoft excel", "ms excel"),
    "express": ("express.js", "expressjs"),
    "spring": ("spring boot", "spring framework"),
}


def _is_listed_item(skill: str, text: str) -> bool:
    """True if ``skill`` appears as a discrete item in a delimited list.

    CVs enumerate skills as "Python, Go, Kubernetes" or "- Go". Requiring that
    shape keeps the ordinary-English use of the same word from counting.
    """
    pattern = (
        r"(?:^|[\n\r]|[,;|/•·]|\u2022|\t)\s*"
        + re.escape(skill)
        + r"\s*(?=$|[\n\r]|[,;|/•·]|\u2022|\t|\(|\-)"
    )
    return re.search(pattern, text, re.IGNORECASE | re.MULTILINE) is not None


def _ambiguous_skill_present(skill: str, text_lower: str, original: str) -> bool:
    """Decide whether an ambiguous skill name is really a skill mention."""
    for alias in _SKILL_ALIASES.get(skill, ()):
        if alias in text_lower:
            return True
    return _is_listed_item(skill, original)


def _extract_skills(text: str) -> tuple[list[str], list[str]]:
    text_lower = text.lower()
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9\+\#\.\-]*", text)

    technical = []
    seen = set()

    multi_word_skills = [s for s in _TECH_VOCAB if " " in s]
    multi_word_skills.sort(key=len, reverse=True)
    blocked = set()
    for skill in multi_word_skills:
        if skill in text_lower and skill not in seen:
            mapped = _FRAMEWORK_MAP.get(skill, skill.title())
            technical.append(mapped)
            seen.add(skill)
            for part in skill.split():
                blocked.add(part)

    for word in words:
        w = word.lower().rstrip(".,:;!?)\"\'")
        if w not in _TECH_VOCAB or w in seen or w in blocked:
            continue
        if w in _AMBIGUOUS_SKILLS and not _ambiguous_skill_present(w, text_lower, text):
            continue
        technical.append(_FRAMEWORK_MAP.get(w, w.capitalize()))
        seen.add(w)

    capitalized = re.findall(r"\b[A-Z][a-zA-Z0-9\.\-]{2,}\b", text)
    for word in capitalized:
        if word in _FRAMEWORK_MAP and word not in technical:
            technical.append(word)

    soft = []
    for skill in _SOFT_SKILLS:
        if skill in text_lower and skill not in soft:
            soft.append(skill.capitalize())

    general = []
    for skill in _GENERAL_SKILLS:
        if skill not in text_lower or skill in general:
            continue
        if skill in _AMBIGUOUS_SKILLS and not _ambiguous_skill_present(skill, text_lower, text):
            continue
        general.append(_FRAMEWORK_MAP.get(skill, skill.title()))

    combined = technical + general

    # No cap. This used to be `combined[:12]`, which silently discarded five
    # of a seventeen-skill CV -- and discarded whichever happened to be
    # scanned last rather than the weakest. Callers that need a short list
    # should take the first N of the evidence-ranked order instead.
    return combined, soft


def _extract_experience(text: str) -> list[str]:
    """Lines describing what the candidate has done.

    Delegates the heading detection to cv_sections: the previous version only
    recognised a line *starting* with "experience", so "PROFESSIONAL
    EXPERIENCE", "Work Experience" and "Employment History" all yielded an
    empty list, taking the experience score and every skill named only in a
    job description down with them.
    """
    sections = split_sections(text)
    experience = []
    for line in sections.get("experience", []):
        cleaned = line.strip().lstrip("-•*–— ").strip()
        # Very short lines are dates or column headers, not descriptions.
        if len(cleaned) < 10 or cleaned in experience:
            continue
        experience.append(cleaned)
    return experience[:20]


def _section_lines(text: str, section: str, *, min_len: int, limit: int) -> list[str]:
    """Cleaned, de-duplicated lines under one CV section.

    Uses the same heading detection as experience (cv_sections), so
    "Academic Background", "Licenses & Certifications" or "Selected Projects"
    are found too. The previous per-section scanners only recognised a line
    that *started* with the exact word, and silently returned nothing for
    every other heading.
    """
    lines: list[str] = []
    for line in split_sections(text).get(section, []):
        cleaned = line.strip().lstrip("-•*–— ").strip()
        if len(cleaned) < min_len or cleaned.endswith(":") or cleaned in lines:
            continue
        lines.append(cleaned)
    return lines[:limit]


def _lines_mentioning(text: str, pattern: str, *, limit: int) -> list[str]:
    """Real lines of the CV that match ``pattern``.

    The fallback when a CV has no heading for a section. It used to insert
    text the CV never contained -- "Bachelor's degree in Computer Science or
    related field" for anyone who wrote the word "degree" -- which then
    counted as the candidate's education. Quoting the CV's own line is
    honest, and still gives the matcher something to compare.
    """
    found: list[str] = []
    for line in text.split("\n"):
        cleaned = line.strip().lstrip("-•*–— ").strip()
        if 5 <= len(cleaned) <= 200 and re.search(pattern, cleaned, re.IGNORECASE):
            if cleaned not in found:
                found.append(cleaned)
    return found[:limit]


_DEGREE_WORDS = (
    r"\b(bachelor|master|ph\.?d|doctorate|b\.?sc|m\.?sc|b\.?a\b|m\.?a\b|"
    r"b\.?eng|m\.?eng|mba|diploma|degree|university|college)"
)
_CERT_WORDS = r"\b(certified|certification|certificate)\b"
_YEARS_WORDS = r"\b\d+\+?\s*(years?|yrs?)\b"


def _extract_education(text: str) -> list[str]:
    return _section_lines(text, "education", min_len=5, limit=5)


def _extract_certifications(text: str) -> list[str]:
    return _section_lines(text, "certifications", min_len=5, limit=5)


def _extract_projects(text: str) -> list[str]:
    return _section_lines(text, "projects", min_len=10, limit=10)


def _local_analyze_job_description(job_description: str) -> JobRequirements:
    technical, soft = _extract_skills(job_description)

    years_match = re.search(r"(\d+)\s*(?:\+|years|year)", job_description.lower())
    required_experience = f"{years_match.group(1)} years" if years_match else ""

    education_requirements = ""
    jd_lower = job_description.lower()
    if any(x in jd_lower for x in ["degree", "bachelor", "master", "phd", "computer science", "engineering", "certification"]):
        if "master" in jd_lower or "phd" in jd_lower:
            education_requirements = "Advanced degree (Master's or PhD)"
        else:
            education_requirements = "Bachelor's degree in Computer Science or related field"

    certifications = []
    if "aws" in jd_lower and ("certified" in jd_lower or "certificate" in jd_lower):
        certifications.append("AWS Certification")
    if "kubernetes" in jd_lower and ("certified" in jd_lower or "ckad" in jd_lower or "cka" in jd_lower):
        certifications.append("Kubernetes Certification")

    keywords = [w.upper() for w in technical[:10]]

    return JobRequirements(
        technical_skills=technical,
        soft_skills=soft,
        required_experience=required_experience,
        education_requirements=education_requirements,
        certifications=certifications,
        keywords=keywords,
    )


def _gemini_analyze_job_description(job_description: str) -> JobRequirements | None:
    from ai_job_intelligence.config import GOOGLE_API_KEY

    # No key, no call. Creating a client without one fails half-way and the
    # library then logs an AttributeError while cleaning up after itself.
    if not GOOGLE_API_KEY:
        return None
    try:
        from google import genai  # type: ignore
        from google.genai import types  # type: ignore

        client = genai.Client(api_key=GOOGLE_API_KEY)

        prompt = f"""
You are a job-requirements extraction system.

Analyze the following job description.

Extract:
- technical skills
- soft skills
- required experience
- education requirements
- certifications
- important keywords

Only extract information supported by the job description.
Do not invent requirements.

Job description:
---
{job_description}
---
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=JobRequirements,
            ),
        )

        if response.parsed is not None:
            return response.parsed
    except Exception:
        pass
    return None


@lru_cache(maxsize=512)
def _cached_gemini_analyze(job_description: str) -> JobRequirements | None:
    """Memoised Gemini extraction.

    Job descriptions are immutable text, so the same description never needs to
    be sent to the model twice. Without this, listing endpoints re-extract the
    same postings on every page load.
    """
    return _gemini_analyze_job_description(job_description)


def analyze_job_description(
    job_description: str,
    *,
    use_llm: bool = True,
) -> JobRequirements:
    """Extract structured requirements from a job description.

    ``use_llm=False`` skips Gemini entirely and uses the deterministic
    extractor. Bulk endpoints that score many jobs at once should pass False:
    one LLM round-trip per job does not survive a 50-job list, and the local
    extractor is good enough for ranking. Reserve the LLM path for single-job,
    user-initiated deep analysis.
    """
    if use_llm:
        result = _cached_gemini_analyze(job_description)
        if result is not None:
            return result
    return _local_analyze_job_description(job_description)


@lru_cache(maxsize=512)
def analyze_cv_text(cv_text: str) -> CandidateProfile:
    """Extract a structured candidate profile from raw CV text.

    Pure and deterministic (no LLM), so it is memoised: the same CV is
    re-analysed by many endpoints on every request otherwise.
    """
    technical, soft = _extract_skills(cv_text)

    # Where each skill actually appeared. Ranked strongest-evidence-first, so
    # a skill demonstrated in a project outranks one merely listed -- and a
    # caller that truncates the list drops the weakest rather than whatever
    # was scanned last.
    hits = skill_evidence.collect_evidence(
        cv_text,
        vocabulary=list(_TECH_VOCAB) + list(_GENERAL_SKILLS),
        canonical=_FRAMEWORK_MAP,
        ambiguous=_AMBIGUOUS_SKILLS,
        ambiguity_test=_ambiguous_skill_present,
    )
    ranked = skill_evidence.rank_skills(hits)
    if ranked:
        # Anything the evidence pass found but the flat scan missed is still
        # a real skill; anything only the flat scan found is kept behind it.
        # Compared case-insensitively, because the two passes canonicalise
        # differently and would otherwise show "REST" and "Rest Api" as two
        # separate skills.
        merged: list[str] = []
        seen_lower: set[str] = set()
        for name in ranked + technical:
            key = name.lower().replace(" ", "")
            if key in seen_lower:
                continue
            seen_lower.add(key)
            merged.append(name)
        technical = merged

    best = skill_evidence.best_hit_per_skill(hits)
    evidence = [
        SkillEvidence(skill=h.skill, source=h.source, context=h.context)
        for h in best.values()
    ]

    experience = _extract_experience(cv_text)
    education = _extract_education(cv_text)
    certifications = _extract_certifications(cv_text)
    projects = _extract_projects(cv_text)

    req = _local_analyze_job_description(cv_text)

    # A CV without a heading for a section still gets something to match on,
    # but only its own words: the lines that mention a degree, a
    # certification, or a number of years.
    if not education:
        education = _lines_mentioning(cv_text, _DEGREE_WORDS, limit=3)
    if not experience:
        experience = _lines_mentioning(cv_text, _YEARS_WORDS, limit=3)
    if not certifications:
        certifications = _lines_mentioning(cv_text, _CERT_WORDS, limit=3)

    return CandidateProfile(
        technical_skills=technical,
        soft_skills=soft,
        experience=experience,
        education=education,
        certifications=certifications,
        projects=projects,
        keywords=req.keywords,
        skill_evidence=evidence,
    )


def ocr_image(file_path: str) -> str:
    """Extract text from an image using Gemini Vision API."""
    from ai_job_intelligence.config import GOOGLE_API_KEY

    if not GOOGLE_API_KEY:
        return ""
    try:
        from pathlib import Path
        from google import genai  # type: ignore
        from google.genai import types  # type: ignore

        path = Path(file_path)
        with open(path, "rb") as f:
            img_data = f.read()

        mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/png", ".bmp": "image/png", ".tiff": "image/png", ".tif": "image/png"}
        mime_type = mime_map.get(path.suffix.lower(), "image/jpeg")

        client = genai.Client(api_key=GOOGLE_API_KEY)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                "Extract all text from this CV/resume image. Return only the extracted text content, preserving the structure as much as possible. Do not add any explanations or commentary.",
                types.Part.from_bytes(data=img_data, mime_type=mime_type),
            ],
        )
        return (response.text or "").strip()
    except Exception:
        pass
    return ""
