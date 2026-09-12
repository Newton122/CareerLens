from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4

import json
import logging
import time

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi import status
from sqlalchemy import and_, inspect, or_, text

from ai_job_intelligence.config import (
    CORS_ORIGINS,
    IMAGES_DIR,
    IS_PRODUCTION,
    UPLOAD_DIR,
)
from ai_job_intelligence.schemas import (
    CandidateProfile,
    CVAnalysisRequest, CVAnalysisResponse,
    JobCreate, JobRead, JobUpdate,
    ApplicationCreate, ApplicationRead,
    SavedJobCreate, SavedJobRead,
    RegisterRequest, LoginRequest, AuthResponse,
    UserStats, CareerInsights, CVAnalysisDetail,
    ProfileRead, ProfileUpdate,
    InterviewCreate, InterviewRead, InterviewStatusUpdate,
    InterviewDetailsUpdate,
    MessageCreate, MessageRead, ConversationRead,
)
from ai_job_intelligence.services.pdf_parser import (
    TextExtractionError,
    extract_text_from_file,
)
from ai_job_intelligence.services.matcher import analyze_match
from ai_job_intelligence.services.database import SessionLocal, engine, Base
from ai_job_intelligence.services.ai_service import (analyze_job_description, analyze_cv_text, ocr_image)
from ai_job_intelligence.services.cv_profile import (
    get_candidate_profile,
    get_profiles_for_cvs,
    store_profile,
)
from ai_job_intelligence.services import assistant, learning_resources, semantic_index
from ai_job_intelligence.services.guidance import build_guidance
from ai_job_intelligence.models.cv import CV
from ai_job_intelligence.models.analysis import Analysis
from ai_job_intelligence.models.user import User
from ai_job_intelligence.models.user_profile import UserProfile
from ai_job_intelligence.models.job import Job
from ai_job_intelligence.models.application import Application
from ai_job_intelligence.models.saved_job import SavedJob
from ai_job_intelligence.models.interview import Interview
from ai_job_intelligence.models.message import Message
from ai_job_intelligence.services.auth import (create_access_token,
                                               hash_password,
                                               verify_password,
                                               verify_password_constant_time)
from ai_job_intelligence.services.password_policy import (
    PasswordPolicyError,
    validate_password,
)
from ai_job_intelligence.services.rate_limit import Rule, SlidingWindowLimiter

from ai_job_intelligence.services.auth_dependency import get_current_user_id

logger = logging.getLogger(__name__)

app = FastAPI(title="AI Job Intelligence API", version="0.1.0")

# Allow the frontend (Next.js dev server) to call the API during development.
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _add_missing_columns(table: str, columns: list[tuple[str, str]]) -> None:
    """Add any of ``columns`` that ``table`` does not already have.

    Two things this has to get right on PostgreSQL:

    * The live schema is inspected and a plain ADD COLUMN is issued only for
      what is missing, so each startup reports exactly what it changed.
    * A failed statement aborts the whole transaction, so every later statement
      on that connection fails as well. Each column therefore gets its own
      transaction: a permission error on one table cannot cascade into a failed
      startup.
    """
    with engine.connect() as conn:
        inspector = inspect(conn)
        if table not in inspector.get_table_names():
            return
        existing = {c["name"] for c in inspector.get_columns(table)}

    for name, col_type in columns:
        if name in existing:
            continue
        try:
            with engine.begin() as conn:
                conn.execute(
                    text(f'ALTER TABLE {table} ADD COLUMN "{name}" {col_type}')
                )
            logger.info("Added column %s.%s", table, name)
        except Exception as exc:
            logger.error("Could not add column %s.%s: %s", table, name, exc)


@app.on_event("startup")
def startup_event() -> None:
    Base.metadata.create_all(bind=engine)

    _add_missing_columns(
        "user_profiles",
        [
            ("description", "TEXT"),
            ("industry", "VARCHAR"),
            ("company_size", "VARCHAR"),
            ("website", "VARCHAR"),
            ("linkedin", "VARCHAR"),
            ("twitter", "VARCHAR"),
            ("image_url", "VARCHAR"),
        ],
    )
    # Cache of the parsed CandidateProfile -- see services/cv_profile.py.
    # embedding/embedding_version -- see services/vector_store.py.
    _add_missing_columns(
        "cvs",
        [
            ("profile_json", "TEXT"),
            ("profile_version", "INTEGER"),
            ("profile_parsed_at", "TIMESTAMP"),
            ("embedding", "TEXT"),
            ("embedding_version", "INTEGER"),
        ],
    )
    _add_missing_columns(
        "jobs",
        [
            ("embedding", "TEXT"),
            ("embedding_version", "INTEGER"),
        ],
    )
    # How a candidate actually attends. Added after the table shipped with
    # only a free-text location, which left video calls with nowhere to put a
    # link. Defaults are set inline so existing rows read as a video call of
    # the standard length rather than as nulls the UI has to special-case.
    _add_missing_columns(
        "interviews",
        [
            ("mode", "VARCHAR(20) DEFAULT 'video' NOT NULL"),
            ("meeting_url", "TEXT"),
            ("dial_in", "VARCHAR(64)"),
            ("contact_email", "VARCHAR(255)"),
            ("contact_phone", "VARCHAR(64)"),
            ("duration_minutes", "INTEGER DEFAULT 45 NOT NULL"),
            ("timezone", "VARCHAR(64)"),
        ],
    )

    # experience_match/education_match became nullable: null now means "the
    # posting did not state this", which is different from a score of zero.
    for column in ("experience_match", "education_match"):
        try:
            with engine.begin() as conn:
                conn.execute(
                    text(f"ALTER TABLE analyses ALTER COLUMN {column} DROP NOT NULL")
                )
        except Exception as exc:
            # Already nullable, or the table was just built by create_all from
            # the current model; either way there is nothing to relax.
            logger.debug("Could not relax analyses.%s: %s", column, exc)

    # Note: name/role/company live on user_profiles, not users. Earlier code
    # also tried to add them to the users table; nothing reads them there, and
    # the app's DB role does not own that table, so the attempt only produced
    # errors. Dropped deliberately.
    try:
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE user_profiles SET role = 'job_seeker' WHERE role IS NULL")
            )
    except Exception as exc:
        logger.error("Could not backfill null user_profiles.role: %s", exc)



# --- Upload handling -------------------------------------------------------

ALLOWED_CV_EXTENSIONS = {".pdf", ".txt", ".png", ".jpg", ".jpeg"}

# Applies to CV uploads. A CV is a few hundred KB; anything far larger is a
# mistake or an attempt to fill the disk.
MAX_CV_UPLOAD_BYTES = 5 * 1024 * 1024

# The demo endpoint is unauthenticated, so it is capped harder and rate limited.
MAX_DEMO_UPLOAD_BYTES = 2 * 1024 * 1024
# Tight in production, roomier locally: while developing you test from a single
# IP and would otherwise lock yourself out after five attempts.
DEMO_RATE_LIMIT = 5 if IS_PRODUCTION else 30
DEMO_RATE_WINDOW_SECONDS = 3600
MIN_JOB_DESCRIPTION_CHARS = 30

# --- Rate limiters ---------------------------------------------------------
#
# All in-process; see services/rate_limit for what that does and does not buy.
#
# Login is limited on two independent keys. Per-IP stops one machine grinding
# through a password list. Per-account stops a distributed attempt against a
# single high-value account, where each source IP stays under its own limit.

_demo_limiter = SlidingWindowLimiter(
    Rule(limit=DEMO_RATE_LIMIT, window_seconds=DEMO_RATE_WINDOW_SECONDS)
)
# Per-IP limits are relaxed outside production. Locally -- and in end-to-end
# tests -- every request originates from 127.0.0.1, so a production-tight
# per-IP limit locks the developer out of their own app after a handful of
# actions. The per-account limit is NOT relaxed: it is keyed by email, so it
# never collides between users, and it is the one that actually stops an
# attacker grinding a single account.
_LOGIN_IP_LIMIT = 10 if IS_PRODUCTION else 200
_REGISTER_IP_LIMIT = 5 if IS_PRODUCTION else 200

_login_ip_limiter = SlidingWindowLimiter(
    Rule(limit=_LOGIN_IP_LIMIT, window_seconds=300)
)
_login_account_limiter = SlidingWindowLimiter(Rule(limit=5, window_seconds=900))
_register_limiter = SlidingWindowLimiter(
    Rule(limit=_REGISTER_IP_LIMIT, window_seconds=3600)
)


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _enforce(limiter: SlidingWindowLimiter, key: str, message: str) -> None:
    retry_after = limiter.check(key)
    if retry_after is not None:
        raise HTTPException(
            status_code=429,
            detail=message,
            headers={"Retry-After": str(int(retry_after))},
        )


def _check_demo_rate_limit(request: Request) -> None:
    key = _client_ip(request)
    _enforce(
        _demo_limiter,
        key,
        f"The free demo is limited to {DEMO_RATE_LIMIT} analyses per hour. "
        "Create a free account for unlimited analyses.",
    )
    _demo_limiter.record(key)


def _validated_extension(filename: str | None) -> str:
    if not filename:
        raise HTTPException(status_code=400, detail="No file selected")
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_CV_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only PDF, TXT, PNG, JPG, JPEG files are allowed",
        )
    return ext


async def _save_upload(
    file: UploadFile,
    *,
    max_bytes: int,
    prefix: str = "",
) -> tuple[Path, str]:
    """Persist an upload safely and return (path on disk, original filename).

    The stored name is always generated, never taken from the client. Using the
    supplied filename directly allowed a path like "../../evil.txt" to escape
    the upload directory and overwrite files elsewhere in the project.
    """
    ext = _validated_extension(file.filename)

    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large (maximum {max_bytes // (1024 * 1024)}MB)",
        )
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    stored_path = UPLOAD_DIR / f"{prefix}{uuid4().hex}{ext}"
    stored_path.write_bytes(content)

    return stored_path, Path(file.filename).name


def _extract_or_400(file_path: Path) -> str:
    """Extract text, converting parser failures into actionable 400s."""
    try:
        extracted = extract_text_from_file(file_path)
    except TextExtractionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not extracted.strip():
        ext = file_path.suffix.lower()
        if ext in (".png", ".jpg", ".jpeg"):
            detail = (
                "No text could be read from this image. Try a sharper photo, "
                "or upload a PDF or TXT file instead."
            )
        elif ext == ".pdf":
            detail = (
                "No text could be read from this PDF. It may be a scan or "
                "image-only document. Try a text-based PDF or a TXT file."
            )
        else:
            detail = "No text could be read from this file."
        raise HTTPException(status_code=400, detail=detail)

    return extracted


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "AI Job Intelligence API is running"}


@app.post("/api/analyze", response_model=CVAnalysisResponse)
def analyze_cv(
    payload: CVAnalysisRequest,
    current_user_id: int = Depends(get_current_user_id),
) -> CVAnalysisResponse:
    db = SessionLocal()

    try:
        cv = db.get(CV, payload.cv_id)

        if cv is None or cv.user_id != current_user_id:
            raise HTTPException(
                status_code=404,
                detail="CV not found",
            )

        # Understand the candidate
        candidate = get_candidate_profile(db, cv)

        # Understand the job
        requirements = analyze_job_description(
            payload.job_description
        )

        # Compare candidate against job
        result = analyze_match(
            candidate=candidate,
            requirements=requirements,
        )
        analysis = Analysis(
            cv_id=cv.id,
            job_title=payload.job_title,
            company=payload.company,
            job_description=payload.job_description,
            match_score=result["match_score"],
            matched_skills=json.dumps(result["matched_skills"]),
            missing_skills=json.dumps(result["missing_skills"]),
            experience_match=result["experience_match"],
            education_match=result["education_match"],
            recommendations=json.dumps(result["recommendations"]),
            summary=result["summary"],
        )

        db.add(analysis)
        db.commit()
        db.refresh(analysis)

        return {
            "analysis_id": analysis.id,
            "match_score": result["match_score"],
            "matched_skills": result["matched_skills"],
            "missing_skills": result["missing_skills"],
            "experience_match": result["experience_match"],
            "education_match": result["education_match"],
            "recommendations": result["recommendations"],
            "summary": result["summary"],
        }

    finally:
        db.close()


