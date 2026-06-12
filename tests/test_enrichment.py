from __future__ import annotations

from src.transformation.runner import _classify_seniority, _parse_salary


def test_classify_seniority() -> None:
    # Test Lead keyword
    assert _classify_seniority("Lead Python Engineer", None) == "Lead"
    assert _classify_seniority("Principal Data Scientist", None) == "Lead"
    
    # Test Senior keyword
    assert _classify_seniority("Senior Software Engineer", None) == "Senior"
    assert _classify_seniority("Sr. Developer", None) == "Senior"
    
    # Test Junior keyword
    assert _classify_seniority("Junior Data Analyst", None) == "Junior"
    assert _classify_seniority("Frontend Intern", None) == "Junior"
    
    # Test Mid-level default
    assert _classify_seniority("Database Administrator", None) == "Mid-level"


def test_parse_salary_from_string() -> None:
    # Test standard ranges in USD
    assert _parse_salary("$120k - $160k", None) == (120000.0, 160000.0, "USD")
    assert _parse_salary("100,000 - 130,000", None) == (100000.0, 130000.0, "USD")
    
    # Test currencies
    assert _parse_salary("£40k - £60k", None) == (40000.0, 60000.0, "GBP")
    assert _parse_salary("€80,000 - €95,000", None) == (80000.0, 95000.0, "EUR")
    
    # Test single value
    assert _parse_salary("$110k", None) == (110000.0, 110000.0, "USD")


def test_parse_salary_from_description() -> None:
    # Test falling back to description
    desc = "We offer a flexible schedule and a salary range of $130,000 to $170,000 per year."
    assert _parse_salary(None, desc) == (130000.0, 170000.0, "USD")
    
    # Test hourly rate conversion
    desc_hourly = "The hourly pay rate is $50 - $70/hr depending on experience."
    assert _parse_salary(None, desc_hourly) == (100000.0, 140000.0, "USD")
