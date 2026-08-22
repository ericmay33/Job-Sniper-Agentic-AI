"""Scaffolding smoke test.

Exists so `uv run pytest` collects something — an empty run exits 5, which reads
as a failure. Replaced by real tests as stages land.
"""

import jobsniper
from jobsniper import cli


def test_package_exposes_version():
    assert jobsniper.__version__


def test_cli_runs_with_no_args(capsys):
    assert cli.main([]) == 0
    assert "jobsniper" in capsys.readouterr().out
