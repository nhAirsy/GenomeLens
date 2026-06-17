"""把 manifest(清单) 分发到受支持的 workflows(工作流)"""

# region import
from __future__ import annotations

from pathlib import Path

from jcvi_genomelens.manifest_models import EngineRunManifest
from jcvi_genomelens.runtime.command_runner import CommandAudit
from jcvi_genomelens.workflow_contract import GLOBAL_KARYOTYPE_WORKFLOW, normalize_workflow
from jcvi_genomelens.workflows import (
    catalog_ortholog,
    graphics_dotplot,
    graphics_karyotype,
    graphics_karyotype_global,
    graphics_synteny,
    local_synteny,
    mcscan_pairwise,
)

# endregion


def dispatch(manifest: EngineRunManifest, outdir: str | Path) -> tuple[list[CommandAudit], dict[str, object]]:
    """分发 manifest(清单) 中的 workflow(工作流) 名称"""

    # 入口先做 workflow 名称归一化，兼容上层别名和历史写法。
    workflow = normalize_workflow(manifest.workflow)
    if workflow == "mcscan_pairwise":
        return mcscan_pairwise.run(manifest, outdir)
    if workflow == "graphics_synteny":
        return graphics_synteny.run(manifest, outdir)
    if workflow == "graphics_dotplot":
        return graphics_dotplot.run(manifest, outdir)
    if workflow == "graphics_karyotype":
        return graphics_karyotype.run(manifest, outdir)
    if workflow == "catalog_ortholog":
        return catalog_ortholog.run(manifest, outdir)
    if workflow == "local_synteny":
        return local_synteny.run(manifest, outdir)
    if workflow == GLOBAL_KARYOTYPE_WORKFLOW:
        return graphics_karyotype_global.run(manifest, outdir)
    raise ValueError(f"Unsupported workflow: {manifest.workflow}")
