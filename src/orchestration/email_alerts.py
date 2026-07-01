from __future__ import annotations

import os
import re
import smtplib
from datetime import UTC, datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from sqlalchemy.orm import Session

from src.config import settings
from src.ingestion.db import BronzeJob, EmailSubscription, SilverJob
from src.logger import logger

# Directory to save simulated emails when running in dry-run/development mode without SMTP credentials
SIMULATED_EMAILS_DIR = Path("logs/email_alerts")


def get_matching_jobs(session: Session, subscription: EmailSubscription, since_time: datetime) -> list[tuple[BronzeJob, SilverJob | None]]:
    """Fetch all jobs ingested since `since_time` that match the subscription's skills.

    A job matches if at least one subscription skill matches a tag on the job or a word in the job title.
    """
    # Query jobs ingested since the last checked time
    # Join BronzeJob with SilverJob to get enriched info if available
    jobs = (
        session.query(BronzeJob, SilverJob)
        .outerjoin(SilverJob, BronzeJob.id == SilverJob.job_id)
        .filter(BronzeJob.ingested_at >= since_time)
        .order_by(BronzeJob.publication_date.desc())
        .all()
    )

    if not subscription.skills:
        # If no specific skills are selected, subscription acts as "all new remote jobs"
        return jobs

    matched_jobs = []
    sub_skills = {s.strip().lower() for s in subscription.skills if s.strip()}

    for bronze, silver in jobs:
        # Gather all search terms from tags and title
        job_tags = {t.lower() for t in (bronze.tags or [])}
        title_words = set(re.findall(r"\b[a-zA-Z0-9+#\-\.]+\b", bronze.title.lower()))
        job_terms = job_tags.union(title_words)

        if sub_skills.intersection(job_terms):
            matched_jobs.append((bronze, silver))

    return matched_jobs


def build_email_html(subscription: EmailSubscription, jobs_list: list[tuple[BronzeJob, SilverJob | None]]) -> str:
    """Build a premium, responsive HTML email digest for matching jobs."""
    skills_list_str = ", ".join(f"<code>{s}</code>" for s in subscription.skills) if subscription.skills else "All remote fields"
    
    # Render job cards
    job_cards_html = ""
    for bronze, silver in jobs_list:
        salary_str = "Not specified"
        if silver and silver.salary_min and silver.salary_max:
            currency = silver.salary_currency or "$"
            salary_str = f"{currency}{int(silver.salary_min):,} - {currency}{int(silver.salary_max):,}"
        elif bronze.salary:
            salary_str = bronze.salary

        seniority_badge = ""
        if silver and silver.seniority and silver.seniority != "Unspecified":
            seniority_badge = f'<span class="badge badge-sen">{silver.seniority}</span>'

        source_name = bronze.source or "remotive"
        source_badge = f'<span class="badge badge-src">{source_name.upper()}</span>'
        location = bronze.candidate_required_location or "Remote"
        pub_date = bronze.publication_date.strftime("%b %d, %Y")

        job_cards_html += f"""
        <div class="job-card">
            <div class="job-title-row">
                <a href="{bronze.url}" class="job-title" target="_blank">{bronze.title}</a>
                <div>
                    {seniority_badge}
                    {source_badge}
                </div>
            </div>
            <div class="job-company">{bronze.company_name}</div>
            <div class="job-meta">
                <span>📍 {location}</span> &bull; 
                <span>💰 {salary_str}</span> &bull; 
                <span>📅 {pub_date}</span>
            </div>
        </div>
        """

    # Complete HTML template
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
    <style>
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: #0e1117;
            color: #c9d1d9;
            margin: 0;
            padding: 0;
            -webkit-font-smoothing: antialiased;
        }}
        .wrapper {{
            background-color: #0e1117;
            width: 100%;
            padding: 24px 0;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            background-color: #161b22;
            border: 1px solid #30363d;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.35);
        }}
        .header {{
            background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
            padding: 32px 24px;
            text-align: center;
            border-bottom: 1px solid #30363d;
        }}
        .header h1 {{
            color: #58a6ff;
            margin: 0;
            font-size: 24px;
            font-weight: 700;
            letter-spacing: -0.5px;
        }}
        .header p {{
            color: #8b949e;
            margin: 8px 0 0 0;
            font-size: 14px;
        }}
        .content {{
            padding: 24px;
        }}
        .intro {{
            font-size: 15px;
            line-height: 1.6;
            margin-bottom: 24px;
            color: #c9d1d9;
        }}
        .intro code {{
            background-color: #21262d;
            color: #58a6ff;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 13px;
        }}
        .job-card {{
            background-color: #0d1117;
            border: 1px solid #21262d;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 16px;
        }}
        .job-title-row {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
        }}
        .job-title {{
            color: #58a6ff;
            font-size: 16px;
            font-weight: 600;
            text-decoration: none;
        }}
        .job-title:hover {{
            text-decoration: underline;
        }}
        .job-company {{
            color: #e6edf3;
            font-weight: 500;
            font-size: 14px;
            margin-top: 4px;
        }}
        .job-meta {{
            font-size: 12px;
            color: #8b949e;
            margin-top: 12px;
        }}
        .badge {{
            display: inline-block;
            font-size: 10px;
            font-weight: 600;
            padding: 2px 8px;
            border-radius: 12px;
            margin-left: 6px;
            text-transform: uppercase;
        }}
        .badge-sen {{
            background-color: #382402;
            color: #f0883e;
        }}
        .badge-src {{
            background-color: #162c46;
            color: #58a6ff;
        }}
        .footer {{
            background-color: #0d1117;
            padding: 24px;
            text-align: center;
            border-top: 1px solid #21262d;
            font-size: 12px;
            color: #8b949e;
            line-height: 1.5;
        }}
        .footer a {{
            color: #58a6ff;
            text-decoration: none;
        }}
        .footer a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="wrapper">
        <div class="container">
            <div class="header">
                <h1>CareerLens Job Alerts</h1>
                <p>Global Remote Job Intelligence Digest</p>
            </div>
            <div class="content">
                <div class="intro">
                    Hello <strong>{subscription.name}</strong>,<br><br>
                    Here is your custom daily remote job digest for: {skills_list_str}. We found <strong>{len(jobs_list)}</strong> new matches since your last update.
                </div>
                
                {job_cards_html}
                
            </div>
            <div class="footer">
                This email was sent by CareerLens.<br>
                To unsubscribe or update your preferences, visit the dashboard or click the link below:<br><br>
                <a href="{settings.api_base_url}/api/v1/subscriptions/unsubscribe?email={subscription.email}" style="color: #f0883e;">Unsubscribe from job alerts</a>
            </div>
        </div>
    </div>
