"""测试 McscanMethodConfig -> McscanRequest 的字段映射层。"""

from pathlib import Path

import pytest

from genomelens.analysis.methods.mcscan_request_mapping import (
    _map_method_config_to_request,
    to_mcscan_request,
)
from genomelens.analysis.request_models import (
    AnalysisInput,
    AnalysisOptions,
    AnalysisOutput,
    AnalysisRequest,
    AnalysisSpeciesInput,
    McscanMethodConfig,
)
from genomelens.app.errors.exceptions import InputValidationError
from genomelens.data.config.config_models import (
    ConfigModel,
    LocalSyntenyDefaults,
    McscanDefaults,
    RuntimeDefaults,
    ToolchainConfig,
    WorkspaceConfig,
)


def test_map_method_config_to_request_field_names() -> None:
    """映射层应把 method_config 字段名转成 McscanRequest 字段名。"""

    method_config = McscanMethodConfig(
        workflow="graphics_synteny",
        jcvi_engine="/custom/jcvi",
        blastn="/custom/blastn",
        makeblastdb="/custom/makeblastdb",
        align_soft="blast",
        dbtype="nucl",
        cscore=0.8,
        dist=10,
        iter=2,
        target_gene_ids=["g1", "g2"],
        up=15,
        down=25,
        split_targets=True,
        label_targets=True,
        glyphstyle="arrow",
        glyphcolor="orthogroup",
        shadestyle="curve",
        figsize="12x6",
        dpi=600,
    )
    config = ConfigModel(
        workspace=WorkspaceConfig(
            workspace_root="/tmp/ws",
            temp_root="/tmp/ws/temp",
            default_output_root="/tmp/ws/out",
        ),
        runtime=RuntimeDefaults(),
        mcscan=McscanDefaults(),
        local_synteny=LocalSyntenyDefaults(),
        toolchain=ToolchainConfig(
            jcvi_engine_path="/config/jcvi",
            blastn_path="/config/blastn",
            makeblastdb_path="/config/makeblastdb",
        ),
    )

    mapped = _map_method_config_to_request(method_config, config)

    # CLI 显式值应覆盖配置中的 fallback
    assert mapped["jcvi_engine"] == "/custom/jcvi"
    assert mapped["blastn_path"] == "/custom/blastn"
    assert mapped["makeblastdb_path"] == "/custom/makeblastdb"
    assert mapped["jcvi_workflow"] == "graphics_synteny"
    # 其它字段原样传递
    assert mapped["align_soft"] == "blast"
    assert mapped["dbtype"] == "nucl"
    assert mapped["cscore"] == 0.8
    assert mapped["dist"] == 10
    assert mapped["iter"] == 2
    assert mapped["target_gene_ids"] == ["g1", "g2"]
    assert mapped["up"] == 15
    assert mapped["down"] == 25
    assert mapped["split_targets"] is True
    assert mapped["label_targets"] is True
    assert mapped["glyphstyle"] == "arrow"
    assert mapped["glyphcolor"] == "orthogroup"
    assert mapped["shadestyle"] == "curve"
    assert mapped["figsize"] == "12x6"
    assert mapped["dpi"] == 600


def test_map_method_config_uses_toolchain_fallback() -> None:
    """当 method_config 没有显式值时，应回退到 config.toolchain。"""

    method_config = McscanMethodConfig(workflow="graphics_synteny")
    config = ConfigModel(
        workspace=WorkspaceConfig(
            workspace_root="/tmp/ws",
            temp_root="/tmp/ws/temp",
            default_output_root="/tmp/ws/out",
        ),
        runtime=RuntimeDefaults(),
        mcscan=McscanDefaults(),
        local_synteny=LocalSyntenyDefaults(),
        toolchain=ToolchainConfig(
            jcvi_engine_path="/config/jcvi",
            blastn_path="/config/blastn",
            makeblastdb_path="/config/makeblastdb",
            lastal_path="/config/lastal",
            lastdb_path="/config/lastdb",
        ),
    )

    mapped = _map_method_config_to_request(method_config, config)

    assert mapped["jcvi_engine"] == "/config/jcvi"
    assert mapped["blastn_path"] == "/config/blastn"
    assert mapped["makeblastdb_path"] == "/config/makeblastdb"
    assert mapped["lastal_path"] == "/config/lastal"
    assert mapped["lastdb_path"] == "/config/lastdb"


