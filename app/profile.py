from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from app.models import JobApplication


TOKEN_PATTERN = re.compile(r"[a-z0-9+#.-]{2,}")
STOP_WORDS = {
    "and",
    "are",
    "for",
    "from",
    "into",
    "the",
    "this",
    "using",
    "with",
}


def load_candidate_profile(path: str | Path) -> dict[str, Any]:
    profile_path = Path(path)
    if not profile_path.exists():
        return {}
    return yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {}


def application_facts(profile: dict[str, Any]) -> dict[str, Any]:
    facts = profile.get("application_facts")
    return facts if isinstance(facts, dict) else profile


def _tokens(value: str) -> set[str]:
    tokens: set[str] = set()
    for token in TOKEN_PATTERN.findall(value.lower()):
        if token not in STOP_WORDS:
            tokens.add(token)
        for part in re.split(r"[+#.-]+", token):
            if len(part) >= 2 and part not in STOP_WORDS:
                tokens.add(part)
            family = re.match(r"([a-z]+)\d", part)
            if family and len(family.group(1)) >= 2:
                tokens.add(family.group(1))
    return tokens


def select_relevant_projects(
    job: JobApplication,
    profile: dict[str, Any],
    limit: int = 4,
) -> list[dict[str, Any]]:
    facts = application_facts(profile)
    projects = facts.get("projects", [])
    if not isinstance(projects, list):
        return []

    job_tokens = _tokens(f"{job.title} {job.description}")
    ranked: list[tuple[int, str, dict[str, Any]]] = []
    for project in projects:
        if not isinstance(project, dict) or project.get("use_for_applications") is False:
            continue
        searchable = yaml.safe_dump(project, sort_keys=False)
        project_tokens = _tokens(searchable)
        overlap = job_tokens & project_tokens
        score = len(overlap)
        title = str(project.get("name", ""))
        if "fpga" in job_tokens and "fpga" in project_tokens:
            score += 5
        if "rtl" in job_tokens and {"rtl", "verilog", "systemverilog", "vhdl"} & project_tokens:
            score += 4
        if "robotics" in job_tokens and {"robotics", "ros", "autonomous"} & project_tokens:
            score += 4
        if "architecture" in job_tokens and {"processor", "pipeline", "soc"} & project_tokens:
            score += 4
        evidence = str(project.get("evidence", "")).lower()
        if "github readme" in evidence:
            score += 2
        if "official" in evidence or "uf robopi" in evidence:
            score += 2
        ranked.append((score, title.lower(), project))

    ranked.sort(key=lambda item: (-item[0], item[1]))
    relevant = [project for score, _, project in ranked if score > 0]
    if not relevant:
        relevant = [project for _, _, project in ranked]
    return relevant[:limit]


def build_candidate_context(
    profile: dict[str, Any],
    projects: list[dict[str, Any]],
) -> str:
    facts = application_facts(profile)
    context = {
        "identity": facts.get("identity", {}),
        "education": facts.get("education", []),
        "core_skills": facts.get("core_skills", {}),
        "experience": facts.get("experience", []),
        "leadership_and_accomplishments": facts.get(
            "leadership_and_accomplishments", []
        ),
        "most_relevant_projects": projects,
    }
    return yaml.safe_dump(context, sort_keys=False, allow_unicode=False)