@app.post("/api/demo/analyze")
async def demo_analyze(
    request: Request,
    file: UploadFile = File(...),
    job_title: str = Form(...),
    job_description: str = Form(...),
) -> dict:
    """Run one analysis without an account.

    Unauthenticated, so it is rate limited per IP, capped tighter than the
    signed-in upload, and always deletes the uploaded file -- including when
    the analysis fails.
    """
    _check_demo_rate_limit(request)

    if len(job_description.strip()) < MIN_JOB_DESCRIPTION_CHARS:
        raise HTTPException(
            status_code=400,
            detail=(
                "Please paste a fuller job description (at least "
                f"{MIN_JOB_DESCRIPTION_CHARS} characters). Short descriptions "
                "produce meaningless match scores."
            ),
        )

    file_path, original_name = await _save_upload(
        file, max_bytes=MAX_DEMO_UPLOAD_BYTES, prefix="demo_"
    )

    try:
        extracted = _extract_or_400(file_path)

        candidate = analyze_cv_text(extracted)
        requirements = analyze_job_description(job_description)
        result = analyze_match(candidate=candidate, requirements=requirements)

        required_count = len(requirements.technical_skills)
        matched_count = len(result["matched_skills"])
        skills_match = (
            round((matched_count / required_count) * 100) if required_count else None
        )

        # Say what the score was built from, matching the rest of the app.
        sources = [
            f"Skills read from your CV: {len(candidate.technical_skills)} detected.",
            (
                f"Requirements read from the job description: "
                f"{required_count} technical skill(s)."
            ),
        ]
        if result["experience_match"] is None:
            sources.append(
                "The posting states no experience requirement, so experience "
                "was not scored."
            )
        if result["education_match"] is None:
            sources.append(
                "The posting states no education requirement, so education "
                "was not scored."
            )

        return {
            "job_title": job_title,
            "filename": original_name,
            "match_score": result["match_score"],
            "matched_skills": result["matched_skills"],
            "missing_skills": result["missing_skills"],
            "skills_match": skills_match,
            "experience_match": result["experience_match"],
            "education_match": result["education_match"],
            "recommendations": result["recommendations"],
            "summary": result["summary"],
            "detected_skills": candidate.technical_skills,
            "sources": sources,
        }
    finally:
        # Always clean up. Previously this ran only after a successful
        # analysis, so every failed upload was left on disk permanently.
        file_path.unlink(missing_ok=True)


@app.post(
    "/api/auth/register",
    response_model=AuthResponse,
)
def register(payload: RegisterRequest, request: Request) -> AuthResponse:
    ip = _client_ip(request)
    _enforce(
        _register_limiter,
        ip,
        "Too many accounts created from this network. Please try again later.",
    )

    try:
        validate_password(payload.password, email=payload.email)
    except PasswordPolicyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    db = SessionLocal()

    try:
        existing_user = (
            db.query(User)
            .filter(User.email == payload.email)
            .first()
        )

        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Email already registered",
            )

        _register_limiter.record(ip)

        user = User(
            email=payload.email,
            password_hash=hash_password(payload.password),
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        profile = UserProfile(
            user_id=user.id,
            name=payload.name,
            role=payload.role,
        )
        db.add(profile)
        db.commit()

        token = create_access_token(user.id)

        return AuthResponse(
            access_token=token,
            token_type="bearer",
            user_id=user.id,
            email=user.email,
            role=payload.role,
        )

    finally:
        db.close()
        

@app.post(
    "/api/auth/login",
    response_model=AuthResponse,
)
def login(payload: LoginRequest, request: Request) -> AuthResponse:
    ip = _client_ip(request)
    account_key = payload.email

    _enforce(
        _login_ip_limiter,
        ip,
        "Too many sign-in attempts from this network. Please wait and try again.",
    )
    _enforce(
        _login_account_limiter,
        account_key,
        "Too many sign-in attempts for this account. Please wait and try again.",
    )

    db = SessionLocal()

    try:
        user = (
            db.query(User)
            .filter(User.email == payload.email)
            .first()
        )

        # Always run a hash comparison, even when no such account exists.
        # Skipping it returned in ~2ms instead of ~330ms, which let anyone
        # enumerate registered email addresses by timing alone.
        password_ok = verify_password_constant_time(
            payload.password,
            user.password_hash if user else None,
        )

        if not user or not password_ok:
            _login_ip_limiter.record(ip)
            _login_account_limiter.record(account_key)
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password",
            )

        # A successful sign-in clears that account's failure history so a user
        # who mistypes a few times is not locked out after getting it right.
        _login_account_limiter.reset(account_key)

        token = create_access_token(user.id)

        role = _get_user_role(db, user.id)

        return AuthResponse(
            access_token=token,
            token_type="bearer",
            user_id=user.id,
            email=user.email,
            role=role,
        )

    finally:
        db.close()


@app.get("/api/profile", response_model=ProfileRead)
def get_profile(current_user_id: int = Depends(get_current_user_id)) -> ProfileRead:
    db = SessionLocal()
    try:
        user = db.get(User, current_user_id)
        profile = _get_user_profile(db, current_user_id)
        role = _get_user_role(db, current_user_id)

        return ProfileRead(
            name=(profile.name or "") if profile else "",
            email=user.email if user else "",
            role=role,
            company=(profile.company or "") if profile else "",
            description=(profile.description or "") if profile else "",
            industry=(profile.industry or "") if profile else "",
            company_size=(profile.company_size or "") if profile else "",
            website=(profile.website or "") if profile else "",
            linkedin=(profile.linkedin or "") if profile else "",
            twitter=(profile.twitter or "") if profile else "",
            image_url=(profile.image_url or "") if profile else "",
        )
    finally:
        db.close()


@app.put("/api/profile", response_model=ProfileRead)
def update_profile(
    payload: ProfileUpdate,
    current_user_id: int = Depends(get_current_user_id),
) -> ProfileRead:
    db = SessionLocal()
    try:
        user = db.get(User, current_user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        profile = _get_user_profile(db, current_user_id)
        if profile is None:
            profile = UserProfile(
                user_id=current_user_id,
                role="job_seeker",
            )
            db.add(profile)
            db.flush()

        if payload.name is not None:
            profile.name = payload.name
        if payload.company is not None:
            profile.company = payload.company
        if payload.description is not None:
            profile.description = payload.description
        if payload.industry is not None:
            profile.industry = payload.industry
        if payload.company_size is not None:
            profile.company_size = payload.company_size
        if payload.website is not None:
            profile.website = payload.website
        if payload.linkedin is not None:
            profile.linkedin = payload.linkedin
        if payload.twitter is not None:
            profile.twitter = payload.twitter

        if payload.image_url is not None:
            profile.image_url = payload.image_url

        db.commit()

        role = _get_user_role(db, current_user_id)
        return ProfileRead(
            name=profile.name or "",
            email=user.email,
            role=role,
            company=profile.company or "",
            description=profile.description or "",
            industry=profile.industry or "",
            company_size=profile.company_size or "",
            website=profile.website or "",
            linkedin=profile.linkedin or "",
            twitter=profile.twitter or "",
            image_url=profile.image_url or "",
        )
    finally:
        db.close()


@app.get("/api/cvs")
def get_cvs( current_user_id: int = Depends(get_current_user_id),) -> list[dict]:
    db = SessionLocal()

    try:
        cvs = (
            db.query(CV)
            .filter(CV.user_id == current_user_id)
            .order_by(CV.created_at.desc())
            .all()
        )

        return [
            {
                "id": cv.id,
                "filename": cv.filename,
                "created_at": cv.created_at,
            }
            for cv in cvs
        ]

    finally:
        db.close()
        
@app.get("/api/cvs/{cv_id}")
def get_cv(
    cv_id: int,
    current_user_id: int = Depends(get_current_user_id),
) -> dict:
    db = SessionLocal()

    try:
        cv = db.get(CV, cv_id)

        if cv is None or (
            cv.user_id != current_user_id
            and _get_user_role(db, current_user_id) != ADMIN_ROLE
        ):
            raise HTTPException(
                status_code=404,
                detail="CV not found",
            )

        return {
            "id": cv.id,
            "filename": cv.filename,
            "file_path": cv.file_path,
            "extracted_text": cv.extracted_text,
            "created_at": cv.created_at,
        }

    finally:
        db.close()                
        
        
@app.get("/api/cvs/{cv_id}/analysis", response_model=CVAnalysisDetail)
def get_cv_analysis(
    cv_id: int,
    current_user_id: int = Depends(get_current_user_id),
) -> dict:
    db = SessionLocal()
    try:
        cv = db.get(CV, cv_id)
        if cv is None or cv.user_id != current_user_id:
            raise HTTPException(
                status_code=404,
                detail="CV not found",
            )

        profile = get_candidate_profile(db, cv)

        # No cap. This mirrored the one in the extractor and had the same
        # effect: a CV listing more than twelve skills lost the rest with no
        # indication. The list is already ordered strongest-evidence-first.
        all_skills = profile.technical_skills + profile.soft_skills

        skills_list = [
            {
                "name": skill,
                "proficiency": "advanced" if i < len(all_skills) // 3 else (
                    "intermediate" if i < len(all_skills) * 2 // 3 else "beginner"
                ),
            }
            for i, skill in enumerate(all_skills)
        ]

        strengths = all_skills[:5]

        weaknesses = []
        if len(profile.experience) < 2:
            weaknesses.append("Add more detailed work experience with metrics and achievements.")
        if not profile.certifications:
            weaknesses.append("Earn relevant certifications to validate your skills.")
        if len(profile.projects) < 2:
            weaknesses.append("Add more projects to demonstrate practical application of your skills.")
        if not weaknesses:
            weaknesses = ["No major gaps identified"]

        experience_assessment = f"Identified {len(profile.experience)} experience entries."
        if profile.experience:
            experience_assessment += f" Experience includes: {', '.join(profile.experience[:3])}."
        if len(profile.experience) < 2:
            experience_assessment += " Consider adding more detailed work experience with metrics and achievements."

        education_assessment = "No education details extracted."
        if profile.education:
            education_assessment = f"Education background includes: {', '.join(profile.education[:3])}."
        if profile.education and profile.technical_skills:
            education_assessment += " The academic background supports the technical skill set."

        # Recommendations grounded in what open roles actually ask for, so the
        # advice names real skills and real counts rather than generic filler.
        open_jobs = db.query(Job).filter(Job.status == "open").all()
        demand: dict[str, int] = {}
        display: dict[str, str] = {}
        for job in open_jobs:
            for skill in _parse_json_list(job.required_skills):
                key = skill.strip().lower()
                if key:
                    demand[key] = demand.get(key, 0) + 1
                    display.setdefault(key, skill.strip())

        have = {s.lower() for s in profile.technical_skills + profile.soft_skills}
        top_missing = [
            (display[k], c)
            for k, c in sorted(demand.items(), key=lambda kv: kv[1], reverse=True)
            if k not in have
        ][:3]

        analysis_sources: list[str] = []
        recommendations = []

        for name, count in top_missing:
            share = round((count / len(open_jobs)) * 100) if open_jobs else 0
            recommendations.append(
                f"Add {name} to your CV or gain experience with it - "
                f"{count} open role(s) require it ({share}% of postings)."
            )
        if top_missing:
            analysis_sources.append(
                f"Skill recommendations derived from {len(open_jobs)} open job posting(s)."
            )

        if not profile.experience:
            recommendations.append(
                "No work experience section was detected. Add one with dated roles - "
                "without it, experience cannot be scored against any job."
            )
        elif len(profile.experience) < 2:
            recommendations.append(
                f"Only {len(profile.experience)} experience entry was detected. "
                "Add earlier roles with quantifiable achievements."
            )

        if not profile.certifications:
            certs_in_demand = [
                display[k] for k in demand
                if any(t in k for t in ("aws", "azure", "kubernetes", "gcp", "salesforce"))
            ][:2]
            if certs_in_demand:
                recommendations.append(
                    "No certifications detected. Certifications in "
                    f"{' or '.join(certs_in_demand)} appear in current postings."
                )
            else:
                recommendations.append(
                    "No certifications detected. Adding relevant ones helps validate your skills."
                )

        if len(profile.projects) < 2:
            recommendations.append(
                f"Only {len(profile.projects)} project(s) detected. Add 2-3 with the "
                "tech used and the outcome, so skills are evidenced rather than listed."
            )

        if len(profile.technical_skills) < 5:
            recommendations.append(
                f"Only {len(profile.technical_skills)} technical skills were detected. "
                "List them as discrete comma-separated items under a Skills heading - "
                "prose mentions are easily missed by parsers."
            )

        if not recommendations:
            recommendations.append(
                "Your CV covers the skills currently in demand and is well structured. "
                "Focus on tailoring it per application."
            )

        analysis_sources.append(
            "Section detection (experience, education, projects, certifications) "
            "comes from parsing your uploaded CV."
        )

        # Where each skill was actually found. This answers the most common
        # complaint about the analysis -- "that skill IS in my CV" -- by
        # showing the sentence that evidenced it, or by its absence making
        # clear the parser never saw it.
        evidence = [
            {"skill": e.skill, "source": e.source, "context": e.context}
            for e in (profile.skill_evidence or [])
        ]
        demonstrated = sum(
            1
            for e in (profile.skill_evidence or [])
            if e.source in ("experience", "projects", "certifications")
        )
        if evidence:
            analysis_sources.append(
                f"{demonstrated} of {len(evidence)} skills were evidenced by work "
                "you described, rather than only listed."
            )

        formatting_tips = [
            "Use a clean, ATS-friendly layout with standard fonts (Arial, Calibri, Helvetica).",
            "Keep your CV to 1-2 pages maximum for optimal readability.",
            "Use consistent formatting for dates, headings, and bullet points.",
            "Save and send your CV as a PDF to preserve formatting across devices.",
            "Use adequate white space and margins (at least 0.5 inches).",
        ]

        ats_tips = [
            "Include keywords from the job description naturally throughout your CV.",
            "Use standard section headings: Experience, Education, Skills, Projects.",
            "Avoid tables, text boxes, headers/footers, and complex graphics.",
            "Use full job titles and company names (avoid abbreviations).",
            "Quantify achievements with numbers, percentages, and metrics.",
        ]

        action_verbs = [
            "Use action verbs to start each bullet point: Led, Built, Designed, Implemented, Optimized, Delivered.",
            "Focus on achievements, not just responsibilities. What impact did you make?",
            "Tailor your professional summary to each job application.",
        ]

        total_completeness = len(profile.technical_skills) + len(profile.experience) + len(profile.education) + len(profile.certifications)
        overall_score = min(100, len(profile.technical_skills) * 10 + len(profile.experience) * 10 + len(profile.education) * 10 + len(profile.certifications) * 10)

        summary = f"This CV analysis identified {len(profile.technical_skills)} technical skills"
        if profile.experience:
            summary += f", {len(profile.experience)} experience entries"
        if profile.education:
            summary += f", and {len(profile.education)} education items"
        summary += f". Profile completeness score: {overall_score}%. "
        summary += "The candidate's profile was analyzed using AI to extract skills, experience, and education."
        summary += " Recommendations and assessments are generated based on the extracted information."

        return {
            "id": cv.id,
            "cv_name": cv.filename,
            "overall_score": overall_score,
            "summary": summary,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "recommendations": recommendations,
            "skills": skills_list,
            "experience": profile.experience,
            "education": profile.education,
            "projects": profile.projects,
            "certifications": profile.certifications,
            "experience_assessment": experience_assessment,
            "education_assessment": education_assessment,
            "formatting_tips": formatting_tips,
            "ats_tips": ats_tips,
            "action_verbs": action_verbs,
            "analyzed_at": cv.created_at,
            "sources": analysis_sources,
            "skill_evidence": evidence,
            # The gaps most worth closing, taken from what open postings
            # actually ask for rather than a generic list.
            "learn_next": [name for name, _ in top_missing],
        }
    finally:
        db.close()


