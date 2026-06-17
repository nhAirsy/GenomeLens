"""shell(外壳) 侧分析的应用工作流控制器"""

# region import
from __future__ import annotations

from genomelens.analysis.request_models import (
    AnalysisConfigRef,
    AnalysisInput,
    AnalysisOptions,
    AnalysisOutput,
    AnalysisRequest,
    AnalysisSpeciesInput,
    McscanMethodConfig,
)
from genomelens.app.controller.orchestrator import WorkflowOrchestrator
from genomelens.app.controller.state_machine import WorkflowState
from genomelens.app.controller.workflow_provider import WorkflowProvider
from genomelens.app.events.signal_bus import SignalBus
from genomelens.core.jcvi_adapter.adapter_models import McscanRequest
from genomelens.core.models import GenomeInputSpec
from genomelens.core.summary_models import RunSummary

# endregion


def _species_to_analysis_input(species: GenomeInputSpec) -> AnalysisSpeciesInput:
    """把内部 GenomeInputSpec 转成 AnalysisSpeciesInput，供通用工作流使用"""

    if species.prepared:
        return AnalysisSpeciesInput(
            name=species.name,
            input_mode="bed_cds",
            bed=str(species.prepared.bed),
            cds=str(species.prepared.cds),
        )
    if species.raw:
        return AnalysisSpeciesInput(
            name=species.name,
            input_mode="gff_genome",
            gff=str(species.raw.gff),
            genome=str(species.raw.genome),
        )
    return AnalysisSpeciesInput(name=species.name, input_mode="unknown")


def _mcscan_request_to_analysis(request: McscanRequest) -> AnalysisRequest:
    """把旧版 McscanRequest 转成通用 AnalysisRequest，保留对 legacy 入口的兼容"""

    method_config = McscanMethodConfig(
        workflow=request.jcvi_workflow,
        jcvi_engine=request.jcvi_engine,
        blastn=request.blastn_path,
        makeblastdb=request.makeblastdb_path,
        jcvi_layout=request.jcvi_layout,
        jcvi_seqids=request.jcvi_seqids,
        allow_simplified_fallback=request.allow_simplified_fallback,
        align_soft=request.align_soft,
        dbtype=request.dbtype,
        cscore=request.cscore,
        dist=request.dist,
        iter=request.iter,
        target_gene_ids=list(request.target_gene_ids),
        up=request.up,
        down=request.down,
        split_targets=request.split_targets,
        label_targets=request.label_targets,
        glyphstyle=request.glyphstyle,
        glyphcolor=request.glyphcolor,
        shadestyle=request.shadestyle,
        figsize=request.figsize,
        dpi=request.dpi,
    )

    return AnalysisRequest(
        method="mcscan",
        input=AnalysisInput(
            mode="files",
            species=[_species_to_analysis_input(item) for item in request.species],
            reference_index=0,
        ),
        output=AnalysisOutput(
            directory=str(request.outdir),
            force=request.force,
            formats=list(request.formats),
        ),
        config=AnalysisConfigRef(),
        options=AnalysisOptions(
            preset="auto",
            threads=request.threads,
            min_block_size=request.min_block_size,
        ),
        method_config=method_config.to_json(),
    )


class WorkflowController:
    """WorkflowController(工作流控制器)：编排一次完整的 shell(外壳) 运行"""

    def __init__(self, signal_bus: SignalBus | None = None) -> None:
        self.signal_bus = signal_bus or SignalBus()
        self.state = WorkflowState.PENDING

    def _set_state(self, state: WorkflowState) -> None:
        self.state = state
        # 统一在状态切换点发事件，避免各 runner 自己重复维护 UI/日志通知逻辑
        self.signal_bus.emit("state", state=state.value)

    def run(self, request: AnalysisRequest, provider: WorkflowProvider) -> RunSummary:
        """根据请求与方法提供者编排执行"""

        self._set_state(WorkflowState.PENDING)
        orchestrator = WorkflowOrchestrator()
        result = orchestrator.run(request, provider, self.signal_bus)
        self._set_state(WorkflowState.SUCCEEDED if result.status == "SUCCEEDED" else WorkflowState.FAILED)
        return result

    def run_mcscan(self, request: McscanRequest) -> RunSummary:
        """兼容旧版 McscanRequest 入口：自动转换为通用 AnalysisRequest 后执行"""

        from genomelens.analysis.methods.mcscan_provider import McscanWorkflowProvider

        analysis_request = _mcscan_request_to_analysis(request)
        return self.run(analysis_request, McscanWorkflowProvider())
