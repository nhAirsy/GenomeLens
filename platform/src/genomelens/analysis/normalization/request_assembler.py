"""request_assembler(请求组装器)：把解析后的输入/选项组装成 AnalysisRequest"""

# region import
from __future__ import annotations

import argparse

from genomelens.analysis.normalization.input_resolver import _path_text, discover_species_from_directory
from genomelens.analysis.normalization.option_merger import (
    _align_soft,
    _cscore,
    _dbtype,
    _dist,
    _down,
    _dpi,
    _formats,
    _iter,
    _label_targets,
    _min_block_size,
    _split_targets,
    _style_arg,
    _target_gene_ids,
    _threads,
    _up,
    _workflow,
)
from genomelens.analysis.normalization.reference_resolver import (
    _reference,
    _resolve_jcvi_config,
    _resolve_reference_index,
)
from genomelens.analysis.request_models import (
    AnalysisConfigRef,
    AnalysisInput,
    AnalysisOptions,
    AnalysisOutput,
    AnalysisRequest,
    McscanMethodConfig,
)
from genomelens.app.errors.exceptions import InputValidationError
from genomelens.data.config.config_models import ConfigModel
from genomelens.data.config.config_store import read_optional_config

# endregion


def read_request_config(request: AnalysisRequest) -> ConfigModel | None:
    """读取 request(请求) 引用的配置文件"""

    return read_optional_config(
        request.config.project_config,
        jcvi_config_path=request.config.method_config,
    )


def _build_mcscan_method_config(args: argparse.Namespace, config: ConfigModel | None) -> McscanMethodConfig:
    """根据 CLI 和配置构建 McscanMethodConfig"""

    # CLI 原始参数和 config 默认值会在这里收口成 method_config，后续 adapter 不再回头读 argparse
    return McscanMethodConfig(
        workflow=_workflow(args, config),
        jcvi_engine=args.jcvi_engine,
        blastn=args.blastn,
        makeblastdb=args.makeblastdb,
        jcvi_layout=args.jcvi_layout,
        jcvi_seqids=args.jcvi_seqids,
        allow_simplified_fallback=bool(args.allow_simplified_fallback),
        align_soft=_align_soft(args, config),
        dbtype=_dbtype(args, config),
        cscore=_cscore(args, config),
        dist=_dist(args, config),
        iter=_iter(args, config),
        target_gene_ids=_target_gene_ids(args, config),
        up=_up(args, config),
        down=_down(args, config),
        split_targets=_split_targets(args, config),
        label_targets=_label_targets(args, config),
        glyphstyle=_style_arg(args, config, "glyphstyle"),
        glyphcolor=_style_arg(args, config, "glyphcolor"),
        shadestyle=_style_arg(args, config, "shadestyle"),
        figsize=_style_arg(args, config, "figsize"),
        dpi=_dpi(args, config),
    )


def mcscan_auto_request_from_cli(args: argparse.Namespace) -> AnalysisRequest:
    """把 `analyze mcscan` CLI 参数转成 AnalysisRequest(分析请求)"""

    jcvi_config_path = _resolve_jcvi_config(args)
    config_ref = AnalysisConfigRef(project_config=args.config, method_config=jcvi_config_path)

    # 先用最小 request 读取配置文件，避免在目录发现前重复手写同一套优先级逻辑
    base_request = AnalysisRequest(
        method="mcscan",
        input=AnalysisInput(mode="auto_directory"),
        output=AnalysisOutput(directory=""),
        config=config_ref,
    )
    config = read_request_config(base_request)

    input_dir = _path_text(args.input_dir)
    discovered = discover_species_from_directory(input_dir)
    reference_index = _resolve_reference_index(_reference(args, config), discovered)
    analysis_input = AnalysisInput(
        mode="auto_directory",
        directory=input_dir,
        species=discovered,
        reference_index=reference_index,
    )
    return AnalysisRequest(
        method="mcscan",
        input=analysis_input,
        output=AnalysisOutput(
            directory=_path_text(args.output_dir),
            force=bool(args.force),
            formats=_formats(args, config),
        ),
        config=config_ref,
        options=AnalysisOptions(
            preset="auto",
            threads=_threads(args, config),
            min_block_size=_min_block_size(args, config),
        ),
        method_config=_build_mcscan_method_config(args, config).to_json(),
    )


def normalize_analysis_request(request: AnalysisRequest) -> AnalysisRequest:
    """补齐 request(请求) 中可推导的输入字段"""

    if request.method != "mcscan":
        return request
    if request.input.mode != "auto_directory" or request.input.species:
        return request
    if not request.input.directory:
        raise InputValidationError("auto_directory request 缺少 input.directory")

    # 外部入口只要给出目录，就在这里补齐 species[]，让后续 dispatcher 总是消费完整请求
    return AnalysisRequest(
        method=request.method,
        input=AnalysisInput(
            mode=request.input.mode,
            directory=_path_text(request.input.directory),
            species=discover_species_from_directory(request.input.directory),
            reference_index=request.input.reference_index,
        ),
        output=request.output,
        config=request.config,
        options=request.options,
        method_config=request.method_config,
        schema_version=request.schema_version,
        kind=request.kind,
    )


def mcscan_template_request() -> AnalysisRequest:
    """返回 mcscan 方法的 request(JSON 请求) 模板"""

    return AnalysisRequest(
        method="mcscan",
        input=AnalysisInput(
            mode="auto_directory",
            directory="input",
            species=[],
        ),
        output=AnalysisOutput(
            directory="output",
            force=False,
            formats=["png"],
        ),
        config=AnalysisConfigRef(
            project_config="workspace/genomelens.config.json",
            method_config="workspace/jcvi.config.json",
        ),
        options=AnalysisOptions(
            preset="auto",
            threads=None,
            min_block_size=None,
        ),
        method_config=McscanMethodConfig(workflow="graphics_synteny").to_json(),
    )
