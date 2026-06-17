from pathlib import Path

import pytest

from jcvi_genomelens.workflows.local_synteny import _extract_local_blocks


def test_single_unsplit_target_marks_gene_red(tmp_path: Path) -> None:
    blocks = tmp_path / "blocks.txt"
    blocks.write_text("qgene2\tsgene2\n", encoding="utf-8")

    local_blocks, covered = _extract_local_blocks(
        blocks,
        ["qgene1", "qgene2", "qgene3"],
        {"qgene1": 0, "qgene2": 1, "qgene3": 2},
        ["qgene2"],
        up=1,
        down=1,
        split_targets=False,
        query_label="query",
        subject_label="subject",
    )

    assert local_blocks == {"qgene2": ["r*qgene2\tsgene2"]}
    assert covered == {"qgene1", "qgene2", "qgene3"}


def test_window_keeps_non_target_rows_unmarked(tmp_path: Path) -> None:
    blocks = tmp_path / "blocks.txt"
    blocks.write_text("qgene1\tsgene1\nqgene2\tsgene2\nqgene3\tsgene3\n", encoding="utf-8")

    local_blocks, _ = _extract_local_blocks(
        blocks,
        ["qgene1", "qgene2", "qgene3"],
        {"qgene1": 0, "qgene2": 1, "qgene3": 2},
        ["qgene2"],
        up=1,
        down=1,
        split_targets=False,
        query_label="query",
        subject_label="subject",
    )

    assert local_blocks == {"qgene2": ["qgene1\tsgene1", "r*qgene2\tsgene2", "qgene3\tsgene3"]}


def test_single_unsplit_target_error_names_gene_not_merged(tmp_path: Path) -> None:
    blocks = tmp_path / "blocks.txt"
    blocks.write_text("qgene2\t.\n", encoding="utf-8")

    with pytest.raises(ValueError) as excinfo:
        _extract_local_blocks(
            blocks,
            ["qgene1", "qgene2", "qgene3"],
            {"qgene1": 0, "qgene2": 1, "qgene3": 2},
            ["qgene2"],
            up=1,
            down=1,
            split_targets=False,
            query_label="query",
            subject_label="subject",
        )

    message = str(excinfo.value)
    assert "qgene2" in message
    assert "merged" not in message
