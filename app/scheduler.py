from __future__ import annotations

from apscheduler.schedulers.blocking import BlockingScheduler

from app.application_queue import ApplicationQueue
from app.config import Settings, settings
from app.sources.collector import collect_configured_jobs


def run_daily(config: Settings = settings) -> None:
    ApplicationQueue(config).run(collect_configured_jobs(config.sources_path))


def poll_email_replies(config: Settings = settings) -> None:
    ApplicationQueue(config).process_email_replies()


def start_scheduler(config: Settings = settings) -> None:
    scheduler = BlockingScheduler(timezone="America/New_York")
    scheduler.add_job(
        run_daily,
        "cron",
        hour=8,
        minute=0,
        kwargs={"config": config},
        id="daily_job_agent",
        replace_existing=True,
    )
    scheduler.add_job(
        poll_email_replies,
        "interval",
        minutes=config.email_poll_interval_minutes,
        kwargs={"config": config},
        id="job_agent_email_replies",
        replace_existing=True,
    )
    scheduler.start()


if __name__ == "__main__":
    start_scheduler()
