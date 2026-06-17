import json
from pathlib import Path

from genomelens.data.config.config_store import (
    default_config,
    default_jcvi_config_path,
    read_config,
    write_split_config,
)


def test_split_config_roundtrip(tmp_path: Path) -> None:
    config = default_config(tmp_path / "work")
    main_path = tmp_path / "work" / "genomelens.config.json"
    jcvi_path = default_jcvi_config_path(tmp_path / "work")

    written_main, written_jcvi = write_split_config(config, main_path, jcvi_path)
    loaded = read_config(written_main)

    assert written_main == main_path.resolve(strict=False)
    assert written_jcvi == jcvi_path.resolve(strict=False)
    assert loaded.workspace.jcvi_config_path == str(written_jcvi)
    assert loaded.schema_version == 2

    # runtime 仅保留通用运行级字段
    assert loaded.runtime.default_threads == 4
    assert loaded.runtime.default_formats == ["png"]
    assert loaded.runtime.log_level == "INFO"

    # mcscan 分组
    assert loaded.mcscan.workflow == "graphics_synteny"
    assert loaded.mcscan.min_block_size == 5
    assert loaded.mcscan.align_soft == "blast"
    assert loaded.mcscan.dbtype == "nucl"
    assert loaded.mcscan.cscore == 0.7
    assert loaded.mcscan.dist == 20
    assert loaded.mcscan.iter == 1
    assert loaded.mcscan.reference == ""

    # local_synteny 分组
    assert loaded.local_synteny.target_gene_ids == []
    assert loaded.local_synteny.up == 20
    assert loaded.local_synteny.down == 20
    assert loaded.local_synteny.split_targets is False
    assert loaded.local_synteny.label_targets is False
    assert loaded.local_synteny.dpi == 300

    assert loaded.toolchain.lastal_path == ""
    assert loaded.toolchain.lastdb_path == ""

    # 断言 jcvi.config.json 为分组结构
    jcvi_text = jcvi_path.read_text(encoding="utf-8")
    assert '"toolchain"' in jcvi_text
    assert '"mcscan"' in jcvi_text
    assert '"local_synteny"' in jcvi_text
    assert '"cscore"' in jcvi_text
    assert '"reference"' in jcvi_text
    assert '"dpi"' in jcvi_text


def test_jcvi_config_reads_v2_grouped_keys(tmp_path: Path) -> None:
    jcvi_path = tmp_path / "jcvi.config.json"
    jcvi_path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "toolchain": {
                    "blastn_path": "C:\\Tools\\blast\\bin\\blastn.exe",
                },
                "runtime": {
                    "threads": 8,
                },
                "mcscan": {
                    "workflow": "graphics_dotplot",
                    "cscore": 0.9,
                    "reference": "subject",
                },
                "local_synteny": {
                    "up": 15,
                    "dpi": 200,
                },
            }
        ),
        encoding="utf-8",
    )
    main_path = tmp_path / "genomelens.config.json"
    main_path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "workspace_root": str(tmp_path / "work"),
                "jcvi_config_path": str(jcvi_path),
                "log_level": "INFO",
            }
        ),
        encoding="utf-8",
    )
    loaded = read_config(main_path)
    assert loaded.toolchain.blastn_path == str(Path("C:\\Tools\\blast\\bin\\blastn.exe").resolve())
    assert loaded.runtime.default_threads == 8
    assert loaded.mcscan.workflow == "graphics_dotplot"
    assert loaded.mcscan.cscore == 0.9
    assert loaded.mcscan.reference == "subject"
    assert loaded.local_synteny.up == 15
    assert loaded.local_synteny.dpi == 200
