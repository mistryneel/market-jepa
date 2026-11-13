"""Pre-registration lock for the primary endpoint.

If this test fails you changed ``configs/endpoint.yaml``. That is allowed only while
``status: draft`` and only together with (1) a dated entry in
``docs/harness/DECISIONS.md`` explaining the change and (2) an update of the pin below
in the same commit. Once locked-test data has been read, the endpoint must not change.
"""

from __future__ import annotations

import re
from pathlib import Path

from mjepa_harness.config import fingerprint, load_harness_config

PREREGISTERED_ENDPOINT_FINGERPRINT = (
    "sha256:b68e9f2c88630c21abf005fded01788e00d5a0e95b6411c658e91a8c1f2c0036"
)

# The sentence from the project brief (section 1), verbatim.
BRIEF_STATEMENT = (
    "Mean out-of-sample Stein loss of 5-trading-day covariance forecasts (trading days 1 to 5 "
    "after the event) for the top 500 US stocks by prior-month dollar volume (price above $5, "
    "universe rebuilt monthly). It is taken across every scheduled FOMC and CPI announcement "
    "in the locked test period, paired by event, and compared with a block bootstrap across "
    "months."
)


def test_endpoint_fingerprint_matches_preregistration(config_dir: Path) -> None:
    endpoint = load_harness_config(config_dir).endpoint
    assert fingerprint(endpoint) == PREREGISTERED_ENDPOINT_FINGERPRINT, (
        "configs/endpoint.yaml changed; see this module's docstring before updating the pin"
    )


def test_statement_is_the_brief_verbatim(config_dir: Path) -> None:
    statement = load_harness_config(config_dir).endpoint.statement
    assert re.sub(r"\s+", " ", statement).strip() == BRIEF_STATEMENT
