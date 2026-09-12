from __future__ import annotations

from datetime import datetime
from typing import List

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CVAnalysisRequest(BaseModel):
    cv_id:int
    job_title: str = Field(..., min_length=2)
    company: str | None = None
    job_description: str = Field(..., min_length=10)


class CVAnalysisResponse(BaseModel):
    analysis_id: int | None = None
    match_score: int
    matched_skills: List[str]
    missing_skills: List[str]
    # None means the job posting did not state this requirement, so it was
    # excluded from the score rather than counted as a perfect match.
    experience_match: int | None = None
    education_match: int | None = None
    recommendations: List[str]
    summary: str


class AnalysisRecord(BaseModel):
    id: str | None = None
    filename: str
    match_score: int
    matched_skills: List[str]
    missing_skills: List[str]
    summary: str


class SkillEvidence(BaseModel):
    """Where a skill was found in the CV, and the words that showed it.

    A skill named in a project description is stronger evidence than the same
    word in a comma-separated list, and this is what lets matching say so --
    and lets the candidate see why a skill did or did not count.
    """

    skill: str
    # "declared" | "experience" | "projects" | "certifications" | "summary" | "other"
    source: str
    context: str = ""


class CandidateProfile(BaseModel):
    name: str | None = None
    technical_skills: List[str] = Field(default_factory=list)
    soft_skills: List[str] = Field(default_factory=list)
    experience: List[str] = Field(default_factory=list)
    education: List[str] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    projects: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    # Empty on profiles cached before evidence existed; every consumer treats
    # a missing entry as "declared", which is the old behaviour.
    skill_evidence: List[SkillEvidence] = Field(default_factory=list)

class JobRequirements(BaseModel):
    technical_skills: List[str]
    soft_skills: List[str]
    required_experience: str
    education_requirements: str
    certifications: List[str]
    keywords: List[str]

    @property
    def experience_requirements(self) -> List[str]:
        if isinstance(self.required_experience, list):
            return self.required_experience
        if not self.required_experience:
            return []
        return [s.strip() for s in self.required_experience.split(",")]

    @property
    def education_requirements_list(self) -> List[str]:
        if isinstance(self.education_requirements, list):
            return self.education_requirements
        if not self.education_requirements:
            return []
        return [s.strip() for s in self.education_requirements.split(",")]


# Roles a person may choose for themselves when signing up. "admin" is
# deliberately absent: it was previously accepted straight from the request
# body, so anyone could register as an administrator and read every user's
# details. Admin access must be granted out of band.
SELF_ASSIGNABLE_ROLES = ("job_seeker", "employer")

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=254)
    # Length is enforced here; strength is checked by password_policy so the
    # user gets a specific explanation rather than a generic 422.
    password: str = Field(..., min_length=1, max_length=128)
    name: str | None = Field(default=None, max_length=120)
    role: str = "job_seeker"

    @field_validator("email")
    @classmethod
    def _valid_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not _EMAIL_RE.match(value):
            raise ValueError("Enter a valid email address")
        return value

    @field_validator("role")
    @classmethod
    def _allowed_role(cls, value: str) -> str:
        value = (value or "job_seeker").strip().lower()
        if value not in SELF_ASSIGNABLE_ROLES:
            raise ValueError(
                "role must be one of: " + ", ".join(SELF_ASSIGNABLE_ROLES)
            )
        return value


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=254)
    password: str = Field(..., min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def _normalise_email(cls, value: str) -> str:
        return value.strip().lower()


class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=254)

    @field_validator("email")
    @classmethod
    def _normalise_email(cls, value: str) -> str:
        return value.strip().lower()


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=10, max_length=200)
    password: str = Field(..., min_length=1, max_length=128)


class VerifyEmailRequest(BaseModel):
    token: str = Field(..., min_length=10, max_length=200)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    email: str
    role: str = "job_seeker"


class JobBase(BaseModel):
    title: str
    description: str
    location: str
    salary_min: int | None = None
    salary_max: int | None = None
    employment_type: str = "full-time"
    required_skills: list[str] = Field(default_factory=list)
    experience_required: str | None = None
    education_required: str | None = None
    responsibilities: str | None = None
    benefits: list[str] = Field(default_factory=list)


class JobCreate(JobBase):
    pass


# Statuses an employer may set on their own posting. "draft" hides a posting
# from candidates without deleting it; "closed" stops new applications while
# keeping the ones already received.
JOB_STATUSES = ("open", "closed", "draft")


