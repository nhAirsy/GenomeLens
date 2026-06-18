"""shell workflow(外壳工作流) 的输入与选项校验"""

# region import
from __future__ import annotations

from pathlib import Path

from genomelens.app.errors.exceptions import InputValidationError
from genomelens.core.jcvi_adapter.adapter_models import McscanRequest
from genomelens.core.jcvi_adapter.command_mapping import SUPPORTED_WORKFLOWS, normalize_workflow
from genomelens.core.models import GenomeInputSpec

# endregion


def require_existing_file(path: Path, label: str) -> None:
    """校验路径指向已存在文件"""

    if not path.is_file():
        raise InputValidationError(f"{label} does not exist or is not a file: {path}")


def validate_genome_input(spec: GenomeInputSpec, label: str) -> None:
    """校验分析请求中的一个物种侧"""

    # prepared/raw 是互斥协议，normalizer 会尽量整理，这里再做最终硬校验。
    if bool(spec.prepared) == bool(spec.raw):
        raise InputValidationError(f"{label} must use exactly one input mode: bed_cds or gff_genome")
    if spec.prepared:
        require_existing_file(spec.prepared.bed, f"{label} BED")
        require_existing_file(spec.prepared.cds, f"{label} CDS")
    if spec.raw:
        require_existing_file(spec.raw.gff, f"{label} GFF/GTF")
        require_existing_file(spec.raw.genome, f"{label} genome FASTA")


def validate_request(request: McscanRequest) -> None:
    """校验完整 MCscan 请求"""

    species = request.species
    if len(species) < 2:
        raise InputValidationError("at least two species are required")
    names = [item.name for item in species]
    if len(set(names)) != len(names):
        raise InputValidationError("species names must be unique")
    for index, spec in enumerate(species, start=1):
        validate_genome_input(spec, f"species[{index}] {spec.name}")
    if request.threads < 1:
        raise InputValidationError("--threads must be >= 1")
    if request.min_block_size < 1:
        raise InputValidationError("--min-block-size must be >= 1")
    if normalize_workflow(request.jcvi_workflow) not in SUPPORTED_WORKFLOWS:
        raise InputValidationError(f"unsupported JCVI workflow: {request.jcvi_workflow}")
    if request.allow_simplified_fallback:
        raise InputValidationError("allow_simplified_fallback is not implemented for production JCVI workflows")
    for optional_path, label in [(request.jcvi_layout, "layout"), (request.jcvi_seqids, "seqids")]:
        if optional_path and not Path(optional_path).expanduser().is_file():
            raise InputValidationError(f"{label} path does not exist: {optional_path}")
    # 显式工具路径一旦给出，就要求其真实可用；否则后面 locator 的报错会更绕。
    for optional_path, label in [(request.blastn_path, "blastn"), (request.makeblastdb_path, "makeblastdb")]:
        if optional_path and not Path(optional_path).expanduser().is_file():
            raise InputValidationError(f"{label} path does not exist: {optional_path}")
