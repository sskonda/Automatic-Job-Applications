from pathlib import Path

import yaml

from app.config import Settings
from app.materials import build_materials_prompt, generate_materials
from app.models import JobApplication
from app.profile import load_candidate_profile, select_relevant_projects


def make_job() -> JobApplication:
    return JobApplication(
        title="FPGA SoC Engineer",
        company="Example",
        source="greenhouse",
        job_url="https://example.com/jobs/1",
        description="Design AXI RTL, custom FPGA IP, and embedded C firmware.",
    )


def write_profile(path: Path) -> None:
    path.write_text(
        yaml.safe_dump(
            {
                "application_facts": {
                    "identity": {"name": "Sanat Konda"},
                    "projects": [
                        {
                            "name": "FPGA Rover",
                            "summary": "Zynq AXI custom IP and FreeRTOS robotics",
                            "keywords": ["FPGA", "AXI", "RTL"],
                        },
                        {
                            "name": "Web Dashboard",
                            "summary": "Frontend application",
                            "keywords": ["React"],
                        },
                    ],
                },
                "review_required_claims": [
                    {"issue": "Unconfirmed metric", "details": "3x faster"}
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def test_fpga_project_is_selected_for_fpga_job(tmp_path: Path) -> None:
    path = tmp_path / "profile.yaml"
    write_profile(path)
    projects = select_relevant_projects(make_job(), load_candidate_profile(path))
    assert projects[0]["name"] == "FPGA Rover"


def test_hyphenated_axi_project_matches_axi_job(tmp_path: Path) -> None:
    path = tmp_path / "profile.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "application_facts": {
                    "projects": [
                        {
                            "name": "Documented Rover",
                            "keywords": ["AXI4-Lite", "Zynq-7000", "FPGA"],
                            "evidence": "GitHub README",
                        },
                        {
                            "name": "Undocumented Filter",
                            "keywords": ["FPGA", "RTL"],
                            "evidence": "CV",
                        },
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    axi_job = JobApplication(
        title="SoC Integration Engineer",
        company="Example",
        source="greenhouse",
        job_url="https://example.com/jobs/axi",
        description="Design AXI peripherals for Zynq platforms.",
    )
    projects = select_relevant_projects(axi_job, load_candidate_profile(path))
    assert projects[0]["name"] == "Documented Rover"


def test_materials_prompt_excludes_review_required_claims(tmp_path: Path) -> None:
    path = tmp_path / "profile.yaml"
    write_profile(path)
    config = Settings(profile_path=path, openai_api_key="")
    prompt, _ = build_materials_prompt(make_job(), config)
    assert "FPGA Rover" in prompt
    assert "3x faster" not in prompt


def test_fallback_cover_letter_uses_relevant_project(tmp_path: Path) -> None:
    path = tmp_path / "profile.yaml"
    write_profile(path)
    job = make_job()
    materials = generate_materials(
        job,
        Settings(profile_path=path, openai_api_key=""),
    )
    assert "FPGA Rover" in (materials.cover_letter or "")
