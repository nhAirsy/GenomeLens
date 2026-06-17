"""Public workflow names and aliases shared across engine entrypoints"""

# region import
from __future__ import annotations

# endregion


# 全局多物种核型总图工作流：把已算好的 pairwise tracks/edges 渲染为一张总图


GLOBAL_KARYOTYPE_WORKFLOW = "graphics_karyotype_global"

SUPPORTED_WORKFLOWS = (
    "mcscan_pairwise",
    "graphics_synteny",
    "graphics_dotplot",
    "graphics_karyotype",
    "catalog_ortholog",
    "local_synteny",
    GLOBAL_KARYOTYPE_WORKFLOW,
)

WORKFLOW_ALIASES = {
    "dotplot": "graphics_dotplot",
    "karyotype": "graphics_karyotype",
    "karyotype_global": GLOBAL_KARYOTYPE_WORKFLOW,
    "local": "local_synteny",
}


def normalize_workflow(name: str) -> str:
    """Normalize compatible workflow aliases to their public names"""

    # shell、配置和 engine 都通过这里收敛别名，避免各处维护一份映射。
    return WORKFLOW_ALIASES.get(name, name)
