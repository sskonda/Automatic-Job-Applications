from pathlib import Path

from app.application_queue import load_preapproved_answers


def test_preapproved_answers_expand_environment_variables(
    tmp_path: Path, monkeypatch
) -> None:
    path = tmp_path / "answers.yaml"
    path.write_text(
        "email: ${APPLICANT_EMAIL}\nphone: ${APPLICANT_PHONE}\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("APPLICANT_EMAIL", "sanat@example.com")
    monkeypatch.delenv("APPLICANT_PHONE", raising=False)

    answers = load_preapproved_answers(path)

    assert answers["email"] == "sanat@example.com"
    assert answers["phone"] == ""