</body>
</html>
"""
    return html


def send_email_via_smtp(to_email: str, subject: str, html_body: str) -> bool:
    """Send an HTML email via SMTP server using settings credentials."""
    if not settings.smtp_user:
        logger.warning("SMTP_USER is empty. Email alerts will run in simulation mode.")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_user}>"
    msg["To"] = to_email

    msg.attach(MIMEText(html_body, "html"))

    try:
        # Connect to SMTP server
        server = smtplib.SMTP(settings.smtp_host, settings.smtp_port)
        server.ehlo()
        server.starttls()  # Upgrade connection to secure
        server.ehlo()
        server.login(settings.smtp_user, settings.smtp_password)
        server.sendmail(settings.smtp_user, to_email, msg.as_string())
        server.close()
        logger.info("Email alert successfully sent to %s", to_email)
        return True
    except Exception as exc:
        logger.error("Failed to send email to %s via SMTP: %s", to_email, exc)
        return False


def process_subscription_alert(session: Session, subscription: EmailSubscription, force: bool = False) -> bool:
    """Process a single subscription and send alert if matching new jobs are found."""
    now = datetime.now(UTC)
    
    # Calculate starting point for new jobs
    if subscription.last_sent_at:
        since_time = subscription.last_sent_at
        # Convert timezone-naive to UTC if needed (SQLAlchemy DateTime(timezone=True) normally yields timezone-aware)
        if since_time.tzinfo is None:
            since_time = since_time.replace(tzinfo=UTC)
    else:
        since_time = now - timedelta(days=1)

    # If it is not forced, verify that 23 hours have elapsed since the last alert
    if not force and subscription.last_sent_at:
        elapsed = now - since_time
        if elapsed < timedelta(hours=23):
            # Too early, skip
            return False

    # Fetch matching jobs
    matching_jobs = get_matching_jobs(session, subscription, since_time)
    if not matching_jobs:
        logger.info(
            "No new matching jobs for subscriber %s (%s) since %s",
            subscription.name,
            subscription.email,
            since_time.isoformat(),
        )
        # Still update last_sent_at to current time to avoid searching old window next time
        subscription.last_sent_at = now
        session.commit()
        return False

    logger.info(
        "Found %d matching jobs for subscriber %s (%s)",
        len(matching_jobs),
        subscription.name,
        subscription.email,
    )

    # Compile HTML body
    html_content = build_email_html(subscription, matching_jobs)
    subject = f"CareerLens: {len(matching_jobs)} new remote jobs matching your skills"

    # Try sending via SMTP
    sent = send_email_via_smtp(subscription.email, subject, html_content)
    
    # In both cases (real SMTP or mock simulation), we save copy of email to logs for easy inspection
    try:
        SIMULATED_EMAILS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")
        safe_email_name = subscription.email.replace("@", "_at_").replace(".", "_")
        log_file = SIMULATED_EMAILS_DIR / f"alert_{safe_email_name}_{timestamp_str}.html"
        log_file.write_text(html_content, encoding="utf-8")
        logger.info("Saved alert digest simulation to %s", log_file)
    except Exception as exc:
        logger.error("Could not write simulated email file: %s", exc)

    # Update subscription record
    subscription.last_sent_at = now
    session.commit()
    return True


def send_job_alerts(session: Session, force: bool = False) -> int:
    """Search active subscriptions and trigger matching job alerts.

    Args:
        session: Active SQLAlchemy DB session.
        force: If True, ignore the 23-hour limit and send alerts immediately.

    Returns:
        Number of alerts triggered.
    """
    logger.info("Executing job alerts dispatch cycle (force=%s)...", force)
    active_subs = (
        session.query(EmailSubscription)
        .filter(EmailSubscription.active.is_(True))
        .all()
    )

    sent_count = 0
    for sub in active_subs:
        try:
            if process_subscription_alert(session, sub, force=force):
                sent_count += 1
        except Exception as exc:
            logger.error("Failed to process subscription alert for %s: %s", sub.email, exc)

    logger.info("Job alerts dispatch complete | alerts_sent=%d", sent_count)
    return sent_count
