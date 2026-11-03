"""Intentionally failing test to show the CI pipeline stops on a broken build.

Delete this file after taking the evidence screenshot.
"""

import pandas as pd

from app.sandbox.executor import run_generated_code


def test_falla_intencional_dropna():
    # dropna() removes the row with a null value, so 2 rows remain.
    # The expected value is wrong on purpose (3) so the pipeline fails.
    df = pd.DataFrame({"edad": [20, None, 30]})
    result = run_generated_code("df = df.dropna()", df)
    assert len(result.df) == 3
