"""外部 jcvi-genomelens engine adapter(引擎适配器)

模块职责：
- probe(探测) engine(引擎)。
- 写出 manifest(跨层协议)。
- 调用 engine run(引擎运行)。
- 解析 `engine_run_summary.json`。

关键约束：
- 这里不 import(导入) `jcvi`。
- 所有调用都通过外部进程完成。"""

# region import
from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from genomelens._version import __version__
from genomelens.app.errors.exceptions import EngineProbeError, EngineRunError, SummaryParseError
from genomelens.core.jcvi_adapter.adapter_models import JcviRunResult, McscanRequest
from genomelens.core.jcvi_adapter.command_mapping import normalize_workflow
from genomelens.core.jcvi_adapter.path_patch import absolute_path
from genomelens.core.models import GenomeInputSpec, PreparedGenomeInputSpec
from genomelens.toolchain.runtime.subprocess_runner import run_command

# endregion


def _ensure_prepared(value: PreparedGenomeInputSpec | None, label: str) -> PreparedGenomeInputSpec:
    if value is None:
        raise EngineRunError(f"{label} input was not prepared before manifest creation")
    return value


def _species_manifest_entry(
    species: GenomeInputSpec,
    role: str,
    prepared: PreparedGenomeInputSpec,
) -> dict[str, object]:
    # species[] 是公开协议的一部分，即便 engine 实际仍只消费 query/subject，也保留统一字段
    return {
        "name": species.name,
        "role": role,
        "input_mode": species.mode,
        "bed": absolute_path(prepared.bed),
        "cds": absolute_path(prepared.cds),
    }