class JobUpdate(BaseModel):
    """A partial edit of an existing posting.

    Every field is optional and ``None`` means "leave this alone", so a form
    that submits only the fields it changed cannot silently blank out the
    rest. That distinction matters for the nullable columns -- sending
    ``responsibilities: ""`` clears it, omitting the key does not.
    """

    title: str | None = Field(default=None, min_length=1)
    description: str | None = Field(default=None, min_length=1)
    location: str | None = Field(default=None, min_length=1)
    salary_min: int | None = None
    salary_max: int | None = None
    employment_type: str | None = None
    required_skills: list[str] | None = None
    experience_required: str | None = None
    education_required: str | None = None
    responsibilities: str | None = None
    benefits: list[str] | None = None
    status: str | None = None

    @field_validator("status")
    @classmethod
    def _known_status(cls, v: str | None) -> str | None:
        if v is not None and v not in JOB_STATUSES:
            raise ValueError(f"status must be one of: {', '.join(JOB_STATUSES)}")
        return v

    @field_validator("title", "location", "employment_type")
    @classmethod
    def _no_blank(cls, v: str | None) -> str | None:
        # A field that is present must carry a value; omit it to keep the
        # current one.
        if v is not None and not v.strip():
            raise ValueError("This field cannot be empty")
        return v.strip() if v is not None else v


class JobRead(JobBase):
    id: int
    status: str = "open"
    company: str = ""
    views: int = 0
    created_at: datetime
    applications_count: int = 0
    match_score: float | None = None
    skill_gaps: list[str] | None = None
    match_breakdown: dict | None = None

    model_config = ConfigDict(from_attributes=True)


class ApplicationCreate(BaseModel):
    job_id: int


class ApplicationRead(BaseModel):
    id: int
    job_id: int
    job_title: str
    company: str
    candidate_name: str | None = None
    candidate_email: str | None = None
    status: str
    match_score: int | None = None
    applied_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SavedJobCreate(BaseModel):
    job_id: int