@app.get("/api/analyses/{analysis_id}")
def get_analysis(
    analysis_id: int,
    current_user_id: int = Depends(get_current_user_id),
) -> dict:
    db = SessionLocal()
    try:
        analysis = db.get(Analysis, analysis_id)
        if analysis is None:
            raise HTTPException(status_code=404, detail="Analysis not found")

        cv = db.get(CV, analysis.cv_id)
        if cv is None or cv.user_id != current_user_id:
            raise HTTPException(status_code=404, detail="Analysis not found")

        matched = json.loads(analysis.matched_skills)
        missing = json.loads(analysis.missing_skills)

        # Only used to tell whether the CV listed any projects, so a failure
        # to parse it must not take the page down with it.
        try:
            profile = get_candidate_profile(db, cv)
        except Exception:
            profile = None

        return {
            "id": analysis.id,
            "cv_id": analysis.cv_id,
            "job_title": analysis.job_title,
            "company": analysis.company,
            "job_description": analysis.job_description,
            "match_score": analysis.match_score,
            "matched_skills": json.loads(analysis.matched_skills),
            "missing_skills": json.loads(analysis.missing_skills),
            "experience_match": analysis.experience_match,
            "education_match": analysis.education_match,
            "recommendations": json.loads(analysis.recommendations),
            # Grouped, prioritised actions derived from the same numbers.
            # `recommendations` is kept alongside it so older clients and the
            # saved analyses list keep working unchanged.
            "guidance": build_guidance(
                matched_skills=matched,
                missing_skills=missing,
                experience_match=analysis.experience_match,
                education_match=analysis.education_match,
                match_score=analysis.match_score,
                has_projects=bool(profile.projects) if profile else False,
                job_title=analysis.job_title or "",
            ),
            "summary": analysis.summary,
            "created_at": analysis.created_at,
        }
    finally:
        db.close()


@app.get("/api/learning-resources")
def get_learning_resources(
    skills: str = Query(..., description="Comma-separated skill names"),
    limit: int = Query(4, ge=1, le=8),
    current_user_id: int = Depends(get_current_user_id),
) -> dict:
    """Places to actually learn the given skills.

    Kept off the analysis response deliberately: this reaches out to third
    party APIs, and an analysis page must render immediately whether or not
    those are up. The client asks for this separately and shows the panel when
    it arrives.
    """
    wanted = [s.strip() for s in skills.split(",") if s.strip()]
    if not wanted:
        raise HTTPException(status_code=400, detail="Name at least one skill")

    return {"skills": learning_resources.resources_for_skills(wanted, limit=limit)}


@app.get("/api/cvs/{cv_id}/analyses")
def get_cv_analyses(
    cv_id: int,
    current_user_id: int = Depends(get_current_user_id),
) -> list[dict]:
    db = SessionLocal()

    try:
        cv = db.get(CV, cv_id)

        if cv is None or cv.user_id != current_user_id:
            raise HTTPException(
                status_code=404,
                detail="CV not found",
            )

        analyses = (
            db.query(Analysis)
            .filter(Analysis.cv_id == cv_id)
            .order_by(Analysis.created_at.desc())
            .all()
        )

        return [
            {
                "id": analysis.id,
                "cv_id": analysis.cv_id,
                "job_title": analysis.job_title,
                "company": analysis.company,
                "job_description": analysis.job_description,
                "match_score": analysis.match_score,
                "matched_skills": json.loads(
                    analysis.matched_skills
                ),
                "missing_skills": json.loads(
                    analysis.missing_skills
                ),
                "experience_match": analysis.experience_match,
                "education_match": analysis.education_match,
                "recommendations": json.loads(
                    analysis.recommendations
                ),
                "summary": analysis.summary,
                "created_at": analysis.created_at,
            }
            for analysis in analyses
        ]

    finally:
        db.close()        
        
        
@app.post("/api/upload-cv")
async def upload_cv(
    file: UploadFile = File(...),
    current_user_id: int = Depends(get_current_user_id),
) -> dict:
    file_path, original_name = await _save_upload(
        file, max_bytes=MAX_CV_UPLOAD_BYTES
    )

    try:
        extracted = _extract_or_400(file_path)
    except HTTPException:
        # Nothing usable was stored, so do not leave the file behind.
        file_path.unlink(missing_ok=True)
        raise

    db = SessionLocal()

    try:
        cv = CV(
            filename=original_name,
            file_path=str(file_path),
            extracted_text=extracted,
            user_id=current_user_id,
        )

        db.add(cv)
        db.commit()
        db.refresh(cv)

        # Parse once, here, and persist alongside the CV. Every other endpoint
        # reads this cached profile instead of re-parsing the document.
        candidate = analyze_cv_text(cv.extracted_text)
        store_profile(cv, candidate)
        semantic_index.set_cv_embedding(cv, candidate)
        db.commit()

        all_skills = candidate.technical_skills + candidate.soft_skills
        if len(all_skills) > 12:
            all_skills = all_skills[:12]

        skills_list = [
            {
                "name": skill,
                "proficiency": "advanced" if i < len(all_skills) // 3 else (
                    "intermediate" if i < len(all_skills) * 2 // 3 else "beginner"
                ),
            }
            for i, skill in enumerate(all_skills)
        ]

        strengths = all_skills[:5]

        weaknesses = []
        if len(candidate.experience) < 2:
            weaknesses.append("Add more detailed work experience with metrics and achievements.")
        if not candidate.certifications:
            weaknesses.append("Earn relevant certifications to validate your skills.")
        if len(candidate.projects) < 2:
            weaknesses.append("Add more projects to demonstrate practical application of your skills.")
        if not weaknesses:
            weaknesses = ["No major gaps identified"]

        recommendations = []
        if len(candidate.experience) < 2:
            recommendations.append("Expand your work experience section with quantifiable achievements.")
        if not candidate.certifications:
            recommendations.append("Earn relevant certifications (AWS, Docker, etc.) to validate your skills.")
        if len(candidate.projects) < 2:
            recommendations.append("Add more projects to demonstrate practical application of your skills.")
        recommendations.append("Tailor your CV for each job application by highlighting relevant skills.")
        recommendations.append("Use action verbs like 'Led', 'Built', 'Designed' to describe your achievements.")
        recommendations.append("Include metrics and numbers to quantify your impact (e.g., 'Increased performance by 30%').")
        recommendations.append("Keep your CV concise and focused on the most relevant experience for your target role.")
        if not recommendations:
            recommendations.append("Your profile is strong. Keep building your career.")

        total_completeness = len(candidate.technical_skills) + len(candidate.experience) + len(candidate.education) + len(candidate.certifications)
        overall_score = min(100, len(candidate.technical_skills) * 10 + len(candidate.experience) * 10 + len(candidate.education) * 10 + len(candidate.certifications) * 10)

        return {
            "cv_id": str(cv.id),
            "filename": cv.filename,
            "status": "uploaded",
            "profile": {
                "overall_score": overall_score,
                "skills": skills_list,
                "experience": candidate.experience,
                "education": candidate.education,
                "projects": candidate.projects,
                "certifications": candidate.certifications,
                "strengths": strengths,
                "weaknesses": weaknesses,
                "recommendations": recommendations,
            }
        }

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to save CV to database",
        )

    finally:
        db.close()


@app.get("/api/cvs/{cv_id}/download")
def download_cv(
    cv_id: int,
    current_user_id: int = Depends(get_current_user_id),
):
    """Download the original CV PDF file."""
    from fastapi.responses import FileResponse

    db = SessionLocal()
    try:
        cv = db.get(CV, cv_id)
        if cv is None:
            raise HTTPException(status_code=404, detail="CV not found")

        role = _get_user_role(db, current_user_id)
        if role != "admin" and cv.user_id != current_user_id:
            raise HTTPException(status_code=404, detail="CV not found")

        file_path = Path(cv.file_path)
        if file_path.exists():
            ext = file_path.suffix.lower()
            media_type = {
                ".pdf": "application/pdf",
                ".txt": "text/plain",
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
            }.get(ext, "application/octet-stream")

            return FileResponse(
                file_path,
                media_type=media_type,
                filename=cv.filename,
            )
        raise HTTPException(status_code=404, detail="File not found on disk")
    finally:
        db.close()


