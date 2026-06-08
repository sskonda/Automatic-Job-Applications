from __future__ import annotations

import re

from app.models import ApplicationStatus, JobApplication


STRONG_KEYWORDS = {
    "fpga": 18,
    "rtl": 16,
    "verilog": 13,
    "vhdl": 13,
    "systemverilog": 13,
    "uvm": 12,
    "asic": 15,
    "soc": 13,
    "computer architecture": 16,
    "gpu architecture": 18,
    "design verification": 14,
    "digital design": 13,
    "hardware acceleration": 14,
    "embedded systems": 10,
    "firmware": 7,
    "vivado": 9,
    "vitis": 8,
    "axi": 8,
    "pcie": 8,
    "ddr": 7,
    "ethernet": 6,
    "freeRTOS": 6,
    "zephyr": 6,
    "arm cortex": 6,
    "robotics": 6,
    "embedded c": 6,
    "c++": 4,
    "python": 3,
}

TARGET_TITLES = {
    "fpga engineer": 25,
    "rtl design engineer": 25,
    "digital design engineer": 23,
    "asic design engineer": 23,
    "design verification engineer": 23,
    "soc design engineer": 23,
    "gpu architecture engineer": 25,
    "computer architecture engineer": 25,
    "hardware acceleration engineer": 24,
    "embedded systems engineer": 18,
    "firmware engineer": 10,
}

NEGATIVE_KEYWORDS = {
    "plc": -35,
    "electrician": -45,
    "building power": -35,
    "help desk": -45,
    "helpdesk": -45,
    "sales": -30,
    "recruiter": -35,
    "frontend": -30,
    "front-end": -30,
    "web developer": -35,
    "react.js": -25,
}


def _contains(text: str, term: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(term.lower())}(?!\w)", text.lower()) is not None


def score_job(job: JobApplication) -> JobApplication:
    title = job.title.lower()
    haystack = f"{job.title}\n{job.description}".lower()
    score = 20.0
    matches: list[str] = []
    concerns: list[str] = []

    for term, points in TARGET_TITLES.items():
        if term in title:
            score += points
            matches.append(term)

    for term, points in STRONG_KEYWORDS.items():
        if _contains(haystack, term):
            score += points
            matches.append(term)

    for term, points in NEGATIVE_KEYWORDS.items():
        if _contains(haystack, term):
            score += points
            concerns.append(term)

    if re.search(r"\b(senior|staff|principal|lead)\b", title):
        if not re.search(r"\b(new grad|entry.level|0.?2 years|early career)\b", haystack):
            score -= 30
            concerns.append("seniority may exceed target level")

    if re.search(r"\b(7|8|9|10)\+?\s+years\b", haystack):
        score -= 25
        concerns.append("requires 7+ years of experience")

    if "security clearance" in haystack or "us citizen" in haystack:
        concerns.append("clearance or citizenship answer requires review")

    job.score = max(0.0, min(100.0, score))
    job.matched_keywords = sorted(set(matches))
    job.concerns = sorted(set(job.concerns + concerns))
    if job.score >= 75:
        job.recommendation = "strong match"
    elif job.score >= 65:
        job.recommendation = "review for application"
    elif job.score >= 45:
        job.recommendation = "lower priority"
    else:
        job.recommendation = "skip"
    job.transition(ApplicationStatus.RANKED)
    job.log("job_scored", score=job.score, matches=job.matched_keywords, concerns=job.concerns)
    return job
