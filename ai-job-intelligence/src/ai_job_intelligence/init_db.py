from ai_job_intelligence.database import Base, engine
from ai_job_intelligence.models.cv import CV
from ai_job_intelligence.models.analysis import Analysis
from ai_job_intelligence.models.user import User
from ai_job_intelligence.models.user_profile import UserProfile
from ai_job_intelligence.models.job import Job
from ai_job_intelligence.models.application import Application
from ai_job_intelligence.models.saved_job import SavedJob

def init_db() -> None:
    """Initialize the database and create tables."""
    Base.metadata.create_all(bind=engine)
    print("Database initialized and tables created.")


if __name__ == "__main__":
    init_db()
