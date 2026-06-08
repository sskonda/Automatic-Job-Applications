from app.models import JobApplication
from app.ranker import score_job


def job(title: str, description: str) -> JobApplication:
    return JobApplication(
        title=title,
        company="Example",
        source="greenhouse",
        job_url=f"https://example.com/{title.replace(' ', '-')}",
        description=description,
    )


def test_fpga_job_scores_high() -> None:
    result = score_job(
        job("FPGA Design Engineer", "RTL, Verilog, Vivado, AXI, PCIe and embedded C")
    )
    assert result.score >= 75


def test_gpu_architecture_job_scores_high() -> None:
    result = score_job(
        job(
            "GPU Architecture Engineer",
            "Computer architecture, RTL, SystemVerilog and hardware acceleration",
        )
    )
    assert result.score >= 75


def test_web_developer_job_scores_low() -> None:
    result = score_job(job("Web Developer", "Frontend React.js and sales website work"))
    assert result.score < 45


def test_plc_job_scores_low() -> None:
    result = score_job(job("Controls Engineer", "PLC programming and building power systems"))
    assert result.score < 45
