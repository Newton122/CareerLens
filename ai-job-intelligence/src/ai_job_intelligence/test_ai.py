from ai_job_intelligence.services.ai_service import analyze_job_description


job = """
We are looking for a backend developer with strong Python and FastAPI
experience.

The candidate should have experience working with PostgreSQL, REST APIs,
Docker and Git.

At least 2 years of backend development experience is preferred.
A degree in Computer Science or a related field is required.
AWS experience is a plus.
"""

result = analyze_job_description(job)

print("\nTECHNICAL SKILLS:")
print(result.technical_skills)

print("\nSOFT SKILLS:")
print(result.soft_skills)

print("\nEXPERIENCE:")
print(result.experience_requirements)

print("\nEDUCATION:")
print(result.education_requirements)

print("\nCERTIFICATIONS:")
print(result.certifications)

print("\nKEYWORDS:")
print(result.keywords)