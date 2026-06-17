from pathlib import Path


def test_cli_analyze_does_not_call_run_mcscan_directly() -> None:
    root = Path(__file__).resolve().parents[2]
    source = (root / "src" / "genomelens" / "cli" / "commands" / "analyze.py").read_text(encoding="utf-8")

    assert "run_mcscan" not in source
    assert "McscanRequest" not in source
