from __future__ import annotations

import smtplib
from datetime import UTC, datetime, timedelta
import pytest
from sqlalchemy.orm import Session

from src.config import settings
from src.ingestion.db import BronzeJob, EmailSubscription, SilverJob, get_session, init_db
from src.orchestration.email_alerts import (
    build_email_html,
    get_matching_jobs,
    process_subscription_alert,
    send_email_via_smtp,
    send_job_alerts,
)


@pytest.fixture
def db_session(sqlite_db_url: str) -> Session:
    """Create in-memory SQLite session with tables initialized."""
    init_db(db_url=sqlite_db_url)
    session = get_session(db_url=sqlite_db_url)
    try:
        yield session
    finally:
        session.close()


def test_get_matching_jobs(db_session: Session) -> None:
    # 1. Setup subscription
    sub = EmailSubscription(
        name="Alex",
        email="alex@example.com",
        skills=["python", "fastapi"],
    )
    db_session.add(sub)

    # 2. Setup jobs
    # Match: Tag match
    j1 = BronzeJob(
        id=1,
        url="http://x.com/1",
        title="Software Developer",
        company_name="A",
        tags=["python", "docker"],
        publication_date=datetime.now(UTC) - timedelta(hours=2),
        ingested_at=datetime.now(UTC) - timedelta(hours=2),
    )
    # Match: Title match
    j2 = BronzeJob(
        id=2,
        url="http://x.com/2",
        title="FastAPI Engineer",
        company_name="B",
        tags=["web"],
        publication_date=datetime.now(UTC) - timedelta(hours=1),
        ingested_at=datetime.now(UTC) - timedelta(hours=1),
    )
    # No match
    j3 = BronzeJob(
        id=3,
        url="http://x.com/3",
        title="Rust Programmer",
        company_name="C",
        tags=["rust"],
        publication_date=datetime.now(UTC) - timedelta(hours=1),
        ingested_at=datetime.now(UTC) - timedelta(hours=1),
    )
    db_session.add_all([j1, j2, j3])
    db_session.commit()

    since_time = datetime.now(UTC) - timedelta(hours=5)
    matches = get_matching_jobs(db_session, sub, since_time)
    
    matched_ids = [m[0].id for m in matches]
    assert len(matched_ids) == 2
    assert 1 in matched_ids
    assert 2 in matched_ids
    assert 3 not in matched_ids


def test_build_email_html() -> None:
    sub = EmailSubscription(name="Alice", email="alice@gmail.com", skills=["python"])
    job = BronzeJob(
        id=99,
        url="https://xyz.com",
        title="Python Lead",
        company_name="Acme",
        tags=["python"],
        publication_date=datetime.now(UTC),
    )
    html = build_email_html(sub, [(job, None)])
    assert "Alice" in html
    assert "Python Lead" in html
    assert "Acme" in html
    assert "alice@gmail.com" in html


def test_send_email_via_smtp_simulation_mode(mocker) -> None:
    # Set SMTP_USER to empty to trigger simulation mode
    mocker.patch.object(settings, "smtp_user", "")
    
    sent = send_email_via_smtp("test@example.com", "Test Subject", "<html></html>")
    assert sent is False


def test_send_email_via_smtp_success_mode(mocker) -> None:
    # Setup SMTP credentials
    mocker.patch.object(settings, "smtp_user", "sender@gmail.com")
    mocker.patch.object(settings, "smtp_password", "password")
    
    # Mock smtplib.SMTP
    mock_smtp_class = mocker.patch("smtplib.SMTP")
    mock_smtp_instance = mock_smtp_class.return_value
    
    sent = send_email_via_smtp("recipient@example.com", "Test Subject", "<html></html>")
    
    assert sent is True
    mock_smtp_class.assert_called_once_with(settings.smtp_host, settings.smtp_port)
    mock_smtp_instance.starttls.assert_called_once()
    mock_smtp_instance.login.assert_called_once_with("sender@gmail.com", "password")
    mock_smtp_instance.sendmail.assert_called_once()
    mock_smtp_instance.close.assert_called_once()


def test_process_subscription_alert_timing(db_session: Session, mocker) -> None:
    # Subscribed 5 hours ago, alert sent 1 hour ago
    sub = EmailSubscription(
        name="Bob",
        email="bob@gmail.com",
        skills=["python"],
        last_sent_at=datetime.now(UTC) - timedelta(hours=1),
    )
    db_session.add(sub)
    db_session.commit()

    # We shouldn't process it as 23 hours haven't elapsed
    processed = process_subscription_alert(db_session, sub, force=False)
    assert processed is False

    # Force send should bypass timing check
    mocker.patch("src.orchestration.email_alerts.send_email_via_smtp", return_value=True)
    # Add a matching job to make sure it sends
    j = BronzeJob(
        id=10,
        url="http://x.com",
        title="Python Dev",
        company_name="Z",
        tags=["python"],
        publication_date=datetime.now(UTC),
        ingested_at=datetime.now(UTC),
    )
    db_session.add(j)
    db_session.commit()

    processed_forced = process_subscription_alert(db_session, sub, force=True)
    assert processed_forced is True
    assert sub.last_sent_at is not None
    last_sent_naive = sub.last_sent_at.replace(tzinfo=None) if sub.last_sent_at.tzinfo else sub.last_sent_at
    now_naive = datetime.now(UTC).replace(tzinfo=None)
    assert (now_naive - last_sent_naive) < timedelta(seconds=10)


def test_send_job_alerts_integration(db_session: Session, mocker) -> None:
    mocker.patch("src.orchestration.email_alerts.send_email_via_smtp", return_value=True)

    # Add active subscription
    sub1 = EmailSubscription(name="Sub1", email="sub1@gmail.com", active=True, skills=[])
    # Add inactive subscription
    sub2 = EmailSubscription(name="Sub2", email="sub2@gmail.com", active=False, skills=[])
    
    db_session.add_all([sub1, sub2])
    
    # Add one job
    j = BronzeJob(
        id=1,
        url="http://x.com",
        title="Any Job",
        company_name="A",
        tags=[],
        publication_date=datetime.now(UTC),
        ingested_at=datetime.now(UTC),
    )
    db_session.add(j)
    db_session.commit()

    sent_count = send_job_alerts(db_session, force=True)
    assert sent_count == 1