class SavedJobRead(BaseModel):
    id: int
    job_id: int
    title: str
    company: str
    location: str
    salary_min: int | None = None
    salary_max: int | None = None
    saved_at: datetime
    match_score: float | None = None
    required_skills: list[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class UserStats(BaseModel):
    cvs_uploaded: int = 0
    analyses_completed: int = 0
    applications: int = 0
    saved_jobs: int = 0
    jobs_posted: int = 0
    candidates_viewed: int = 0
    applications_received: int = 0
    profile_views: int = 0


class CareerInsights(BaseModel):
    profile_strength: int
    skill_gaps: list[str]
    market_value: str
    recommended_roles: list[str]
    in_demand_skills: list[dict]
    salary_trends: dict | None = None
    action_items: list[str]
    # What each figure was computed from, so the UI can show its working
    # instead of presenting numbers with no provenance.
    sources: list[str] = Field(default_factory=list)


class CVAnalysisDetail(BaseModel):
    id: int
    cv_name: str
    overall_score: int
    summary: str
    strengths: list[str]
    weaknesses: list[str]
    recommendations: list[str]
    skills: list[dict]
    experience: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    experience_assessment: str
    education_assessment: str
    formatting_tips: list[str]
    ats_tips: list[str]
    action_verbs: list[str]
    analyzed_at: datetime
    sources: list[str] = Field(default_factory=list)
    # Where each detected skill was found, and the sentence that showed it.
    skill_evidence: list[dict] = Field(default_factory=list)
    # In-demand skills this CV does not evidence, for the resources panel.
    learn_next: list[str] = Field(default_factory=list)


class ProfileRead(BaseModel):
    name: str = ""
    email: str = ""
    role: str = "job_seeker"
    company: str = ""
    description: str = ""
    industry: str = ""
    company_size: str = ""
    website: str = ""
    linkedin: str = ""
    twitter: str = ""
    image_url: str = ""
    # False until the user clicks the link in their verification email.
    email_verified: bool = False


class ProfileUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    industry: str | None = None
    company_size: str | None = None
    website: str | None = None
    linkedin: str | None = None
    twitter: str | None = None
    company: str | None = None
    image_url: str | None = None

# ─── Interviews ──────────────────────────────────────────────────────


# How the two sides meet. Mirrors models.interview.INTERVIEW_MODES.
INTERVIEW_MODES = ("video", "phone", "onsite")

# A meeting shorter than 5 minutes is a typo; longer than 8 hours is not an
# interview. Bounds exist so a bad value cannot render an absurd end time.
MIN_DURATION_MINUTES = 5
MAX_DURATION_MINUTES = 480


def _validate_meeting_url(v: str | None) -> str | None:
    """Allow only http(s) links.

    This value is rendered as the href of a "Join" button. A "javascript:" or
    "data:" URL there would execute in the candidate's browser the moment they
    click it, so the scheme is checked on the way in rather than trusted at
    render time.
    """
    if v is None:
        return None
    v = v.strip()
    if not v:
        return None
    if not re.match(r"^https?://", v, re.IGNORECASE):
        raise ValueError("Meeting link must start with http:// or https://")
    return v


class InterviewCommsBase(BaseModel):
    """The details that make an interview attendable.

    Shared by the create and edit payloads so both sides validate identically
    -- an edit cannot smuggle in a link shape that create would have rejected.
    """

    mode: str = "video"
    meeting_url: str | None = None
    dial_in: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    duration_minutes: int = 45
    timezone: str | None = None
    location: str | None = None
    notes: str | None = None

    @field_validator("mode")
    @classmethod
    def _known_mode(cls, v: str) -> str:
        if v not in INTERVIEW_MODES:
            raise ValueError(f"mode must be one of: {', '.join(INTERVIEW_MODES)}")
        return v

    @field_validator("meeting_url")
    @classmethod
    def _safe_url(cls, v: str | None) -> str | None:
        return _validate_meeting_url(v)

    @field_validator("duration_minutes")
    @classmethod
    def _sane_duration(cls, v: int) -> int:
        if not MIN_DURATION_MINUTES <= v <= MAX_DURATION_MINUTES:
            raise ValueError(
                f"Duration must be between {MIN_DURATION_MINUTES} and "
                f"{MAX_DURATION_MINUTES} minutes"
            )
        return v


class InterviewCreate(InterviewCommsBase):
    """Schedule an interview.

    Address the candidate with ``candidate_user_id``. ``candidate_id`` is the
    legacy field the employer UI used to send, carrying a *CV* id; it is still
    accepted and resolved to that CV's owner.
    """

    candidate_user_id: int | None = None
    candidate_id: int | None = None
    job_id: int | None = None
    scheduled_at: datetime


class InterviewDetailsUpdate(BaseModel):
    """An employer's edit of an already-scheduled interview.

    Separate from InterviewStatusUpdate: moving an interview to "confirmed" is
    a decision that belongs to one side, whereas correcting a broken meeting
    link is housekeeping the employer does at any point. Every field is
    optional; ``None`` leaves the stored value alone.
    """

    scheduled_at: datetime | None = None
    mode: str | None = None
    meeting_url: str | None = None
    dial_in: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    duration_minutes: int | None = None
    timezone: str | None = None
    location: str | None = None
    notes: str | None = None

    @field_validator("mode")
    @classmethod
    def _known_mode(cls, v: str | None) -> str | None:
        if v is not None and v not in INTERVIEW_MODES:
            raise ValueError(f"mode must be one of: {', '.join(INTERVIEW_MODES)}")
        return v

    @field_validator("meeting_url")
    @classmethod
    def _safe_url(cls, v: str | None) -> str | None:
        return _validate_meeting_url(v)

    @field_validator("duration_minutes")
    @classmethod
    def _sane_duration(cls, v: int | None) -> int | None:
        if v is not None and not MIN_DURATION_MINUTES <= v <= MAX_DURATION_MINUTES:
            raise ValueError(
                f"Duration must be between {MIN_DURATION_MINUTES} and "
                f"{MAX_DURATION_MINUTES} minutes"
            )
        return v


class InterviewRead(BaseModel):
    id: int
    employer_id: int
    employer_name: str = ""
    company: str = ""
    candidate_user_id: int
    candidate_name: str = ""
    candidate_email: str = ""
    cv_id: int | None = None
    job_id: int | None = None
    job_title: str | None = None
    scheduled_at: datetime
    status: str
    mode: str = "video"
    meeting_url: str | None = None
    dial_in: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    duration_minutes: int = 45
    timezone: str | None = None
    location: str | None = None
    notes: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InterviewStatusUpdate(BaseModel):
    status: str


# ─── Messages ────────────────────────────────────────────────────────


class MessageCreate(BaseModel):
    """Send a direct message.

    ``recipient_user_id`` is the address. ``recipient_id`` is the legacy field
    the employer UI sent, carrying a CV id, and is resolved to its owner.
    """

    recipient_user_id: int | None = None
    recipient_id: int | None = None
    job_id: int | None = None
    content: str = Field(..., min_length=1)


class MessageRead(BaseModel):
    id: int
    sender_id: int
    sender_name: str = ""
    recipient_id: int
    recipient_name: str = ""
    body: str
    job_id: int | None = None
    read_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationRead(BaseModel):
    """One correspondent, plus the most recent message exchanged with them."""

    user_id: int
    name: str = ""
    email: str = ""
    role: str = ""
    last_message: str = ""
    last_message_at: datetime | None = None
    last_sender_id: int | None = None
    unread_count: int = 0
