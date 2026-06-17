import json
from pathlib import Path

from jcvi_genomelens.manifest_loader import load_manifest


def test_manifest_loader(tmp_path: Path) -> None:
    bed = tmp_path / "a.bed"
    cds = tmp_path / "a.cds"
    bed.write_text("chr1\t0\t3\tgene1\t0\t+\n", encoding="utf-8")
    cds.write_text(">gene1\nATG\n", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "workflow": "graphics_synteny",
                "task": {
                    "task_id": "q__s__graphics_synteny",
                    "task_type": "pairwise_synteny",
                    "workflow": "graphics_synteny",
                    "source": "pytest",
                },
                "species": [
                    {"name": "q", "role": "query", "input_mode": "bed_cds", "bed": str(bed), "cds": str(cds)},
                    {"name": "s", "role": "subject", "input_mode": "bed_cds", "bed": str(bed), "cds": str(cds)},
                ],
                "query": {"name": "q", "bed": str(bed), "cds": str(cds)},
                "subject": {"name": "s", "bed": str(bed), "cds": str(cds)},
                "toolchain": {
                    "blastn": "",
                    "makeblastdb": "",
                    "lastal": "",
                    "lastdb": "",
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
                    "target_gene_ids": ["AT1G01010"],
                    "up": 20,
                    "down": 20,
                    "split_targets": False,
                    "label_targets": True,
                    "glyphstyle": "arrow",
                    "glyphcolor": "orthogroup",
                    "shadestyle": "curve",
                    "figsize": "10x5",
                    "dpi": 300,
                },
                "expected_outputs": ["blast_table", "figures"],
            }
        ),
        encoding="utf-8",
    )
    loaded = load_manifest(manifest)
    assert loaded.workflow == "graphics_synteny"
    assert loaded.query.name == "q"
    assert loaded.schema_version == 2
    assert loaded.task["task_type"] == "pairwise_synteny"
    assert loaded.options.align_soft == "blast"
    assert loaded.options.dbtype == "nucl"
    assert loaded.options.cscore == 0.7
    assert loaded.options.dist == 20
    assert loaded.options.iter == 1
    assert loaded.options.target_gene_ids == ["AT1G01010"]
    assert loaded.options.up == 20
    assert loaded.options.down == 20
    assert loaded.options.label_targets is True
    assert loaded.options.glyphstyle == "arrow"
    assert loaded.options.figsize == "10x5"
    assert loaded.options.dpi == 300
    assert loaded.toolchain.lastal is None
    assert loaded.toolchain.lastdb is None
