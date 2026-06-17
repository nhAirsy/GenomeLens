"""engine runtime(引擎运行时) 入口辅助模块"""

# region import
from __future__ import annotations

from pathlib import Path

from jcvi_genomelens.manifest_loader import load_manifest
from jcvi_genomelens.runtime.logging_utils import close_engine_logging, setup_engine_logging
from jcvi_genomelens.runtime.summary_writer import write_summary
from jcvi_genomelens.workflow_dispatcher import dispatch

# endregion


def run_manifest(manifest_path: str | Path, outdir: str | Path) -> Path:
    """运行 manifest(清单) 并写出 `engine_run_summary.json`"""

    root = Path(outdir).expanduser().resolve(strict=False)
    root.mkdir(parents=True, exist_ok=True)
    log_path = root / "run.log"
    logger = setup_engine_logging(log_path)
    workflow = "unknown"
    manifest = None
    try:
        # 先解析 manifest，再把 workflow 名称传播到日志和最终摘要。
        manifest = load_manifest(manifest_path)
        workflow = manifest.workflow
        logger.info("Running workflow %s", manifest.workflow)
        commands, artifacts = dispatch(manifest, root)
        return write_summary(
            root / "engine_run_summary.json",
            status="ok",
            workflow=manifest.workflow,
            commands=commands,
            artifacts=artifacts,
            logs={"run_log": str(log_path)},
            schema_version=manifest.schema_version,
            task=manifest.task,
            species=manifest.species,
            expected_outputs=manifest.expected_outputs,
            error=None,
        )
    except Exception as exc:
        logger.exception("Engine run failed")
        manifest_kwargs = {}
        if manifest is not None:
            # manifest 已可用时，失败摘要也尽量保留任务上下文，便于 shell 层复盘。
            manifest_kwargs = {
                "schema_version": manifest.schema_version,
                "task": manifest.task,
                "species": manifest.species,
                "expected_outputs": manifest.expected_outputs,
            }
        return write_summary(
            root / "engine_run_summary.json",
            status="failed",
            workflow=workflow,
            commands=[],
            artifacts={},
            logs={"run_log": str(log_path)},
            **manifest_kwargs,
            error={"type": exc.__class__.__name__, "message": str(exc)},
        )
    finally:
        close_engine_logging()
