from pathlib import Path

from genomelens.data.workspace.output_layout import create_output_layout


def test_output_layout_names(tmp_path: Path) -> None:
    layout = create_output_layout(tmp_path / "run")
    assert layout.manifest.name == "jcvi_engine_manifest.json"
    assert layout.engine_summary.name == "engine_run_summary.json"
    assert layout.run_summary.name == "run_summary.json"
    assert layout.figures.is_dir()
