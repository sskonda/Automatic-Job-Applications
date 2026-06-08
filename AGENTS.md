# Agent Rules

- Never scrape or automate applications on LinkedIn or Indeed.
- Never bypass CAPTCHA, login walls, rate limits, robots.txt, or access controls.
- Pause and create a special case for unknown, legal, sensitive, or demographic answers.
- Use only facts from `profile/sanat_profile.yaml` and explicitly approved values from
  `profile/preapproved_answers.yaml`.
- Keep `AUTO_SUBMIT_ENABLED=false` until the user has reviewed the configured sources,
  answers, and portal adapter.
- Record every ranking, field, generated answer, upload, submission, receipt, exception,
  email, reply, and state change in the job audit log.
- Do not commit credentials, OAuth tokens, API keys, resumes containing private data, or
  generated application artifacts.
