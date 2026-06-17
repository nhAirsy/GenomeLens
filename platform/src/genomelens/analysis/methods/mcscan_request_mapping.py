"""mcscan 请求映射：把 AnalysisRequest 转换为 McscanRequest"""

# region import
from __future__ import annotations

from pathlib import Path
from typing import Any

from genomelens.analysis.request_models import (
    AnalysisRequest,
    AnalysisSpeciesInput,
    McscanMethodConfig,
)
from genomelens.app.errors import messages
from genomelens.app.errors.exceptions import InputValidationError
from genomelens.core.jcvi_adapter.adapter_models import McscanRequest
from genomelens.core.models import (
    GenomeInputSpec,
    PreparedGenomeInputSpec,
    RawAnnotationInputSpec,
)
from genomelens.data.config.config_models import ConfigModel

# endregion


def _configured(value: str, fallback: str) -> str:
    """在显式值与回退值之间选择非空字符串"""

    return value if str(value).strip() else fallback


def _path(value: str) -> Path:
    """把字符串解析为已展开用户目录的 Path"""

    return Path(value).expanduser().resolve(strict=False)


def _species_to_genome_input(species: AnalysisSpeciesInput) -> GenomeInputSpec:
    """把 AnalysisSpeciesInput 转成内部 GenomeInputSpec"""

    if species.input_mode == "bed_cds":
        return GenomeInputSpec(
            name=species.name,
            prepared=PreparedGenomeInputSpec(_path(species.bed), _path(species.cds)),
        )
    if species.input_mode == "gff_genome":
        return GenomeInputSpec(
            name=species.name,
            raw=RawAnnotationInputSpec(_path(species.gff), _path(species.genome)),
        )
    raise ValueError(f"不支持的物种输入模式：{species.input_mode}")


def _read_bed_accns(bed_path: Path) -> set[str]:
    """读取 BED 文件第 4 列的 accn 集合"""

    accns: set[str] = set()
    with bed_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 4:
                continue
            accns.add(parts[3].strip())
    return accns


def _validate_target_genes_in_reference(
    request: AnalysisRequest,
    ref_index: int,
    target_gene_ids: list[str],
) -> None:
    """在请求阶段尽早发现目标基因与参考物种不匹配的问题"""

    if not target_gene_ids:
        return
    if not (0 <= ref_index < len(request.input.species)):
        return

    reference_input = request.input.species[ref_index]
    if reference_input.input_mode != "bed_cds" or not reference_input.bed:
        return

    bed_path = _path(reference_input.bed)
    if not bed_path.is_file():
        return

    accns = _read_bed_accns(bed_path)
    if not any(gene.strip() in accns for gene in target_gene_ids):
        raise InputValidationError(
            messages.LOCAL_SYNTENY_TARGET_GENES_NOT_IN_REFERENCE.format(
                genes=", ".join(target_gene_ids),
                reference=reference_input.name,
            )
        )


def _map_method_config_to_request(
    method_config: McscanMethodConfig,
    config: ConfigModel | None,
) -> dict[str, Any]:
    """把 McscanMethodConfig + ConfigModel 映射成 McscanRequest 构造参数子集

    这是当前唯一的显式跨层字段映射层：method_config/ConfigModel 的字段名
    与 McscanRequest 不同（如 blastn -> blastn_path），所有转换集中在这里，
    避免在多个地方散落。
    """

    toolchain = config.toolchain if config else None
    mapped: dict[str, Any] = {
        # 显式路径优先于配置，避免开发机硬编码路径泄漏到生产环境
        "jcvi_engine": _configured(method_config.jcvi_engine, toolchain.jcvi_engine_path if toolchain else ""),
        "blastn_path": _configured(method_config.blastn, toolchain.blastn_path if toolchain else ""),
        "makeblastdb_path": _configured(method_config.makeblastdb, toolchain.makeblastdb_path if toolchain else ""),
        "lastal_path": _configured("", toolchain.lastal_path if toolchain else ""),
        "lastdb_path": _configured("", toolchain.lastdb_path if toolchain else ""),
        # 工作流与布局决定 JCVI 执行哪条分析路径及参考-目标配对方式
        "jcvi_workflow": method_config.workflow,
        "jcvi_layout": method_config.jcvi_layout,
        "jcvi_seqids": method_config.jcvi_seqids,
        "allow_simplified_fallback": method_config.allow_simplified_fallback,
        # 这些参数直接影响 JCVI scan 的锚点密度与 block 过滤
        "align_soft": method_config.align_soft,
        "dbtype": method_config.dbtype,
        "cscore": method_config.cscore,
        "dist": method_config.dist,
        "iter": method_config.iter,
        # 仅在 target_gene_ids 非空时生效，控制目标基因上下游截取窗口
        "target_gene_ids": list(method_config.target_gene_ids),
        "up": method_config.up,
        "down": method_config.down,
        "split_targets": method_config.split_targets,
        "label_targets": method_config.label_targets,
        # 透传给 JCVI graphics 层，影响最终渲染风格
        "glyphstyle": method_config.glyphstyle,
        "glyphcolor": method_config.glyphcolor,
        "shadestyle": method_config.shadestyle,
        "figsize": method_config.figsize,
        "dpi": method_config.dpi,
    }
    return mapped


def to_mcscan_request(request: AnalysisRequest) -> McscanRequest:
    """把 AnalysisRequest(分析请求) 转为现有 McscanRequest(共线性请求)"""

    from genomelens.analysis.request_normalizer import read_request_config

    config = read_request_config(request)
    species = [_species_to_genome_input(item) for item in request.input.species]
    if len(species) < 2:
        raise InputValidationError(messages.REQUEST_TOO_FEW_SPECIES)

    ref_index = request.input.reference_index
    if not (0 <= ref_index < len(species)):
        raise InputValidationError(messages.REQUEST_REFERENCE_INDEX_OUT_OF_RANGE.format(index=ref_index))

    # AnalysisRequest 使用 species[] + reference_index，旧执行层仍消费 query/subject + additional_species
    reference = species[ref_index]
    targets = species[:ref_index] + species[ref_index + 1 :]
    options = request.options
    method_config = McscanMethodConfig.from_json(request.method_config)
    mapped = _map_method_config_to_request(method_config, config)
    _validate_target_genes_in_reference(request, ref_index, list(method_config.target_gene_ids))
    return McscanRequest(
        query=reference,
        subject=targets[0],
        additional_species=targets[1:],
        outdir=_path(request.output.directory),
        force=bool(request.output.force),
        threads=int(options.threads if options.threads is not None else 4),
        min_block_size=int(options.min_block_size if options.min_block_size is not None else 5),
        formats=request.output.formats,
        **mapped,
    )
