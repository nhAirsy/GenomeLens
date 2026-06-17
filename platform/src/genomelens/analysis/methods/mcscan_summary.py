"""MCscan 方法专属的 RunSummary 扩展字段"""

# region import
from __future__ import annotations

from dataclasses import dataclass, field

from genomelens.core.json_utils import _optional_int
from genomelens.core.summary_models import PairwiseJobSummary

# endregion


@dataclass(frozen=True)
class McscanSummaryExtension:
    """McscanSummaryExtension：承载 RunSummary 中所有 JCVI/MCscan 专属字段

    这些字段不再直接挂在 `RunSummary` 上，而是通过 `method_data` 注入，
    使顶层摘要保持方法无关，同时通过 `to_dict()` 扁平展开保持 JSON 兼容。
    """

    # 引擎元数据
    jcvi_backend: str = ""
    jcvi_workflow: str = ""
    jcvi_engine_path: str = ""
    jcvi_distribution: str = ""
    jcvi_engine_version: str = ""
    jcvi_upstream_version: str = ""
    jcvi_patchset: str = ""
    jcvi_runtime_mode: str = ""
    jcvi_loaded_extensions: list[str] = field(default_factory=list)
    jcvi_missing_extensions: list[str] = field(default_factory=list)

    # 通用产物字段
    engine_summary_path: str = ""
    blast_table: str = ""
    anchors_path: str = ""
    simple_path: str = ""
    blocks_path: str = ""
    query_bed: str = ""
    subject_bed: str = ""
    preprocess_summaries: list[dict[str, object]] = field(default_factory=list)
    preprocessing_summary_path: str = ""
    simplified_fallback: bool = False

    # pairwise 特有字段
    species_a_name: str | None = None
    species_b_name: str | None = None
    species_a_input_mode: str | None = None
    species_b_input_mode: str | None = None
    species_a_bed: str | None = None
    species_b_bed: str | None = None

    # multi-species / reference-vs-targets 特有字段
    species_count: int | None = None
    pairing_strategy: str | None = None
    pairwise_jobs: list[PairwiseJobSummary] | None = None
    pairwise_job_count: int | None = None
    global_figures: list[str] | None = None
    reference_name: str | None = None

    # 原生多物种标记；当前 MCscan 只走 pairwise 聚合，因此默认 False
    native_multi_species: bool = False
    native_edges: list[dict[str, object]] | None = None
    native_layout: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        """转成可合并进 RunSummary.method_data 的字典"""

        data: dict[str, object] = {}

        engine_meta_keys = (
            "jcvi_backend",
            "jcvi_workflow",
            "jcvi_engine_path",
            "jcvi_distribution",
            "jcvi_engine_version",
            "jcvi_upstream_version",
            "jcvi_patchset",
            "jcvi_runtime_mode",
        )
        has_engine_meta = any(getattr(self, key) for key in engine_meta_keys)

        # 引擎元数据：只在有值时输出，避免空字符串污染 summary
        for key in engine_meta_keys:
            value = getattr(self, key)
            if value:
                data[key] = value

        # extension 状态和 runtime 元数据一起出现，读取方更容易当成一组处理
        if has_engine_meta:
            data["jcvi_loaded_extensions"] = list(self.jcvi_loaded_extensions)
            data["jcvi_missing_extensions"] = list(self.jcvi_missing_extensions)
            data["simplified_fallback"] = self.simplified_fallback
        # 通用产物字段
        for key in (
            "engine_summary_path",
            "blast_table",
            "anchors_path",
            "simple_path",
            "blocks_path",
            "query_bed",
            "subject_bed",
            "preprocessing_summary_path",
        ):
            value = getattr(self, key)
            if value:
                data[key] = value

        if self.preprocess_summaries:
            data["preprocess_summaries"] = list(self.preprocess_summaries)
        if self.simplified_fallback:
            data["simplified_fallback"] = self.simplified_fallback

        # pairwise 特有
        for key in (
            "species_a_name",
            "species_b_name",
            "species_a_input_mode",
            "species_b_input_mode",
            "species_a_bed",
            "species_b_bed",
        ):
            value = getattr(self, key)
            if value is not None:
                data[key] = value

        # multi / reference-vs-targets 特有
        if self.species_count is not None:
            data["species_count"] = self.species_count
        if self.pairing_strategy is not None:
            data["pairing_strategy"] = self.pairing_strategy
        if self.pairwise_jobs is not None:
            data["pairwise_jobs"] = [job.to_json() for job in self.pairwise_jobs]
            data["pairwise_job_count"] = len(self.pairwise_jobs)
        if self.global_figures is not None:
            data["global_figures"] = list(self.global_figures)
        if self.reference_name is not None:
            data["reference_name"] = self.reference_name

        # 原生多物种扩展字段；当前 MCscan 默认 False，为后续引擎预留
        data["native_multi_species"] = self.native_multi_species
        if self.native_edges is not None:
            data["native_edges"] = list(self.native_edges)
        if self.native_layout is not None:
            data["native_layout"] = dict(self.native_layout)

        return data

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> McscanSummaryExtension:
        """从 RunSummary.method_data 的原始字典还原"""

        raw_jobs = data.get("pairwise_jobs")
        pairwise_jobs: list[PairwiseJobSummary] | None = None
        if isinstance(raw_jobs, list):
            pairwise_jobs = [PairwiseJobSummary.from_json(item) for item in raw_jobs if isinstance(item, dict)]

        def _str_list(value: object) -> list[str]:
            if isinstance(value, list):
                return [str(item) for item in value]
            return []

        def _dict_list(value: object) -> list[dict[str, object]]:
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
            return []

        def _dict(value: object) -> dict[str, object]:
            if isinstance(value, dict):
                return value
            return {}

        return cls(
            jcvi_backend=str(data.get("jcvi_backend") or ""),
            jcvi_workflow=str(data.get("jcvi_workflow") or ""),
            jcvi_engine_path=str(data.get("jcvi_engine_path") or ""),
            jcvi_distribution=str(data.get("jcvi_distribution") or ""),
            jcvi_engine_version=str(data.get("jcvi_engine_version") or ""),
            jcvi_upstream_version=str(data.get("jcvi_upstream_version") or ""),
            jcvi_patchset=str(data.get("jcvi_patchset") or ""),
            jcvi_runtime_mode=str(data.get("jcvi_runtime_mode") or ""),
            jcvi_loaded_extensions=_str_list(data.get("jcvi_loaded_extensions")),
            jcvi_missing_extensions=_str_list(data.get("jcvi_missing_extensions")),
            engine_summary_path=str(data.get("engine_summary_path") or ""),
            blast_table=str(data.get("blast_table") or ""),
            anchors_path=str(data.get("anchors_path") or ""),
            simple_path=str(data.get("simple_path") or ""),
            blocks_path=str(data.get("blocks_path") or ""),
            query_bed=str(data.get("query_bed") or ""),
            subject_bed=str(data.get("subject_bed") or ""),
            preprocess_summaries=_dict_list(data.get("preprocess_summaries")),
            preprocessing_summary_path=str(data.get("preprocessing_summary_path") or ""),
            simplified_fallback=bool(data.get("simplified_fallback")),
            species_a_name=str(data["species_a_name"]) if "species_a_name" in data else None,
            species_b_name=str(data["species_b_name"]) if "species_b_name" in data else None,
            species_a_input_mode=str(data["species_a_input_mode"]) if "species_a_input_mode" in data else None,
            species_b_input_mode=str(data["species_b_input_mode"]) if "species_b_input_mode" in data else None,
            species_a_bed=str(data["species_a_bed"]) if "species_a_bed" in data else None,
            species_b_bed=str(data["species_b_bed"]) if "species_b_bed" in data else None,
            species_count=_optional_int(data.get("species_count")),
            pairing_strategy=str(data["pairing_strategy"]) if "pairing_strategy" in data else None,
            pairwise_jobs=pairwise_jobs,
            global_figures=_str_list(data.get("global_figures")),
            reference_name=str(data["reference_name"]) if "reference_name" in data else None,
            native_multi_species=bool(data.get("native_multi_species", False)),
            native_edges=_dict_list(data.get("native_edges")),
            native_layout=_dict(data.get("native_layout")),
        )


__all__ = ["McscanSummaryExtension"]