def test_to_mcscan_request_applies_mapping() -> None:
    """to_mcscan_request 应通过映射层正确构造 McscanRequest。"""

    request = AnalysisRequest(
        method="mcscan",
        input=AnalysisInput(
            mode="auto_directory",
            directory="/tmp/in",
            species=[
                AnalysisSpeciesInput(
                    name="query",
                    input_mode="bed_cds",
                    bed="/tmp/in/query.bed",
                    cds="/tmp/in/query.cds",
                ),
                AnalysisSpeciesInput(
                    name="subject",
                    input_mode="bed_cds",
                    bed="/tmp/in/subject.bed",
                    cds="/tmp/in/subject.cds",
                ),
            ],
            reference_index=1,
        ),
        output=AnalysisOutput(
            directory="/tmp/out",
            force=True,
            formats=["png"],
        ),
        options=AnalysisOptions(
            preset="auto",
            threads=4,
            min_block_size=1,
        ),
        method_config=McscanMethodConfig(
            workflow="graphics_synteny",
            blastn="/custom/blastn",
        ).to_json(),
    )

    mcscan_request = to_mcscan_request(request)

    assert mcscan_request.query.name == "subject"
    assert mcscan_request.subject.name == "query"
    assert mcscan_request.outdir == Path("/tmp/out").expanduser().resolve(strict=False)
    assert mcscan_request.force is True
    assert mcscan_request.jcvi_workflow == "graphics_synteny"
    assert mcscan_request.blastn_path == "/custom/blastn"
    # 未显式提供时回退为空字符串
    assert mcscan_request.jcvi_engine == ""


def test_to_mcscan_request_requires_at_least_two_species() -> None:
    request = AnalysisRequest(
        method="mcscan",
        input=AnalysisInput(
            mode="auto_directory",
            directory="/tmp/in",
            species=[
                AnalysisSpeciesInput(
                    name="query",
                    input_mode="bed_cds",
                    bed="/tmp/in/query.bed",
                    cds="/tmp/in/query.cds",
                ),
            ],
            reference_index=0,
        ),
        output=AnalysisOutput(directory="/tmp/out"),
    )

    with pytest.raises(InputValidationError, match="mcscan 至少需要两个物种"):
        to_mcscan_request(request)


def test_to_mcscan_request_rejects_target_genes_missing_from_reference_bed(tmp_path: Path) -> None:
    """目标基因 ID 不在参考物种 BED 中时应给出明确的参考物种提示"""

    bed = tmp_path / "ref.bed"
    bed.write_text("chr1\t1\t100\tg1\t+\nchr1\t101\t200\tg2\t+\n", encoding="utf-8")
    cds = tmp_path / "ref.cds"
    cds.write_text(">g1\nATGC\n", encoding="utf-8")

    request = AnalysisRequest(
        method="mcscan",
        input=AnalysisInput(
            mode="auto_directory",
            directory=str(tmp_path),
            species=[
                AnalysisSpeciesInput(
                    name="ref",
                    input_mode="bed_cds",
                    bed=str(bed),
                    cds=str(cds),
                ),
                AnalysisSpeciesInput(
                    name="subject",
                    input_mode="bed_cds",
                    bed=str(tmp_path / "subject.bed"),
                    cds=str(tmp_path / "subject.cds"),
                ),
            ],
            reference_index=0,
        ),
        output=AnalysisOutput(directory=str(tmp_path / "out")),
        method_config=McscanMethodConfig(
            workflow="graphics_synteny",
            target_gene_ids=["missing_gene"],
        ).to_json(),
    )

    with pytest.raises(InputValidationError, match="参考物种") as exc_info:
        to_mcscan_request(request)
    assert "missing_gene" in str(exc_info.value)
    assert "ref" in str(exc_info.value)
