from __future__ import annotations

import streamlit as st

from app.config import settings
from app.storage import JobStore


st.set_page_config(page_title="Local Job Agent", layout="wide")
st.title("Sanat's Local Job Application Agent")
st.caption("Review rankings, queued submissions, special cases, and audit history.")

store = JobStore(settings.database_path)
jobs = store.list()

status_filter = st.selectbox(
    "Status",
    ["all"] + sorted({job.status.value for job in jobs}),
)
visible = jobs if status_filter == "all" else [
    job for job in jobs if job.status.value == status_filter
]

st.metric("Jobs", len(visible))
for job in visible:
    with st.expander(
        f"{job.company} - {job.title} | {job.score:.1f} | {job.status.value}"
    ):
        st.write(job.location)
        st.link_button("Open job", job.job_url)
        st.write(job.recommendation)
        if job.concerns:
            st.warning("\n".join(job.concerns))
        if job.exception_reason:
            st.error(job.exception_reason)
        st.json(job.model_dump(mode="json"))
