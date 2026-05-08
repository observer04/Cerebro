import pytest
from pydantic import ValidationError

from app.models.rca import RCAIn


def test_rca_missing_root_cause() -> None:
    with pytest.raises(ValidationError):
        RCAIn(
            root_cause="too short",
            mitigation="Restarted service",
            prevention="Add monitoring",
            submitted_by="oncall@corp.com",
        )


def test_rca_missing_mitigation() -> None:
    with pytest.raises(ValidationError):
        RCAIn(
            root_cause="This root cause is long enough",
            mitigation="",
            prevention="Add monitoring",
            submitted_by="oncall@corp.com",
        )


def test_rca_invalid_email_rejected() -> None:
    with pytest.raises(ValidationError):
        RCAIn(
            root_cause="This root cause is long enough",
            mitigation="Restarted service",
            prevention="Add monitoring",
            submitted_by="not-an-email",
        )


def test_valid_rca_accepted() -> None:
    rca = RCAIn(
        root_cause="Connection pool exhausted due to leak in service",
        mitigation="Restarted service and increased pool size",
        prevention="Add pool monitoring and fix leak",
        submitted_by="oncall@corp.com",
    )

    assert rca.root_cause.startswith("Connection pool")
