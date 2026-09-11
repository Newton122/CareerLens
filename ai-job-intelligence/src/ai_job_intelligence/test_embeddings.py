from ai_job_intelligence.services.embedding_service import (
    calculate_similarity,
)


job_text = "Develop RESTful backend APIs using Python."

cv_text = "Built web APIs and backend services with Python and FastAPI."

similarity = calculate_similarity(job_text, cv_text)

print(f"Similarity: {similarity:.4f}")