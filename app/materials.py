from __future__ import annotations

from app.config import Settings
from app.llm import LLMClient
from app.models import ApplicationStatus, GeneratedMaterials, JobApplication


def generate_materials(job: JobApplication, config: Settings) -> GeneratedMaterials:
    llm = LLMClient(config)
    prompt = (
        f"Create a concise cover letter for {job.title} at {job.company}. "
        "Use only facts in the supplied candidate profile. Do not invent experience.\n\n"
        f"Job description:\n{job.description}"
    )
    generated = llm.generate(
        "You write factual, specific job application materials for Sanat Konda.",
        prompt,
    )
    if not generated:
        generated = (
            f"Dear {job.company} Hiring Team,\n\n"
            f"I am interested in the {job.title} role. My Electrical and Computer "
            "Engineering work at the University of Florida includes FPGA, RTL, embedded "
            "systems, and hardware/software co-design projects that align with this opening. "
            "I would welcome the opportunity to discuss the role.\n\n"
            "Sincerely,\nSanat Konda"
        )
    job.generated_materials = GeneratedMaterials(cover_letter=generated)
    job.transition(ApplicationStatus.MATERIALS_GENERATED)
    job.log("materials_generated", fields=["cover_letter"], llm_used=bool(config.openai_api_key))
    return job.generated_materials
