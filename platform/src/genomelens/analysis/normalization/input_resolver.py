"""input_resolver(输入解析器)：目录发现与文件配对"""

# region import
from __future__ import annotations

from pathlib import Path

from genomelens.analysis.request_models import AnalysisSpeciesInput
from genomelens.app.errors import messages
from genomelens.app.errors.exceptions import InputValidationError

# endregion


def _path(value: str) -> Path:
    return Path(value).expanduser().resolve(strict=False)


def _path_text(value: str) -> str:
    return str(_path(value)) if value else ""


def _stemmed_files(input_dir: Path, suffixes: set[str]) -> dict[str, Path]:
    files: dict[str, Path] = {}
    for path in sorted(input_dir.iterdir()):
        if not path.is_file():
            continue

        lower_name = path.name.lower()

        # 后缀按长度倒序匹配，避免 `.cds.fa` 被较短的 `.fa` 提前吞掉
        matched = next(
            (suffix for suffix in sorted(suffixes, key=len, reverse=True) if lower_name.endswith(suffix)),
            "",
        )
        if matched:
            files[path.name[: -len(matched)]] = path
    return files


def discover_species_from_directory(input_dir: str | Path) -> list[AnalysisSpeciesInput]:
    """从目录自动发现同名物种输入文件对"""

    root = Path(input_dir).expanduser().resolve(strict=False)
    if not root.is_dir():
        raise InputValidationError(messages.INPUT_DIRECTORY_NOT_FOUND.format(path=root))

    beds = _stemmed_files(root, {".bed"})
    cds_files = _stemmed_files(root, {".cds", ".cds.fa", ".cds.fasta", ".pep", ".pep.fa", ".pep.fasta", ".faa"})

    prepared = {
        name: AnalysisSpeciesInput(
            name=name,
            input_mode="bed_cds",
            bed=str(bed),
            cds=str(cds_files[name]),
        )
        for name, bed in beds.items()
        if name in cds_files
    }

    gffs = _stemmed_files(root, {".gff", ".gff3", ".gtf"})
    genomes = _stemmed_files(root, {".fa", ".fasta", ".fna"})
    raw = {
        name: AnalysisSpeciesInput(
            name=name,
            input_mode="gff_genome",
            gff=str(gff),
            genome=str(genomes[name]),
        )
        for name, gff in gffs.items()
        if name in genomes
    }

    # 同一物种同时存在 prepared/raw 时优先使用已经准备好的 BED+CDS/PEP。
    species_by_name = {**raw, **prepared}
    species = [species_by_name[name] for name in sorted(species_by_name)]
    if len(species) < 2:
        raise InputValidationError(messages.INPUT_TOO_FEW_SPECIES)
    return species
