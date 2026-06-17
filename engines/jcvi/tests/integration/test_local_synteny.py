import json
from pathlib import Path

from jcvi_genomelens.engine_runtime import run_manifest

ROOT = Path(__file__).resolve().parents[4]
SAMPLE = ROOT / "references" / "samples" / "shell" / "bed_cds_minimal"
BLAST_BIN = ROOT / "toolchains" / "blast" / "current" / "bin"


def _local_manifest(target_gene_ids: list[str], split_targets: bool = False) -> dict[str, object]:
    return {
        "schema_version": 2,
        "workflow": "local_synteny",
        "task": {
            "task_id": "query__subject__local_synteny",
            "task_type": "pairwise_synteny",
            "workflow": "local_synteny",
            "source": "pytest",
        },
        "species": [
            {
                "name": "query",
                "role": "query",
                "input_mode": "bed_cds",
                "bed": str(SAMPLE / "query.bed"),
                "cds": str(SAMPLE / "query.cds"),
            },
            {
                "name": "subject",
                "role": "subject",
                "input_mode": "bed_cds",
                "bed": str(SAMPLE / "subject.bed"),
                "cds": str(SAMPLE / "subject.cds"),
            },
        ],
        "query": {"name": "query", "bed": str(SAMPLE / "query.bed"), "cds": str(SAMPLE / "query.cds")},
        "subject": {"name": "subject", "bed": str(SAMPLE / "subject.bed"), "cds": str(SAMPLE / "subject.cds")},
        "toolchain": {
            "blastn": str(BLAST_BIN / "blastn.exe"),
            "makeblastdb": str(BLAST_BIN / "makeblastdb.exe"),
        },
        "options": {
            "threads": 1,
            "min_block_size": 1,
            "formats": ["png"],
            "align_soft": "blast",
            "dbtype": "nucl",
            "cscore": 0.7,
            "dist": 20,
            "iter": 1,
            "target_gene_ids": target_gene_ids,
            "up": 1,
            "down": 1,
            "split_targets": split_targets,
            "label_targets": True,
            "glyphstyle": "box",
            "glyphcolor": "orientation",
            "shadestyle": "line",
            "dpi": 150,
        },
        "expected_outputs": ["blast_table", "anchors", "simple", "blocks", "figures"],
    }


def test_engine_run_local_synteny_single_target(tmp_path: Path) -> None:
    manifest = tmp_path / "local.json"
    manifest.write_text(json.dumps(_local_manifest(["qgene2"])), encoding="utf-8")
    summary_path = run_manifest(manifest, tmp_path / "engine")
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert payload["status"] == "ok"
    assert payload["task"]["workflow"] == "local_synteny"

    artifacts = payload["artifacts"]
    assert Path(artifacts["blast_table"]).stat().st_size > 0
    assert Path(artifacts["blocks"]).is_file()
    assert artifacts["local_figures"]
    assert all(Path(p).is_file() for p in artifacts["local_figures"])

    local_artifacts = artifacts["local_artifacts"]
    assert len(local_artifacts) == 1
    item = local_artifacts[0]
    # 单个目标且未开启 split_targets 时，仍保留真实目标基因 ID，避免报错和产物指向 "merged"。
    assert item["target"] == "qgene2"
    assert Path(item["blocks"]).is_file()
    assert Path(item["bed"]).is_file()
    assert Path(item["layout"]).is_file()

    # qgene2 上下各 1 个基因，局部 blocks 应覆盖 qgene1..qgene3
    local_blocks_text = Path(item["blocks"]).read_text(encoding="utf-8")
    assert "qgene1" in local_blocks_text
    assert "qgene2" in local_blocks_text
    assert "qgene3" in local_blocks_text
    assert "qgene4" not in local_blocks_text


def test_engine_run_local_synteny_split_targets(tmp_path: Path) -> None:
    manifest = tmp_path / "local_split.json"
    manifest.write_text(json.dumps(_local_manifest(["qgene1", "qgene4"], split_targets=True)), encoding="utf-8")
    summary_path = run_manifest(manifest, tmp_path / "engine")
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert payload["status"] == "ok"

    targets = {item["target"] for item in payload["artifacts"]["local_artifacts"]}
    assert targets == {"qgene1", "qgene4"}
    assert all(Path(path).is_file() for path in payload["artifacts"]["local_figures"])
