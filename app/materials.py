from __future__ import annotations

from app.config import Settings
from app.llm import LLMClient
from app.models import ApplicationStatus, GeneratedMaterials, JobApplication
from app.profile import (
    build_candidate_context,
    load_candidate_profile,
    select_relevant_projects,
)


def build_materials_prompt(job: JobApplication, config: Settings) -> tuple[str, list[dict]]:
    profile = load_candidate_profile(config.profile_path)
    projects = select_relevant_projects(job, profile)
    context = build_candidate_context(profile, projects)
    prompt = (
        f"Create a concise cover letter for {job.title} at {job.company}. "
        "Use only facts in the candidate context below. Do not invent experience, metrics, "
        "project status, or individual ownership. Do not use facts from any "
        "review_required_claims section.\n\n"
        f"Candidate context:\n{context}\n"
        f"Job description:\n{job.description}"
    )
    return prompt, projects


def generate_materials(job: JobApplication, config: Settings) -> GeneratedMaterials:
    llm = LLMClient(config)
    prompt, projects = build_materials_prompt(job, config)
    selected_project_names = [str(project.get("name")) for project in projects]
    generated = llm.generate(
        "You write factual, specific job application materials for Sanat Konda.",
        prompt,
    )
    if not generated:
        project_names = selected_project_names[:2]
        project_text = (
            f" Projects such as {' and '.join(project_names)} demonstrate this background."
            if project_names
            else ""
        )
        generated = (
            f"Dear {job.company} Hiring Team,\n\n"
            f"I am interested in the {job.title} role. My Electrical and Computer "
            "Engineering work at the University of Florida includes FPGA, RTL, embedded "
            "systems, and hardware/software co-design projects that align with this opening."
            f"{project_text} "
            "I would welcome the opportunity to discuss the role.\n\n"
            "Sincerely,\nSanat Konda"
        )
    job.generated_materials = GeneratedMaterials(cover_letter=generated)
    job.transition(ApplicationStatus.MATERIALS_GENERATED)
    job.log(
        "materials_generated",
        fields=["cover_letter"],
        llm_used=bool(config.openai_api_key),
        selected_projects=selected_project_names,
    )
    return job.generated_materials