@app.post("/api/upload-image")
async def upload_image(
    file: UploadFile = File(...),
    current_user_id: int = Depends(get_current_user_id),
) -> dict:
    """Upload a profile picture or company logo."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")

    allowed_types = {"image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Only PNG, JPG, JPEG, GIF, WEBP images are allowed",
        )

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    unique_name = f"{current_user_id}_{uuid4().hex}_{file.filename}"
    file_path = IMAGES_DIR / unique_name

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 5MB)")

    file_path.write_bytes(content)

    image_url = f"/api/images/{unique_name}"

    db = SessionLocal()
    try:
        profile = _get_user_profile(db, current_user_id)
        if profile is None:
            profile = UserProfile(
                user_id=current_user_id,
                role="job_seeker",
            )
            db.add(profile)
        profile.image_url = image_url
        db.commit()
    finally:
        db.close()

    return {"image_url": image_url, "filename": file.filename}


@app.get("/api/images/{image_name}")
def get_image(image_name: str):
    """Serve an uploaded image file."""
    from fastapi.responses import FileResponse

    file_path = IMAGES_DIR / image_name
    if file_path.exists():
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="Image not found")


def _parse_json_list(value: str) -> list[str]:
    try:
        result = json.loads(value or "[]")
        if isinstance(result, list):
            return [str(v) for v in result]
        return []
    except (json.JSONDecodeError, TypeError):
        return []


def _json_dumps(items: list[str]) -> str:
    return json.dumps(items)


def _get_user(db, user_id: int) -> User | None:
    return db.get(User, user_id)


def _get_user_profile(db, user_id: int) -> UserProfile | None:
    return db.get(UserProfile, user_id)


def _get_user_role(db, user_id: int) -> str:
    profile = _get_user_profile(db, user_id)
    if profile and profile.role:
        return profile.role
    return "job_seeker"


def _get_user_company(db, user_id: int) -> str:
    profile = _get_user_profile(db, user_id)
    if profile and profile.company:
        return profile.company
    return ""


def _get_user_name(db, user_id: int) -> str:
    profile = _get_user_profile(db, user_id)
    if profile and profile.name:
        return profile.name
    return ""


def _get_user_email(db, user_id: int) -> str | None:
    user = db.get(User, user_id)
    return user.email if user else None


def _get_latest_cv(db, user_id: int) -> CV | None:
    return (
        db.query(CV)
        .filter(CV.user_id == user_id)
        .order_by(CV.created_at.desc())
        .first()
    )


def _job_to_dict(
    job: Job,
    applications_count: int = 0,
    match_score: float | None = None,
    skill_gaps: list[str] | None = None,
    match_breakdown: dict | None = None,
) -> dict:
    return {
        "id": job.id,
        "title": job.title,
        "description": job.description,
        "location": job.location,
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "employment_type": job.employment_type,
        "required_skills": _parse_json_list(job.required_skills),
        "experience_required": job.experience_required,
        "education_required": job.education_required,
        "responsibilities": job.responsibilities,
        "benefits": _parse_json_list(job.benefits),
        "status": job.status,
        "company": job.company,
        "views": job.views,
        "created_at": job.created_at,
        "applications_count": applications_count,
        "match_score": match_score,
        "skill_gaps": skill_gaps,
        "match_breakdown": match_breakdown,
    }


# How many jobs survive semantic retrieval and go on to full match analysis.
# Generous relative to the number returned, so a role the vector stage ranks
# only moderately can still win on detailed skill matching.
RERANK_CANDIDATES = 50

# Cosine floor for free-text candidate search. Unrelated text scores near zero
# (and can go slightly negative), so this mainly removes obvious non-matches
# rather than imposing a strict relevance bar.
SEMANTIC_SEARCH_FLOOR = 0.15

# Minimum cosine similarity for a job title to be recommended as a role the
# candidate should target. Below this the posting is not really their field.
ROLE_MATCH_FLOOR = 0.25

# How many of the closest roles are considered when measuring what the
# candidate's own field demands.
INSIGHT_ROLE_POOL = 15

# How many recommendations are returned to the client.
RECOMMENDATION_LIMIT = 20


# ─── Job routes ─────────────────────────────────────────────────────


@app.get("/api/jobs", response_model=list[JobRead])
def get_jobs(
    current_user_id: int = Depends(get_current_user_id),
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
) -> list[dict]:
    db = SessionLocal()
    try:
        role = _get_user_role(db, current_user_id)
        is_employer = role == "employer"
        is_admin = role == "admin"

        query = db.query(Job)
        if is_employer:
            query = query.filter(Job.employer_id == current_user_id)
        else:
            query = query.filter(Job.status == "open")

        jobs = (
            query.order_by(Job.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        if not is_employer and not is_admin:
            cv = _get_latest_cv(db, current_user_id)
            candidate_profile = (
                get_candidate_profile(db, cv) if cv else None
            )

        result: list[dict] = []
        for job in jobs:
            app_count = db.query(Application).filter(
                Application.job_id == job.id
            ).count()

            match_score: float | None = None
            skill_gaps: list[str] | None = None
            match_breakdown: dict | None = None

            if not is_employer and not is_admin and candidate_profile is not None:
                # Bulk listing: deterministic extraction only (see analyze_job_description).
                requirements = analyze_job_description(job.description, use_llm=False)
                m = analyze_match(
                    candidate=candidate_profile, requirements=requirements
                )
                match_score = float(m["match_score"])
                skill_gaps = m["missing_skills"]
                match_breakdown = {
                    "skills_match": round(
                        (len(m["matched_skills"]) / max(len(requirements.technical_skills), 1)) * 100
                    ) if requirements.technical_skills else 0,
                    "experience_match": m["experience_match"],
                    "education_match": m["education_match"],
                }

            result.append(
                _job_to_dict(
                    job,
                    applications_count=app_count,
                    match_score=match_score,
                    skill_gaps=skill_gaps,
                    match_breakdown=match_breakdown,
                )
            )
        return result
    finally:
        db.close()


@app.post("/api/jobs", response_model=JobRead, status_code=status.HTTP_201_CREATED)
def create_job(
    payload: JobCreate,
    current_user_id: int = Depends(get_current_user_id),
) -> dict:
    db = SessionLocal()
    try:
        company_name = _get_user_company(db, current_user_id)

        job = Job(
            title=payload.title,
            description=payload.description,
            location=payload.location,
            salary_min=payload.salary_min,
            salary_max=payload.salary_max,
            employment_type=payload.employment_type,
            required_skills=_json_dumps(payload.required_skills),
            experience_required=payload.experience_required,
            education_required=payload.education_required,
            responsibilities=payload.responsibilities,
            benefits=_json_dumps(payload.benefits),
            status="open",
            company=company_name,
            employer_id=current_user_id,
            views=0,
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        # Embed the posting so it is searchable without a later backfill pass.
        semantic_index.set_job_embedding(job)
        db.commit()

        return _job_to_dict(job, applications_count=0)
    finally:
        db.close()


@app.patch("/api/jobs/{job_id}", response_model=JobRead)
def update_job(
    job_id: int,
    payload: JobUpdate,
    current_user_id: int = Depends(get_current_user_id),
) -> dict:
    """Edit a posting you own.

    A partial update: only the fields present in the body are written, so the
    edit form can send a subset without blanking the rest.

    Ownership is checked before anything else and a posting belonging to
    someone else answers 404 rather than 403 -- a 403 would confirm the id
    exists, letting anyone enumerate other employers' postings.
    """
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if job is None or job.employer_id != current_user_id:
            raise HTTPException(status_code=404, detail="Job not found")

        # exclude_unset is what makes this a patch rather than a replace:
        # a key the client never sent is absent here, while an explicit null
        # is present and does clear the column.
        changes = payload.model_dump(exclude_unset=True)

        # Guard the range before writing either end, since a client may send
        # only one of the two and still invert the pair.
        new_min = changes.get("salary_min", job.salary_min)
        new_max = changes.get("salary_max", job.salary_max)
        if new_min is not None and new_max is not None and new_min > new_max:
            raise HTTPException(
                status_code=400,
                detail="Minimum salary cannot be greater than maximum salary",
            )

        # These two are stored as JSON text, so they cannot be set directly.
        list_columns = {"required_skills", "benefits"}

        for field, value in changes.items():
            if field in list_columns:
                setattr(job, field, _json_dumps(value or []))
            else:
                setattr(job, field, value)

        # The embedding is derived from title + skills + description, so it
        # goes stale the moment any of those change. Recomputing here keeps
        # semantic search honest instead of matching against the old text.
        if {"title", "description", "required_skills"} & set(changes):
            semantic_index.set_job_embedding(job)

        db.commit()
        db.refresh(job)

        applications_count = (
            db.query(Application).filter(Application.job_id == job.id).count()
        )
        return _job_to_dict(job, applications_count=applications_count)
    finally:
        db.close()


@app.get("/api/jobs/{job_id}", response_model=JobRead)
def get_job(
    job_id: int,
    current_user_id: int = Depends(get_current_user_id),
) -> dict:
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if job is None:
            raise HTTPException(
                status_code=404,
                detail="Job not found",
            )

        is_employer = _get_user_role(db, current_user_id) == "employer"
        job.views = (job.views or 0) + 1
        db.commit()

        app_count = db.query(Application).filter(
            Application.job_id == job.id
        ).count()

        match_score: float | None = None
        skill_gaps: list[str] | None = None
        match_breakdown: dict | None = None

        if not is_employer:
            cv = _get_latest_cv(db, current_user_id)
            if cv:
                candidate_profile = get_candidate_profile(db, cv)
                requirements = analyze_job_description(job.description)
                m = analyze_match(
                    candidate=candidate_profile, requirements=requirements
                )
                match_score = float(m["match_score"])
                skill_gaps = m["missing_skills"]
                match_breakdown = {
                    "skills_match": round(
                        (len(m["matched_skills"]) / max(len(requirements.technical_skills), 1)) * 100
                    ) if requirements.technical_skills else 0,
                    "experience_match": m["experience_match"],
                    "education_match": m["education_match"],
                }

        return _job_to_dict(
            job,
            applications_count=app_count,
            match_score=match_score,
            skill_gaps=skill_gaps,
            match_breakdown=match_breakdown,
        )
    finally:
        db.close()


@app.get("/api/jobs/{job_id}/applications", response_model=list[ApplicationRead])
def get_job_applications(
    job_id: int,
    current_user_id: int = Depends(get_current_user_id),
) -> list[dict]:
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if job is None:
            raise HTTPException(
                status_code=404,
                detail="Job not found",
            )

        if job.employer_id != current_user_id:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to view these applications",
            )

        applications = (
            db.query(Application)
            .filter(Application.job_id == job_id)
            .order_by(Application.applied_at.desc())
            .all()
        )

        return [
            {
                "id": app.id,
                "job_id": app.job_id,
                "job_title": job.title,
                "company": job.company,
                "candidate_name": _get_user_name(db, app.user_id),
                "candidate_email": _get_user_email(db, app.user_id),
                "status": app.status,
                "match_score": app.match_score,
                "applied_at": app.applied_at,
            }
            for app in applications
        ]
    finally:
        db.close()


# ─── Application routes ─────────────────────────────────────────────


@app.get("/api/applications", response_model=list[ApplicationRead])
def get_applications(
    current_user_id: int = Depends(get_current_user_id),
) -> list[dict]:
    db = SessionLocal()
    try:
        applications = (
            db.query(Application)
            .filter(Application.user_id == current_user_id)
            .order_by(Application.applied_at.desc())
            .all()
        )

        result: list[dict] = []
        for app in applications:
            job = db.get(Job, app.job_id)
            result.append(
                {
                    "id": app.id,
                    "job_id": app.job_id,
                    "job_title": job.title if job else "Unknown",
                    "company": job.company if job else "",
                    "candidate_name": "",
                    "candidate_email": "",
                    "status": app.status,
                    "match_score": app.match_score,
                    "applied_at": app.applied_at,
                }
            )
        return result
    finally:
        db.close()


@app.post("/api/applications", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED)
def apply_to_job(
    payload: ApplicationCreate,
    current_user_id: int = Depends(get_current_user_id),
) -> dict:
    db = SessionLocal()
    try:
        job = db.get(Job, payload.job_id)
        if job is None:
            raise HTTPException(
                status_code=404,
                detail="Job not found",
            )

        existing = (
            db.query(Application)
            .filter(
                Application.job_id == payload.job_id,
                Application.user_id == current_user_id,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=400,
                detail="You have already applied to this job",
            )

        match_score: int | None = None
        cv = _get_latest_cv(db, current_user_id)
        if cv:
            candidate_profile = get_candidate_profile(db, cv)
            requirements = analyze_job_description(job.description)
            m = analyze_match(
                candidate=candidate_profile, requirements=requirements
            )
            match_score = m["match_score"]

        company_name = job.company if job.company else ""

        application = Application(
            job_id=payload.job_id,
            user_id=current_user_id,
            status="applied",
            match_score=match_score,
        )
        db.add(application)
        db.commit()
        db.refresh(application)

        return {
            "id": application.id,
            "job_id": application.job_id,
            "job_title": job.title,
            "company": company_name,
            "candidate_name": "",
            "candidate_email": "",
            "status": application.status,
            "match_score": application.match_score,
            "applied_at": application.applied_at,
        }
    finally:
        db.close()


@app.post("/api/applications/{application_id}/reject")
def reject_application(
    application_id: int,
    current_user_id: int = Depends(get_current_user_id),
) -> dict:
    db = SessionLocal()
    try:
        application = db.get(Application, application_id)
        if application is None:
            raise HTTPException(
                status_code=404,
                detail="Application not found",
            )

        job = db.get(Job, application.job_id)
        if job is None or job.employer_id != current_user_id:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to update this application",
            )

        application.status = "rejected"
        db.commit()

        return {
            "id": application.id,
            "status": application.status,
            "message": "Application rejected",
        }
    finally:
        db.close()


@app.post("/api/applications/{application_id}/accept")
def accept_application(
    application_id: int,
    current_user_id: int = Depends(get_current_user_id),
) -> dict:
    db = SessionLocal()
    try:
        application = db.get(Application, application_id)
        if application is None:
            raise HTTPException(
                status_code=404,
                detail="Application not found",
            )

        job = db.get(Job, application.job_id)
        if job is None or job.employer_id != current_user_id:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to update this application",
            )

        application.status = "accepted"
        db.commit()

        return {
            "id": application.id,
            "status": application.status,
            "message": "Application accepted",
        }
    finally:
        db.close()


# ─── User stats route ───────────────────────────────────────────────


@app.get("/api/user/stats", response_model=UserStats)
def get_user_stats(
    current_user_id: int = Depends(get_current_user_id),
) -> dict:
    db = SessionLocal()
    try:
        role = _get_user_role(db, current_user_id)

        if role == "employer":
            jobs_posted = db.query(Job).filter(
                Job.employer_id == current_user_id
            ).count()
            applications_received = (
                db.query(Application)
                .join(Job)
                .filter(Job.employer_id == current_user_id)
                .count()
            )
            return {
                "cvs_uploaded": 0,
                "analyses_completed": 0,
                "applications": 0,
                "saved_jobs": 0,
                "jobs_posted": jobs_posted,
                "candidates_viewed": 0,
                "applications_received": applications_received,
                "profile_views": 0,
            }

        cvs_uploaded = db.query(CV).filter(
            CV.user_id == current_user_id
        ).count()
        analyses_completed = (
            db.query(Analysis)
            .join(CV)
            .filter(CV.user_id == current_user_id)
            .count()
        )
        applications = db.query(Application).filter(
            Application.user_id == current_user_id
        ).count()
        saved_jobs = db.query(SavedJob).filter(
            SavedJob.user_id == current_user_id
        ).count()

        return {
            "cvs_uploaded": cvs_uploaded,
            "analyses_completed": analyses_completed,
            "applications": applications,
            "saved_jobs": saved_jobs,
            "jobs_posted": 0,
            "candidates_viewed": 0,
            "applications_received": 0,
            "profile_views": 0,
        }
    finally:
        db.close()


# ─── Career insights route ──────────────────────────────────────────


@app.get("/api/job-recommendations")
def get_job_recommendations(
    cv_id: int | None = Query(default=None),
    current_user_id: int = Depends(get_current_user_id),
) -> dict:
    db = SessionLocal()
    try:
        if cv_id is not None:
            cv = db.get(CV, cv_id)
            if cv is None or cv.user_id != current_user_id:
                raise HTTPException(status_code=404, detail="CV not found")
            candidate_profile = get_candidate_profile(db, cv)
        else:
            cv = _get_latest_cv(db, current_user_id)
            if cv is None:
                return {"jobs": [], "profile": None}
            candidate_profile = get_candidate_profile(db, cv)

        open_jobs = db.query(Job).filter(Job.status == "open").all()

        # Retrieve, then rerank.
        #
        # Stage 1 (cheap, scales): rank every open job by cosine similarity
        # between its stored vector and the candidate's. One matrix multiply,
        # no text processing.
        #
        # Stage 2 (expensive, precise): run the full requirement extraction and
        # match analysis only on the shortlist that survives stage 1.
        #
        # Both stages are needed. Vector similarity captures "is this the right
        # kind of role" but cannot say which specific skills are missing;
        # analyze_match can, but is far too costly to run over an entire job
        # board. This is the same retrieval-then-rerank shape the CareerLens
        # assistant will use over a knowledge base later.
        retrieved = semantic_index.rank_jobs_for_cv(
            db, cv, candidate_profile, open_jobs, top_k=RERANK_CANDIDATES
        )
        semantic_scores = {job.id: score for job, score in retrieved}

        scored_jobs: list[dict] = []
        for job, _semantic_score in retrieved:
            # Deterministic extraction only -- no LLM call per job.
            requirements = analyze_job_description(job.description, use_llm=False)
            m = analyze_match(
                candidate=candidate_profile, requirements=requirements
            )
            match_breakdown = {
                "skills_match": round(
                    (len(m["matched_skills"]) / max(len(requirements.technical_skills), 1)) * 100
                ) if requirements.technical_skills else 0,
                "experience_match": m["experience_match"],
                "education_match": m["education_match"],
            }
            scored_jobs.append({
                "job_id": job.id,
                "job_title": job.title,
                "company": job.company,
                "match_score": float(m["match_score"]),
                "matched_skills": m["matched_skills"],
                "missing_skills": m["missing_skills"],
                "location": job.location,
                "salary_min": job.salary_min,
                "salary_max": job.salary_max,
                "employment_type": job.employment_type,
                "required_skills": _parse_json_list(job.required_skills),
                "experience_required": job.experience_required,
                "education_required": job.education_required,
                "match_breakdown": match_breakdown,
                "semantic_score": round(semantic_scores.get(job.id, 0.0), 4),
            })

        scored_jobs.sort(key=lambda x: x["match_score"], reverse=True)
        top_jobs = scored_jobs[:RECOMMENDATION_LIMIT]

        tips = _generate_personalized_tips(candidate_profile, top_jobs)

        return {
            "jobs": top_jobs,
            "profile": {
                "overall_score": min(100, len(candidate_profile.technical_skills) * 10 + len(candidate_profile.experience) * 10 + len(candidate_profile.education) * 10 + len(candidate_profile.certifications) * 10),
                "skills_count": len(candidate_profile.technical_skills) + len(candidate_profile.soft_skills),
                "experience_count": len(candidate_profile.experience),
            },
            "tips": tips,
        }
    finally:
        db.close()


def _generate_personalized_tips(candidate_profile, jobs: list[dict]) -> str:
    if not jobs:
        return "Upload your CV and explore job recommendations to get personalized career tips."

    avg_match = sum(j["match_score"] for j in jobs) / max(len(jobs), 1)
    top_gaps: dict[str, int] = {}
    for job in jobs[:5]:
        for skill in job.get("missing_skills", []):
            key = skill.lower()
            top_gaps[key] = top_gaps.get(key, 0) + 1
    sorted_gaps = sorted(top_gaps.items(), key=lambda x: x[1], reverse=True)

    tips_parts = []
    tips_parts.append(
        f"Your profile shows {len(candidate_profile.technical_skills)} technical skills, "
        f"{len(candidate_profile.experience)} experience entries, and "
        f"{len(candidate_profile.certifications)} certifications. "
        f"Average match score across recommended roles is {round(avg_match)}%."
    )

    if avg_match < 50:
        tips_parts.append(
            "Consider upskilling in areas that appear frequently in job requirements to improve your match scores."
        )
    elif avg_match >= 75:
        tips_parts.append(
            "Your profile aligns well with open roles. Focus on highlighting relevant achievements in your applications."
        )

    if sorted_gaps:
        gap_names = [s.title() for s, _ in sorted_gaps[:3]]
        tips_parts.append(
            f"Top skills to develop: {', '.join(gap_names)}. "
            "Adding these to your profile can significantly boost your match rate."
        )

    if len(candidate_profile.projects) < 2:
        tips_parts.append(
            "Add more projects to demonstrate practical application of your skills to employers."
        )

    return " ".join(tips_parts)


@app.post("/api/career-lens/chat")
def career_lens_chat(
    payload: dict = None,
    current_user_id: int = Depends(get_current_user_id),
) -> dict:
    if payload is None:
        payload = {}

    message = (payload.get("message") or "").strip()
    cv_id = payload.get("cv_id")

    if not message:
        raise HTTPException(status_code=400, detail="message is required")

    db = SessionLocal()
    try:
        candidate_profile = None
        if cv_id is not None:
            cv = db.get(CV, cv_id)
            if cv and cv.user_id == current_user_id:
                candidate_profile = get_candidate_profile(db, cv)
        else:
            cv = _get_latest_cv(db, current_user_id)
            if cv:
                candidate_profile = get_candidate_profile(db, cv)

        return assistant.answer(db, message, cv, candidate_profile)
    finally:
        db.close()


@app.get("/api/career-insights", response_model=CareerInsights)
def get_career_insights(
    current_user_id: int = Depends(get_current_user_id),
) -> dict:
    """Career insights derived from the roles relevant to *this* candidate.

    The important subtlety is which jobs the figures are computed over. Using
    every open posting makes the output nearly identical for everyone, because
    it just surfaces whatever the board happens to contain most of -- an
    accountant ends up being told to learn Docker. So the candidate's profile
    vector first selects the roles that are actually in their field, and demand,
    gaps and salary are measured only within that set.

    When nothing on the board is close enough to their field, that is stated
    plainly rather than papered over with the board's generic top skills.
    """
    db = SessionLocal()
    try:
        cv = _get_latest_cv(db, current_user_id)
        if cv is None:
            return {
                "profile_strength": 0,
                "skill_gaps": [],
                "market_value": "Upload your CV",
                "recommended_roles": [],
                "in_demand_skills": [],
                "salary_trends": None,
                "action_items": ["Upload your CV to get personalized insights."],
                "sources": ["No CV uploaded yet."],
            }

        candidate = get_candidate_profile(db, cv)
        candidate_skills_lower = {
            s.lower() for s in candidate.technical_skills + candidate.soft_skills
        }

        open_jobs = db.query(Job).filter(Job.status == "open").all()
        sources: list[str] = []

        # --- select the candidate's field ---------------------------------
        relevant: list[Job] = []
        if open_jobs:
            ranked = semantic_index.rank_jobs_for_cv(
                db, cv, candidate, open_jobs, top_k=INSIGHT_ROLE_POOL
            )
            relevant = [job for job, score in ranked if score >= ROLE_MATCH_FLOOR]

        if relevant:
            sources.append(
                f"Figures computed from the {len(relevant)} open role(s) matching "
                f"your profile, out of {len(open_jobs)} on the board."
            )
        elif open_jobs:
            sources.append(
                f"None of the {len(open_jobs)} open roles match your field closely "
                "enough to draw conclusions from, so no skill or salary figures "
                "are shown."
            )
        else:
            sources.append("There are no open job postings to analyse.")

        # --- demand, measured only within the candidate's field ------------
        demand_counts: dict[str, int] = {}
        skill_display: dict[str, str] = {}
        for job in relevant:
            for skill in _parse_json_list(job.required_skills):
                key = skill.strip().lower()
                if key:
                    demand_counts[key] = demand_counts.get(key, 0) + 1
                    skill_display.setdefault(key, skill.strip())

        gaps_ranked = [
            (key, count)
            for key, count in sorted(
                demand_counts.items(), key=lambda kv: kv[1], reverse=True
            )
            if key not in candidate_skills_lower
        ]
        skill_gaps = [skill_display[key] for key, _ in gaps_ranked[:6]]

        in_demand_skills = [
            {
                "skill": skill_display[key],
                "demand": round((count / len(relevant)) * 100) if relevant else 0,
            }
            for key, count in gaps_ranked[:6]
        ]

        # Skills the candidate already has that their field asks for -- useful
        # confirmation, and it makes the gap list meaningful by contrast.
        covered = [
            skill_display[key]
            for key in demand_counts
            if key in candidate_skills_lower
        ]
        if covered:
            sources.append(
                f"You already cover {len(covered)} of the "
                f"{len(demand_counts)} skills these roles ask for: "
                + ", ".join(sorted(covered)[:5])
                + ("..." if len(covered) > 5 else "")
            )

        # --- roles worth targeting ------------------------------------------
        recommended_roles: list[str] = []
        seen: set[str] = set()
        for job in relevant:
            title = (job.title or "").strip()
            if title and title.lower() not in seen:
                recommended_roles.append(title)
                seen.add(title.lower())
        recommended_roles = recommended_roles[:4]

        # --- salary, from relevant postings that publish it ------------------
        salary_pool = [j for j in relevant if j.salary_min or j.salary_max]
        salary_trends = None
        market_value = "Not enough salary data"

        if salary_pool:
            mins = [j.salary_min for j in salary_pool if j.salary_min]
            maxes = [j.salary_max for j in salary_pool if j.salary_max]
            all_values = mins + maxes
            if all_values:
                low = min(mins) if mins else min(all_values)
                high = max(maxes) if maxes else max(all_values)
                salary_trends = {
                    "min": int(low),
                    "max": int(high),
                    "average": int(sum(all_values) / len(all_values)),
                }
                market_value = f"${int(low):,} - ${int(high):,}"
                sources.append(
                    f"Salary range taken from {len(salary_pool)} matching "
                    "posting(s) that publish pay."
                )
        elif relevant:
            market_value = "No matching role lists a salary"
            sources.append(
                "None of the matching roles publish pay, so no range is shown."
            )
        else:
            market_value = "No matching roles"

        # --- profile completeness --------------------------------------------
        present = [
            bool(candidate.technical_skills),
            len(candidate.technical_skills) >= 5,
            bool(candidate.experience),
            len(candidate.experience) >= 2,
            bool(candidate.education),
            bool(candidate.projects),
            bool(candidate.certifications),
        ]
        profile_strength = round(sum(present) / len(present) * 100)
        sources.append(
            "Profile strength measures how complete your CV is (skills, "
            "experience, education, projects, certifications)."
        )

        # --- next steps -------------------------------------------------------
        action_items: list[str] = []
        for key, count in gaps_ranked[:3]:
            share = round((count / len(relevant)) * 100) if relevant else 0
            action_items.append(
                f"Learn {skill_display[key]} - asked for by {count} of the "
                f"{len(relevant)} roles matching your profile ({share}%)."
            )

        if not relevant and open_jobs:
            action_items.append(
                "No current opening matches your field. Broaden your CV's skills "
                "section, or check back as new roles are posted."
            )

        if not candidate.experience:
            action_items.append(
                "Add a work experience section with dated roles; none was detected."
            )
        elif len(candidate.experience) < 2:
            action_items.append(
                "Expand your experience section with quantifiable achievements."
            )
        if not candidate.projects:
            action_items.append(
                "Add projects with outcomes and links to evidence your skills."
            )
        if not candidate.certifications:
            action_items.append(
                "Add certifications relevant to your target roles."
            )
        if not action_items:
            action_items.append(
                "You cover the skills your field is asking for. Focus on "
                "tailoring applications to specific roles."
            )

        return {
            "profile_strength": profile_strength,
            "skill_gaps": skill_gaps,
            "market_value": market_value,
            "recommended_roles": recommended_roles,
            "in_demand_skills": in_demand_skills,
            "salary_trends": salary_trends,
            "action_items": action_items,
            "sources": sources,
        }
    finally:
        db.close()



@app.post("/api/reset-data")
def reset_user_data(
    current_user_id: int = Depends(get_current_user_id),
) -> dict:
    db = SessionLocal()
    try:
        cvs = db.query(CV).filter(CV.user_id == current_user_id).all()
        for cv in cvs:
            db.query(Analysis).filter(Analysis.cv_id == cv.id).delete()
            db.delete(cv)
        db.commit()
        return {"message": "All data reset successfully"}
    finally:
        db.close()


@app.delete("/api/analyses/{analysis_id}")
def delete_analysis(
    analysis_id: int,
    current_user_id: int = Depends(get_current_user_id),
) -> dict:
    db = SessionLocal()
    try:
        analysis = db.get(Analysis, analysis_id)
        if analysis is None:
            raise HTTPException(status_code=404, detail="Analysis not found")
        cv = db.get(CV, analysis.cv_id)
        if cv is None or cv.user_id != current_user_id:
            raise HTTPException(status_code=404, detail="Analysis not found")
        db.delete(analysis)
        db.commit()
        return {"message": "Analysis deleted"}
    finally:
        db.close()


# ─── Saved jobs routes ──────────────────────────────────────────────


# ─── Candidate search routes (employer) ─────────────────────────────


@app.get("/api/candidates")
def get_candidates(
    current_user_id: int = Depends(get_current_user_id),
    skills: str | None = Query(default=None),
    q: str | None = Query(default=None),
) -> list[dict]:
    """Return candidates who have uploaded at least one CV.

    Two search modes, both optional:

    * ``skills`` -- exact filter. A candidate must list at least one of the
      given skills verbatim. Precise, but blind to wording ("k8s" misses
      "Kubernetes").
    * ``q`` -- free-text semantic search. The query is embedded and candidates
      are ranked by cosine similarity to their profile vector, so a search for
      "someone who can run our cloud infrastructure" surfaces the DevOps
      engineers without naming a single tool.

    Given together, ``skills`` narrows the set and ``q`` orders what remains.
    """
    db = SessionLocal()
    try:
        # Only employers can search candidates
        role = _get_user_role(db, current_user_id)
        if role != "employer":
            raise HTTPException(
                status_code=403,
                detail="Only employers can search candidates",
            )

        query = (
            db.query(UserProfile, User, CV)
            .join(User, UserProfile.user_id == User.id)
            .join(CV, CV.user_id == User.id)
            .filter(UserProfile.role == "job_seeker")
        )

        rows = list(query)
        # Resolve all profiles up front: cached reads for CVs already parsed,
        # and a single commit for any that still need backfilling.
        profiles_by_cv = get_profiles_for_cvs(db, [cv for _, _, cv in rows])

        semantic_scores: dict[int, float] = {}
        if q and q.strip():
            ranked = semantic_index.rank_cvs_for_query(
                db,
                q,
                [cv for _, _, cv in rows],
                profiles_by_cv,
                min_score=SEMANTIC_SEARCH_FLOOR,
            )
            semantic_scores = {cv.id: score for cv, score in ranked}
            # Drop candidates the query did not plausibly reach at all.
            rows = [r for r in rows if r[2].id in semantic_scores]
            rows.sort(key=lambda r: semantic_scores[r[2].id], reverse=True)

        candidates: list[dict] = []
        for profile, user, cv in rows:
            candidate_profile = profiles_by_cv[cv.id]

            if skills:
                search_skills = [s.strip().lower() for s in skills.split(",")]
                candidate_skills_lower = [
                    s.lower() for s in candidate_profile.technical_skills
                ]
                matched = [s for s in search_skills if s in candidate_skills_lower]
                if not matched:
                    continue

            technical_skills = candidate_profile.technical_skills
            experience = candidate_profile.experience
            education = candidate_profile.education

            experience_level = "entry"
            if len(experience) >= 3:
                experience_level = "expert"
            elif len(experience) >= 2:
                experience_level = "senior"
            elif len(experience) >= 1:
                experience_level = "mid"

            # Realistic match score: weighted skill coverage (40%) +
            # experience level (25%) + education (20%) + analysis depth (15%)
            skill_coverage = min(100, (len(technical_skills) / 15) * 100)
            exp_score = {"entry": 25, "mid": 50, "senior": 75, "expert": 100}[experience_level]
            edu_score = min(100, len(education) * 25)
            depth_score = min(100, len(technical_skills) * 10)
            match_score = min(100, round(skill_coverage * 0.40 + exp_score * 0.25 + edu_score * 0.20 + depth_score * 0.15))

            candidates.append(
                {
                    "id": str(cv.id),
                    "user_id": user.id,
                    "name": profile.name or "Anonymous",
                    "email": user.email,
                    "location": "",
                    "headline": "",
                    "skills": technical_skills,
                    "experience_level": experience_level,
                    "match_score": match_score,
                    "experience": experience,
                    "education": education,
                    "summary": candidate_profile.technical_skills[:5],
                    "cv_url": cv.file_path,
                    "semantic_score": (
                        round(semantic_scores[cv.id], 4)
                        if cv.id in semantic_scores
                        else None
                    ),
                }
            )

        return candidates
    finally:
        db.close()


@app.get("/api/candidates/{candidate_id}")
def get_candidate_detail(
    candidate_id: int,
    current_user_id: int = Depends(get_current_user_id),
) -> dict:
    """Return detailed candidate profile (CV analysis) for an employer."""
    db = SessionLocal()
    try:
        role = _get_user_role(db, current_user_id)
        if role != "employer":
            raise HTTPException(
                status_code=403,
                detail="Only employers can view candidate profiles",
            )

        cv = db.get(CV, candidate_id)
        if cv is None:
            raise HTTPException(
                status_code=404,
                detail="Candidate not found",
            )

        profile = get_candidate_profile(db, cv)
        profile_info = _get_user_profile(db, cv.user_id)
        user = _get_user(db, cv.user_id)

        experience_level = "entry"
        if len(profile.experience) >= 3:
            experience_level = "expert"
        elif len(profile.experience) >= 2:
            experience_level = "senior"
        elif len(profile.experience) >= 1:
            experience_level = "mid"

        # Realistic match score for candidate profile
        skill_coverage = min(100, (len(profile.technical_skills) / 15) * 100)
        exp_score = {"entry": 25, "mid": 50, "senior": 75, "expert": 100}[experience_level]
        edu_score = min(100, len(profile.education) * 25)
        depth_score = min(100, len(profile.technical_skills) * 10)
        match_score = min(100, round(skill_coverage * 0.40 + exp_score * 0.25 + edu_score * 0.20 + depth_score * 0.15))

        experience_entries = [
            {"title": e, "company": "", "duration": ""}
            for e in profile.experience
        ]
        education_entries = [
            {"degree": e, "institution": "", "year": ""}
            for e in profile.education
        ]

        return {
            "id": str(cv.id),
            # The addressable identity. "id" above is a CV id, kept for the
            # existing UI; anything that contacts this person must use user_id.
            "user_id": cv.user_id,
            "name": profile_info.name if profile_info else "Anonymous",
            "email": user.email if user else "",
            "location": "",
            "headline": "",
            "summary": " ".join(profile.technical_skills[:10]),
            "skills": profile.technical_skills,
            "experience_level": experience_level,
            "match_score": match_score,
            "experience": experience_entries,
            "education": education_entries,
            "cv_url": cv.file_path,
        }
    finally:
        db.close()


# ─── Interviews & messaging ───────────────────────────────────────


def _resolve_target_user(db, *, user_id: int | None, cv_id: int | None) -> int:
    """Resolve who a request is addressed to.

    ``user_id`` is authoritative. ``cv_id`` is the legacy path: the employer UI
    identified candidates by CV id, so that value is resolved to the CV's owner
    rather than being used as a user id directly -- which would have delivered
    to whichever unrelated user shared that integer.
    """
    if user_id is not None:
        if db.get(User, user_id) is None:
            raise HTTPException(status_code=404, detail="User not found")
        return user_id

    if cv_id is not None:
        cv = db.get(CV, cv_id)
        if cv is None:
            raise HTTPException(status_code=404, detail="Candidate not found")
        return cv.user_id

    raise HTTPException(
        status_code=400,
        detail="A recipient is required",
    )


def _interview_to_dict(db, interview: Interview) -> dict:
    job = db.get(Job, interview.job_id) if interview.job_id else None
    return {
        "id": interview.id,
        "employer_id": interview.employer_id,
        "employer_name": _get_user_name(db, interview.employer_id),
        "company": _get_user_company(db, interview.employer_id),
        "candidate_user_id": interview.candidate_user_id,
        "candidate_name": _get_user_name(db, interview.candidate_user_id),
        "candidate_email": _get_user_email(db, interview.candidate_user_id) or "",
        "cv_id": interview.cv_id,
        "job_id": interview.job_id,
        "job_title": job.title if job else None,
        "scheduled_at": interview.scheduled_at,
        "status": interview.status,
        "mode": interview.mode or "video",
        "meeting_url": interview.meeting_url,
        "dial_in": interview.dial_in,
        "contact_email": interview.contact_email,
        "contact_phone": interview.contact_phone,
        "duration_minutes": interview.duration_minutes or 45,
        "timezone": interview.timezone,
        "location": interview.location,
        "notes": interview.notes,
        "created_at": interview.created_at,
    }


@app.post(
    "/api/interviews",
    response_model=InterviewRead,
    status_code=status.HTTP_201_CREATED,
)
def schedule_interview(
    payload: InterviewCreate,
    current_user_id: int = Depends(get_current_user_id),
) -> dict:
    """Schedule an interview with a candidate. Employers only."""
    db = SessionLocal()
    try:
        if _get_user_role(db, current_user_id) != "employer":
            raise HTTPException(
                status_code=403,
                detail="Only employers can schedule interviews",
            )

        candidate_user_id = _resolve_target_user(
            db,
            user_id=payload.candidate_user_id,
            cv_id=payload.candidate_id,
        )

        if candidate_user_id == current_user_id:
            raise HTTPException(
                status_code=400,
                detail="You cannot schedule an interview with yourself",
            )

        if payload.job_id is not None:
            job = db.get(Job, payload.job_id)
            if job is None or job.employer_id != current_user_id:
                raise HTTPException(
                    status_code=404, detail="Job not found"
                )

        # Keep the CV reference when the employer scheduled from a CV.
        cv_id = payload.candidate_id
        if cv_id is None:
            latest = _get_latest_cv(db, candidate_user_id)
            cv_id = latest.id if latest else None

        # Fall back to the employer's own account details so an interview is
        # never scheduled with no way to reach anyone. An explicit value on
        # the payload always wins.
        contact_email = payload.contact_email or _get_user_email(
            db, current_user_id
        )

        interview = Interview(
            employer_id=current_user_id,
            candidate_user_id=candidate_user_id,
            cv_id=cv_id,
            job_id=payload.job_id,
            scheduled_at=payload.scheduled_at,
            status="scheduled",
            mode=payload.mode,
            meeting_url=payload.meeting_url,
            dial_in=payload.dial_in,
            contact_email=contact_email,
            contact_phone=payload.contact_phone,
            duration_minutes=payload.duration_minutes,
            timezone=payload.timezone,
            location=payload.location,
            notes=payload.notes,
        )
        db.add(interview)
        db.commit()
        db.refresh(interview)

        return _interview_to_dict(db, interview)
    finally:
        db.close()


@app.get("/api/interviews", response_model=list[InterviewRead])
def get_interviews(
    current_user_id: int = Depends(get_current_user_id),
) -> list[dict]:
    """Interviews involving the caller, on either side."""
    db = SessionLocal()
    try:
        interviews = (
            db.query(Interview)
            .filter(
                or_(
                    Interview.employer_id == current_user_id,
                    Interview.candidate_user_id == current_user_id,
                )
            )
            .order_by(Interview.scheduled_at.desc())
            .all()
        )
        return [_interview_to_dict(db, i) for i in interviews]
    finally:
        db.close()


@app.patch(
    "/api/interviews/{interview_id}/details",
    response_model=InterviewRead,
)
def update_interview_details(
    interview_id: int,
    payload: InterviewDetailsUpdate,
    current_user_id: int = Depends(get_current_user_id),
) -> dict:
    """Correct the time or joining details of an interview you scheduled.

    Employer-only, and deliberately separate from the status endpoint: a
    status change is a decision one side makes about the interview, while a
    broken meeting link is housekeeping that should not require cancelling and
    re-booking.

    Rescheduling resets a confirmed interview to "scheduled". The candidate
    agreed to a specific time, so a new time needs their agreement again --
    silently keeping "confirmed" would show both sides an agreement that never
    happened.
    """
    db = SessionLocal()
    try:
        interview = db.get(Interview, interview_id)
        if interview is None or interview.employer_id != current_user_id:
            # 404 rather than 403: see update_job on why.
            raise HTTPException(status_code=404, detail="Interview not found")

        if interview.status in ("cancelled", "declined", "completed"):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"This interview is {interview.status} and can no longer "
                    "be edited. Schedule a new one instead."
                ),
            )

        changes = payload.model_dump(exclude_unset=True)
        if not changes:
            return _interview_to_dict(db, interview)

        new_time = changes.get("scheduled_at")
        time_moved = new_time is not None and new_time != interview.scheduled_at

        for field, value in changes.items():
            setattr(interview, field, value)

        if time_moved and interview.status == "confirmed":
            interview.status = "scheduled"

        db.commit()
        db.refresh(interview)
        return _interview_to_dict(db, interview)
    finally:
        db.close()


# Who may move an interview into a given state.
_INTERVIEW_TRANSITIONS = {
    "confirmed": "candidate",
    "declined": "candidate",
    "cancelled": "employer",
    "completed": "employer",
}


@app.patch("/api/interviews/{interview_id}", response_model=InterviewRead)
def update_interview_status(
    interview_id: int,
    payload: InterviewStatusUpdate,
    current_user_id: int = Depends(get_current_user_id),
) -> dict:
    """Confirm, decline, cancel or complete an interview.

    Each transition belongs to one side: a candidate confirms or declines, an
    employer cancels or marks complete.
    """
    db = SessionLocal()
    try:
        interview = db.get(Interview, interview_id)
        if interview is None:
            raise HTTPException(status_code=404, detail="Interview not found")

        if current_user_id not in (
            interview.employer_id,
            interview.candidate_user_id,
        ):
            raise HTTPException(status_code=404, detail="Interview not found")

        required_side = _INTERVIEW_TRANSITIONS.get(payload.status)
        if required_side is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "status must be one of: "
                    + ", ".join(sorted(_INTERVIEW_TRANSITIONS))
                ),
            )

        actor_is_employer = current_user_id == interview.employer_id
        if required_side == "employer" and not actor_is_employer:
            raise HTTPException(
                status_code=403,
                detail=f"Only the employer can mark an interview {payload.status}",
            )
        if required_side == "candidate" and actor_is_employer:
            raise HTTPException(
                status_code=403,
                detail=f"Only the candidate can mark an interview {payload.status}",
            )

        if interview.status in ("cancelled", "declined"):
            raise HTTPException(
                status_code=400,
                detail=f"This interview was already {interview.status}",
            )

        interview.status = payload.status
        db.commit()
        db.refresh(interview)
        return _interview_to_dict(db, interview)
    finally:
        db.close()


def _message_to_dict(db, message: Message) -> dict:
    return {
        "id": message.id,
        "sender_id": message.sender_id,
        "sender_name": _get_user_name(db, message.sender_id),
        "recipient_id": message.recipient_id,
        "recipient_name": _get_user_name(db, message.recipient_id),
        "body": message.body,
        "job_id": message.job_id,
        "read_at": message.read_at,
        "created_at": message.created_at,
    }


@app.post(
    "/api/messages",
    response_model=MessageRead,
    status_code=status.HTTP_201_CREATED,
)
def send_message(
    payload: MessageCreate,
    current_user_id: int = Depends(get_current_user_id),
) -> dict:
    """Send a direct message to another user."""
    db = SessionLocal()
    try:
        recipient_id = _resolve_target_user(
            db,
            user_id=payload.recipient_user_id,
            cv_id=payload.recipient_id,
        )

        if recipient_id == current_user_id:
            raise HTTPException(
                status_code=400,
                detail="You cannot message yourself",
            )

        body = payload.content.strip()
        if not body:
            raise HTTPException(
                status_code=400, detail="Message content is required"
            )

        message = Message(
            sender_id=current_user_id,
            recipient_id=recipient_id,
            body=body,
            job_id=payload.job_id,
        )
        db.add(message)
        db.commit()
        db.refresh(message)

        return _message_to_dict(db, message)
    finally:
        db.close()


@app.get("/api/messages", response_model=list[ConversationRead])
def get_conversations(
    current_user_id: int = Depends(get_current_user_id),
) -> list[dict]:
    """One row per correspondent, newest activity first."""
    db = SessionLocal()
    try:
        messages = (
            db.query(Message)
            .filter(
                or_(
                    Message.sender_id == current_user_id,
                    Message.recipient_id == current_user_id,
                )
            )
            .order_by(Message.created_at.desc())
            .all()
        )

        conversations: dict[int, dict] = {}
        for m in messages:
            other = (
                m.recipient_id if m.sender_id == current_user_id else m.sender_id
            )
            convo = conversations.get(other)
            if convo is None:
                convo = {
                    "user_id": other,
                    "name": _get_user_name(db, other),
                    "email": _get_user_email(db, other) or "",
                    "role": _get_user_role(db, other),
                    "last_message": m.body,
                    "last_message_at": m.created_at,
                    "last_sender_id": m.sender_id,
                    "unread_count": 0,
                }
                conversations[other] = convo

            if m.recipient_id == current_user_id and m.read_at is None:
                convo["unread_count"] += 1

        return sorted(
            conversations.values(),
            key=lambda c: c["last_message_at"],
            reverse=True,
        )
    finally:
        db.close()


@app.get("/api/messages/{other_user_id}", response_model=list[MessageRead])
def get_thread(
    other_user_id: int,
    current_user_id: int = Depends(get_current_user_id),
) -> list[dict]:
    """Full conversation with one user, oldest first.

    Reading a thread marks the messages the caller received in it as read.
    """
    db = SessionLocal()
    try:
        messages = (
            db.query(Message)
            .filter(
                or_(
                    and_(
                        Message.sender_id == current_user_id,
                        Message.recipient_id == other_user_id,
                    ),
                    and_(
                        Message.sender_id == other_user_id,
                        Message.recipient_id == current_user_id,
                    ),
                )
            )
            .order_by(Message.created_at.asc())
            .all()
        )

        now = datetime.utcnow()
        touched = False
        for m in messages:
            if m.recipient_id == current_user_id and m.read_at is None:
                m.read_at = now
                touched = True
        if touched:
            db.commit()

        return [_message_to_dict(db, m) for m in messages]
    finally:
        db.close()


@app.get("/api/messages/unread/count")
def get_unread_count(
    current_user_id: int = Depends(get_current_user_id),
) -> dict:
    """Badge count for the navigation."""
    db = SessionLocal()
    try:
        count = (
            db.query(Message)
            .filter(
                Message.recipient_id == current_user_id,
                Message.read_at.is_(None),
            )
            .count()
        )
        return {"unread": count}
    finally:
        db.close()


# ─── Company profile routes (employer) ─────────────────────────────


@app.get("/api/company")
def get_company_profile(
    current_user_id: int = Depends(get_current_user_id),
) -> dict:
    db = SessionLocal()
    try:
        profile = _get_user_profile(db, current_user_id)
        if profile is None:
            return {
                "id": "",
                "name": "",
                "description": "",
                "industry": "",
                "company_size": "1-10",
                "website": "",
                "linkedin": "",
                "twitter": "",
            }

        return {
            "id": str(current_user_id),
            "name": profile.company or "",
            "description": profile.description or "",
            "industry": profile.industry or "",
            "company_size": profile.company_size or "1-10",
            "website": profile.website or "",
            "linkedin": profile.linkedin or "",
            "twitter": profile.twitter or "",
        }
    finally:
        db.close()


@app.post("/api/company")
def upsert_company_profile(
    payload: dict = None,
    current_user_id: int = Depends(get_current_user_id),
) -> dict:
    if payload is None:
        payload = {}

    db = SessionLocal()
    try:
        profile = _get_user_profile(db, current_user_id)

        if profile is None:
            profile = UserProfile(
                user_id=current_user_id,
                role="employer",
            )
            db.add(profile)

        profile.company = payload.get("name") or profile.company
        profile.description = payload.get("description", profile.description)
        profile.industry = payload.get("industry", profile.industry)
        profile.company_size = payload.get(
            "company_size", profile.company_size
        )
        profile.website = payload.get("website", profile.website)
        profile.linkedin = payload.get("linkedin", profile.linkedin)
        profile.twitter = payload.get("twitter", profile.twitter)

        db.commit()

        return {
            "id": str(current_user_id),
            "name": profile.company or "",
            "description": profile.description or "",
            "industry": profile.industry or "",
            "company_size": profile.company_size or "1-10",
            "website": profile.website or "",
            "linkedin": profile.linkedin or "",
            "twitter": profile.twitter or "",
            "message": "Company profile saved successfully",
        }
    finally:
        db.close()


# ─── Saved jobs routes ──────────────────────────────────────────────


@app.get("/api/saved-jobs", response_model=list[SavedJobRead])
def get_saved_jobs(
    current_user_id: int = Depends(get_current_user_id),
) -> list[dict]:
    db = SessionLocal()
    try:
        saved = (
            db.query(SavedJob)
            .filter(SavedJob.user_id == current_user_id)
            .order_by(SavedJob.saved_at.desc())
            .all()
        )

        # The candidate profile is the same for every saved job, so resolve
        # it once rather than re-querying inside the loop.
        cv = _get_latest_cv(db, current_user_id)
        candidate_profile = get_candidate_profile(db, cv) if cv else None

        result: list[dict] = []
        for s in saved:
            job = db.get(Job, s.job_id)
            if job is None:
                continue

            match_score: float | None = None
            if candidate_profile is not None:
                requirements = analyze_job_description(
                    job.description, use_llm=False
                )
                m = analyze_match(
                    candidate=candidate_profile, requirements=requirements
                )
                match_score = float(m["match_score"])

            result.append({
                "id": s.id,
                "job_id": s.job_id,
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "salary_min": job.salary_min,
                "salary_max": job.salary_max,
                "saved_at": s.saved_at,
                "match_score": match_score,
                "required_skills": _parse_json_list(job.required_skills),
            })
        return result
    finally:
        db.close()


@app.post("/api/saved-jobs", status_code=status.HTTP_201_CREATED)
def save_job(
    payload: SavedJobCreate,
    current_user_id: int = Depends(get_current_user_id),
) -> dict:
    db = SessionLocal()
    try:
        job = db.get(Job, payload.job_id)
        if job is None:
            raise HTTPException(
                status_code=404,
                detail="Job not found",
            )

        existing = (
            db.query(SavedJob)
            .filter(
                SavedJob.job_id == payload.job_id,
                SavedJob.user_id == current_user_id,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Job already saved",
            )

        saved = SavedJob(
            job_id=payload.job_id,
            user_id=current_user_id,
        )
        db.add(saved)
        db.commit()
        db.refresh(saved)

        return {
            "id": saved.id,
            "job_id": saved.job_id,
            "saved_at": saved.saved_at,
            "message": "Job saved successfully",
        }
    finally:
        db.close()


@app.delete("/api/saved-jobs/{job_id}")
def unsave_job(
    job_id: int,
    current_user_id: int = Depends(get_current_user_id),
) -> dict:
    db = SessionLocal()
    try:
        saved = (
            db.query(SavedJob)
            .filter(
                SavedJob.job_id == job_id,
                SavedJob.user_id == current_user_id,
            )
            .first()
        )
        if saved is None:
            raise HTTPException(
                status_code=404,
                detail="Saved job not found",
            )

        db.delete(saved)
        db.commit()

        return {"message": "Job removed from saved items"}
    finally:
        db.close()


# ─── Admin routes ─────────────────────────────────────────────────────

ADMIN_ROLE = "admin"


@app.get("/api/admin/users")
def get_all_users(
    current_user_id: int = Depends(get_current_user_id),
) -> list[dict]:
    """Admin-only: list all users with their roles and profile data."""
    db = SessionLocal()
    try:
        role = _get_user_role(db, current_user_id)
        if role != ADMIN_ROLE:
            raise HTTPException(
                status_code=403,
                detail="Admin access required",
            )

        users = db.query(User).all()
        result = []
        for user in users:
            profile = _get_user_profile(db, user.id)
            cv_count = db.query(CV).filter(CV.user_id == user.id).count()
            job_count = db.query(Job).filter(Job.employer_id == user.id).count()
            app_count = db.query(Application).filter(Application.user_id == user.id).count()
            result.append({
                "id": user.id,
                "email": user.email,
                "role": profile.role if profile else "job_seeker",
                "company": profile.company if profile else None,
                "cv_count": cv_count,
                "jobs_posted": job_count,
                "applications": app_count,
            })
        return result
    finally:
        db.close()


@app.get("/api/admin/stats")
def get_admin_stats(
    current_user_id: int = Depends(get_current_user_id),
) -> dict:
    """Admin-only: system-wide statistics."""
    db = SessionLocal()
    try:
        role = _get_user_role(db, current_user_id)
        if role != ADMIN_ROLE:
            raise HTTPException(
                status_code=403,
                detail="Admin access required",
            )

        return {
            "total_users": db.query(User).count(),
            "total_jobs": db.query(Job).count(),
            "total_applications": db.query(Application).count(),
            "total_cvs": db.query(CV).count(),
            "total_analyses": db.query(Analysis).count(),
            "employers": db.query(User).join(UserProfile).filter(UserProfile.role == "employer").count(),
            "job_seekers": db.query(User).join(UserProfile).filter(UserProfile.role == "job_seeker").count(),
        }
    finally:
        db.close()


@app.get("/api/admin/users/{user_id}")
def get_user_detail(
    user_id: int,
    current_user_id: int = Depends(get_current_user_id),
) -> dict:
    """Admin-only: detailed view of a single user."""
    db = SessionLocal()
    try:
        role = _get_user_role(db, current_user_id)
        if role != ADMIN_ROLE:
            raise HTTPException(
                status_code=403,
                detail="Admin access required",
            )

        user = db.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        profile = _get_user_profile(db, user_id)
        cvs = db.query(CV).filter(CV.user_id == user_id).all()
        applications = db.query(Application).filter(Application.user_id == user_id).all()
        saved_jobs = db.query(SavedJob).filter(SavedJob.user_id == user_id).all()

        # Application has no job_title column; resolve titles in one query.
        job_ids = {a.job_id for a in applications}
        job_titles = {
            jid: title
            for jid, title in db.query(Job.id, Job.title).filter(Job.id.in_(job_ids))
        } if job_ids else {}

        return {
            "id": user.id,
            "email": user.email,
            "role": profile.role if profile else "job_seeker",
            "company": profile.company if profile else None,
            "name": profile.name if profile else None,
            "cvs": [{"id": cv.id, "filename": cv.filename} for cv in cvs],
            "applications": [
                {
                    "id": a.id,
                    "job_title": (job_titles.get(a.job_id) or "Unknown"),
                    "status": a.status,
                }
                for a in applications
            ],
            "saved_jobs_count": len(saved_jobs),
        }
    finally:
        db.close()


@app.delete("/api/admin/users/{user_id}")
def delete_user(
    user_id: int,
    current_user_id: int = Depends(get_current_user_id),
) -> dict:
    """Admin-only: delete a user and all their data."""
    db = SessionLocal()
    try:
        role = _get_user_role(db, current_user_id)
        if role != ADMIN_ROLE:
            raise HTTPException(
                status_code=403,
                detail="Admin access required",
            )

        user = db.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        if user_id == current_user_id:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete your own account",
            )

        db.delete(user)
        db.commit()
        return {"message": f"User {user.email} deleted"}
    finally:
        db.close()


# ─── Seed diverse jobs ────────────────────────────────────────────────

DIVERSE_JOBS = [
    {
        "title": "Senior Python Backend Engineer",
        "description": "We are looking for a Senior Python Backend Engineer to build scalable APIs using FastAPI, PostgreSQL, and AWS. You will design and implement backend services for our data processing platform.",
        "location": "San Francisco, CA",
        "salary_min": 120000, "salary_max": 160000,
        "employment_type": "full-time",
        "required_skills": ["Python", "FastAPI", "PostgreSQL", "AWS", "Docker", "Redis"],
        "experience_required": "5+ years",
        "education_required": "Bachelor degree",
        "responsibilities": "Design microservices, write clean APIs, deploy on AWS",
        "benefits": ["Health insurance", "401k", "Remote work", "Stock options"],
    },
    {
        "title": "Frontend React Developer",
        "description": "Join our team building modern web applications with React, TypeScript, and modern CSS. Must have strong UI/UX sensibilities.",
        "location": "Remote",
        "salary_min": 80000, "salary_max": 130000,
        "employment_type": "full-time",
        "required_skills": ["React", "TypeScript", "CSS", "HTML", "JavaScript"],
        "experience_required": "3+ years",
        "education_required": "Bachelor degree",
        "responsibilities": "Build responsive UIs, implement design systems",
        "benefits": ["Flexible hours", "Learning budget", "Remote work"],
    },
    {
        "title": "Data Scientist",
        "description": "We need a Data Scientist to build ML models and analyze large datasets. Experience with Python, statistical modeling, and deploying models to production.",
        "location": "New York, NY",
        "salary_min": 95000, "salary_max": 140000,
        "employment_type": "full-time",
        "required_skills": ["Python", "SQL", "Machine Learning", "Statistics", "Pandas", "Scikit-learn"],
        "experience_required": "3+ years",
        "education_required": "Master degree",
        "responsibilities": "Build ML models, conduct experiments, visualize insights",
        "benefits": ["Health insurance", "Gym stipend", "Conference budget"],
    },
    {
        "title": "DevOps Engineer",
        "description": "Seeking a DevOps Engineer to manage our cloud infrastructure on AWS. Experience with Kubernetes, CI/CD pipelines, and infrastructure as code.",
        "location": "Austin, TX",
        "salary_min": 100000, "salary_max": 150000,
        "employment_type": "full-time",
        "required_skills": ["AWS", "Docker", "Kubernetes", "Terraform", "CI/CD", "Linux"],
        "experience_required": "4+ years",
        "education_required": "Bachelor degree",
        "responsibilities": "Manage AWS infra, build CI/CD pipelines, monitor systems",
        "benefits": ["Health insurance", "Remote work", "Stock options"],
    },
    {
        "title": "Product Manager",
        "description": "Looking for a Product Manager to drive product strategy and work with cross-functional teams. Must have experience in agile environments.",
        "location": "Seattle, WA",
        "salary_min": 110000, "salary_max": 150000,
        "employment_type": "full-time",
        "required_skills": ["Product Management", "Agile", "Roadmapping", "Analytics", "Leadership"],
        "experience_required": "4+ years",
        "education_required": "Bachelor degree",
        "responsibilities": "Define roadmap, prioritize backlog, coordinate teams",
        "benefits": ["Health insurance", "401k", "Equity"],
    },
    {
        "title": "UX/UI Designer",
        "description": "Join our design team to create beautiful and intuitive user interfaces. Experience with Figma, user research, and design systems required.",
        "location": "Remote",
        "salary_min": 75000, "salary_max": 110000,
        "employment_type": "full-time",
        "required_skills": ["Figma", "UI Design", "UX Research", "Prototyping", "HTML/CSS"],
        "experience_required": "2+ years",
        "education_required": "Bachelor degree",
        "responsibilities": "Design wireframes, conduct user research, create design systems",
        "benefits": ["Health insurance", "Creative budget", "Remote work"],
    },
    {
        "title": "Salesforce Administrator",
        "description": "We need a Salesforce Administrator to manage our CRM system and support business users. Must have Salesforce certification.",
        "location": "Chicago, IL",
        "salary_min": 70000, "salary_max": 100000,
        "employment_type": "full-time",
        "required_skills": ["Salesforce", "CRM", "SQL", "Process Automation", "Reporting"],
        "experience_required": "3+ years",
        "education_required": "Bachelor degree",
        "responsibilities": "Manage Salesforce, create reports, support users",
        "benefits": ["Health insurance", "Training budget"],
    },
    {
        "title": "Marketing Data Analyst",
        "description": "Seeking a Marketing Data Analyst to analyze campaign performance and optimize marketing spend. Experience with SQL, Tableau, and marketing platforms.",
        "location": "Boston, MA",
        "salary_min": 65000, "salary_max": 95000,
        "employment_type": "full-time",
        "required_skills": ["SQL", "Tableau", "Google Analytics", "Python", "Marketing"],
        "experience_required": "2+ years",
        "education_required": "Bachelor degree",
        "responsibilities": "Analyze campaigns, build dashboards, report insights",
        "benefits": ["Health insurance", "Flexible hours"],
    },
]

@app.on_event("startup")
def seed_jobs_if_empty():
    """Seed diverse jobs across sectors if the jobs table is empty.

    Seeding is best-effort: a failure here must never prevent the API from
    starting, so the whole body is guarded.
    """
    if IS_PRODUCTION:
        # The seed accounts use fixed, weak, publicly documented passwords and
        # one of them is an administrator. They exist to make local development
        # easy and must never be created on a production database.
        logger.info("APP_ENV=production: skipping demo data seeding")
        return

    db = SessionLocal()
    try:
        if db.query(Job).count() > 0:
            return

        logger.warning(
            "Seeding demo accounts with well-known development passwords "
            "(employer@example.com, admin@careerlens.ai). Remove or change "
            "these before exposing this instance to anyone."
        )

        employer_user = _seed_user(
            db,
            email="employer@example.com",
            password="password123",
            role="employer",
            name="Example Employer",
            company="Example Corp",
        )
        _seed_user(
            db,
            email="admin@careerlens.ai",
            password="admin123",
            role="admin",
            name="Admin User",
        )

        for job_data in DIVERSE_JOBS:
            payload = dict(job_data)
            # required_skills/benefits are Text columns holding JSON, so the
            # literal lists in DIVERSE_JOBS must be encoded the same way
            # create_job() encodes them.
            payload["required_skills"] = _json_dumps(payload["required_skills"])
            payload["benefits"] = _json_dumps(payload["benefits"])
            db.add(Job(**payload, employer_id=employer_user.id, status="open"))
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Job seeding failed; continuing startup without seed data")
    finally:
        db.close()


def _seed_user(
    db,
    *,
    email: str,
    password: str,
    role: str,
    name: str,
    company: str | None = None,
) -> User:
    """Get or create a seed user together with its profile."""
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = User(email=email, password_hash=hash_password(password))
        db.add(user)
        db.commit()
        db.refresh(user)

    profile = _get_user_profile(db, user.id)
    if profile is None:
        db.add(
            UserProfile(
                user_id=user.id,
                role=role,
                name=name,
                company=company,
            )
        )
        db.commit()

    return user


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("ai_job_intelligence.main:app", host="127.0.0.1", port=8000, reload=True)
