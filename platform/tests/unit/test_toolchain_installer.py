import tarfile
import zipfile
from pathlib import Path

import pytest

from genomelens.toolchain.runtime.toolchain_installer import (
    _find_child_with_files,
    _safe_extract_tar,
    _safe_extract_zip,
)


def test_find_child_with_files_ignores_missing_bin_dirs(tmp_path: Path) -> None:
    (tmp_path / "empty-child").mkdir()
    bin_dir = tmp_path / "ncbi-blast" / "bin"
    bin_dir.mkdir(parents=True)
    (bin_dir / "blastn.exe").touch()
    (bin_dir / "makeblastdb.exe").touch()

    assert _find_child_with_files(tmp_path, ["blastn.exe", "makeblastdb.exe"]) == tmp_path / "ncbi-blast"


def test_find_child_with_files_supports_files_at_candidate_root(tmp_path: Path) -> None:
    candidate = tmp_path / "ImageMagick"
    candidate.mkdir()
    (candidate / "magick.exe").touch()

    assert _find_child_with_files(tmp_path, ["magick.exe"]) == candidate


def test_safe_extract_zip_rejects_path_traversal(tmp_path: Path) -> None:
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as zip_handle:
        zip_handle.writestr("../evil.txt", "bad")

    with pytest.raises(RuntimeError):
        _safe_extract_zip(archive, tmp_path / "extract")


def test_safe_extract_tar_rejects_path_traversal(tmp_path: Path) -> None:
    archive = tmp_path / "bad.tar.gz"
    payload = tmp_path / "payload.txt"
    payload.write_text("bad", encoding="utf-8")
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(payload, arcname="../evil.txt")

    with pytest.raises(RuntimeError):
        _safe_extract_tar(archive, tmp_path / "extract")