class JcviEngineAdapter:
    """JcviEngineAdapter(engine 适配器)：唯一合法的 shell-to-engine(外壳到引擎) 门面"""

    def __init__(self, engine_path: str | Path):
        self.engine_path = str(engine_path)

    def probe(self) -> dict[str, object]:
        """运行 engine probe(引擎探测) 并解析 JSON 输出"""

        result = run_command([self.engine_path, "probe", "--json"], timeout=120)
        if not result.ok:
            raise EngineProbeError(result.stderr or result.stdout or f"probe failed: {result.returncode}")
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise EngineProbeError(f"probe did not return JSON: {result.stdout}") from exc
        if payload.get("status") != "ok":
            raise EngineProbeError(f"engine probe status is not ok: {payload}")
        return payload

    def build_manifest(
        self,
        request: McscanRequest,
        *,
        query: PreparedGenomeInputSpec,
        subject: PreparedGenomeInputSpec,
        blastn_path: str,
        makeblastdb_path: str,
        lastal_path: str = "",
        lastdb_path: str = "",
    ) -> dict[str, object]:
        """构建公开 engine manifest(引擎清单)"""

        workflow = normalize_workflow(request.jcvi_workflow)
        task = request.task_spec

        # toolchain 与 options 会跨进程传给 engine，因此这里使用公开协议字段名而不是内部对象名
        toolchain: dict[str, object] = {
            "blastn": absolute_path(blastn_path),
            "makeblastdb": absolute_path(makeblastdb_path),
        }
        if request.align_soft == "last":
            toolchain["lastal"] = absolute_path(lastal_path)
            toolchain["lastdb"] = absolute_path(lastdb_path)
        options: dict[str, object] = {
            "threads": request.threads,
            "min_block_size": request.min_block_size,
            "formats": request.formats,
            "layout": absolute_path(request.jcvi_layout),
            "seqids": absolute_path(request.jcvi_seqids),
            "allow_simplified_fallback": request.allow_simplified_fallback,
            "align_soft": request.align_soft,
            "dbtype": request.dbtype,
            "cscore": request.cscore,
            "dist": request.dist,
            "iter": request.iter,
            "target_gene_ids": list(request.target_gene_ids),
            "up": request.up,
            "down": request.down,
            "split_targets": request.split_targets,
            "label_targets": request.label_targets,
            "glyphstyle": request.glyphstyle,
            "glyphcolor": request.glyphcolor,
            "shadestyle": request.shadestyle,
            "figsize": request.figsize,
            "dpi": request.dpi,
        }
        return {
            "schema_version": 2,
            "workflow": workflow,
            "task": {
                # task_spec 里的 workflow 需要与规范化后的公开 workflow 名保持一致
                **task.to_manifest_json(),
                "workflow": workflow,
            },
            "species": [
                _species_manifest_entry(request.query, "query", query),
                _species_manifest_entry(request.subject, "subject", subject),
            ],
            "query": {
                "name": request.query.name,
                "bed": absolute_path(query.bed),
                "cds": absolute_path(query.cds),
            },
            "subject": {
                "name": request.subject.name,
                "bed": absolute_path(subject.bed),
                "cds": absolute_path(subject.cds),
            },
            "toolchain": toolchain,
            "options": options,
            "expected_outputs": ["blast_table", "anchors", "simple", "blocks", "figures"],
            "meta": {
                "source": "genomelens-shell",
                "shell_version": __version__,
                "platform_protocol": "task_manifest_v2",
                # 当前 engine 仍以 query/subject 为 pairwise worker 输入模型
                "species_model": "pairwise_query_subject",
            },
        }

    def build_global_karyotype_manifest(
        self,
        *,
        tracks: list[dict[str, str]],
        edges: list[dict[str, object]],
        blastn_path: str,
        makeblastdb_path: str,
        formats: list[str],
        task: dict[str, object] | None = None,
        species: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        """构建全局多物种核型总图 manifest(引擎清单)

        `tracks` 每项含 name/bed；`edges` 每项含 i/j 下标与 pairwise 产出的
        simple 文件路径。这个 manifest 不重算共线性，只渲染已算好的结果。
        """

        return {
            "schema_version": 2,
            "workflow": "graphics_karyotype_global",
            "task": task or {"workflow": "graphics_karyotype_global", "task_type": "global_synteny"},
            "species": species or [],
            "tracks": [{"name": str(track["name"]), "bed": absolute_path(track["bed"])} for track in tracks],
            "edges": [
                {
                    "i": int(cast(int, edge["i"])),
                    "j": int(cast(int, edge["j"])),
                    "simple": absolute_path(str(edge["simple"])),
                }
                for edge in edges
            ],
            "toolchain": {
                "blastn": absolute_path(blastn_path),
                "makeblastdb": absolute_path(makeblastdb_path),
            },
            "options": {
                "formats": formats,
            },
            "expected_outputs": ["global_karyotype_figures"],
            "meta": {
                "source": "genomelens-shell",
                "shell_version": __version__,
                "platform_protocol": "task_manifest_v2",
                # 全局总图不再用 query/subject，而是切换到 tracks/edges 模型
                "species_model": "multi_species_tracks",
            },
        }

    def write_manifest(self, manifest: dict[str, object], path: str | Path) -> Path:
        """用 UTF-8 编码写出 manifest JSON(清单 JSON)"""

        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return target

    def run_manifest(self, manifest_path: str | Path, outdir: str | Path) -> JcviRunResult:
        """用 manifest(清单) 运行 engine(引擎)，并解析摘要"""

        result = run_command([self.engine_path, "run", "--manifest", manifest_path, "--outdir", outdir], timeout=3600)
        summary_path = Path(outdir) / "engine_run_summary.json"
        if not result.ok:
            # engine 失败时优先读取已写出的 summary，这样 shell 侧能保留更完整的错误上下文
            if summary_path.is_file():
                parsed = self.parse_engine_summary(summary_path)
                raise EngineRunError(f"engine failed with summary: {parsed.error}")
            raise EngineRunError(result.stderr or result.stdout or f"engine run failed: {result.returncode}")
        return self.parse_engine_summary(summary_path)

    def parse_engine_summary(self, summary_path: str | Path) -> JcviRunResult:
        """解析公开 engine summary(引擎摘要) 契约"""

        path = Path(summary_path)
        if not path.is_file():
            raise SummaryParseError(f"engine summary not found: {path}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SummaryParseError(f"engine summary is not valid JSON: {path}") from exc

        artifacts = payload.get("artifacts") or {}
        if not isinstance(artifacts, dict):
            raise SummaryParseError("engine summary artifacts must be an object")
        return JcviRunResult(
            status=str(payload.get("status") or "failed"),
            summary_path=path,
            engine_version=str(payload.get("engine_version") or ""),
            jcvi_upstream_version=str(payload.get("jcvi_upstream_version") or ""),
            patchset=str(payload.get("patchset") or ""),
            artifacts=artifacts,
            distribution=str(payload.get("distribution") or ""),
            runtime_mode=str(payload.get("runtime_mode") or ""),
            loaded_extensions=list(payload.get("loaded_extensions") or []),
            missing_extensions=list(payload.get("missing_extensions") or []),
            task=dict(payload.get("task") or {}),
            species=list(payload.get("species") or []),
            artifact_index=list(payload.get("artifact_index") or []),
            error=payload.get("error"),
        )
