"""`genomelens check` 命令"""

# region import
from __future__ import annotations

import argparse
import json

from genomelens.cli.ui import render_check_report
from genomelens.core.jcvi_adapter.adapter import JcviEngineAdapter
from genomelens.core.summary_models import CheckReport, CheckToolItem
from genomelens.data.config.config_store import read_optional_config
from genomelens.toolchain.runtime.platform_names import (
    blastn_candidates,
    jcvi_engine_candidates,
    magick_candidates,
    makeblastdb_candidates,
)
from genomelens.toolchain.runtime.resource_locator import locate_engine, locate_tool
from genomelens.toolchain.runtime.toolchain_installer import install_toolchain

# endregion


def register(subparsers: argparse._SubParsersAction) -> None:
    """注册 check 命令"""

    parser = subparsers.add_parser("check", help="检查运行环境和工具链")
    parser.add_argument("-j", "--json", action="store_true", help="输出机器可读 JSON")
    parser.add_argument("-c", "--config", default="", help="GenomeLens 主配置 JSON 路径")
    parser.add_argument("--jcvi-config", default="", help="JCVI 配置 JSON 路径")
    parser.add_argument("--jcvi-engine", default="", help="显式指定 jcvi-genomelens 可执行文件或脚本")
    parser.add_argument("--blastn", default="", help="显式指定 blastn 可执行文件")
    parser.add_argument("--makeblastdb", default="", help="显式指定 makeblastdb 可执行文件")
    parser.add_argument("--magick", default="", help="显式指定 ImageMagick 可执行文件")
    parser.add_argument("--install-missing", action="store_true", help="下载缺失的 BLAST+/ImageMagick 工具链")
    parser.set_defaults(func=run_check)


def run_check(args: argparse.Namespace) -> int:
    """运行 runtime diagnostics(运行时诊断)"""

    config = read_optional_config(args.config, jcvi_config_path=args.jcvi_config)
    toolchain = config.toolchain if config else None

    # check 命令复用真实定位逻辑，避免“检查通过但正式运行仍找不到工具”的双重标准
    engine = locate_engine(explicit=args.jcvi_engine, config=config)
    blastn = locate_tool(
        "blast",
        explicit=args.blastn,
        config_value=toolchain.blastn_path if toolchain else "",
        packaged_names=blastn_candidates(),
    )
    makeblastdb = locate_tool(
        "blast",
        explicit=args.makeblastdb,
        config_value=toolchain.makeblastdb_path if toolchain else "",
        packaged_names=makeblastdb_candidates(),
    )
    magick = locate_tool(
        "imagemagick",
        explicit=args.magick,
        config_value=toolchain.magick_path if toolchain else "",
        packaged_names=magick_candidates(),
    )
    installs: list[dict[str, object]] = []
    if args.install_missing:
        if not blastn.ok or not makeblastdb.ok:
            result = install_toolchain("blast")
            installs.append(
                {"name": result.name, "status": result.status, "path": result.path, "message": result.message}
            )
        if not magick.ok:
            result = install_toolchain("imagemagick")
            installs.append(
                {"name": result.name, "status": result.status, "path": result.path, "message": result.message}
            )
        blastn = locate_tool(
            "blast",
            explicit=args.blastn,
            config_value=toolchain.blastn_path if toolchain else "",
            packaged_names=blastn_candidates(),
        )
        makeblastdb = locate_tool(
            "blast",
            explicit=args.makeblastdb,
            config_value=toolchain.makeblastdb_path if toolchain else "",
            packaged_names=makeblastdb_candidates(),
        )
        magick = locate_tool(
            "imagemagick",
            explicit=args.magick,
            config_value=toolchain.magick_path if toolchain else "",
            packaged_names=magick_candidates(),
        )

    # report 统一落到强类型对象，CLI 文本输出和 JSON 输出都从这里派生
    blastn_item = CheckToolItem(status=blastn.status, path=blastn.path, message=blastn.message)
    makeblastdb_item = CheckToolItem(status=makeblastdb.status, path=makeblastdb.path, message=makeblastdb.message)
    magick_item = CheckToolItem(status=magick.status, path=magick.path, message=magick.message)
    jcvi_engine_item = CheckToolItem(status=engine.status, path=engine.path, message=engine.message)

    if engine.ok:
        try:
            # probe 额外补充引擎能力、版本与运行模式，方便诊断“路径正确但能力不匹配”的情况
            probe = JcviEngineAdapter(engine.path).probe()
            jcvi_engine_item = CheckToolItem(
                status=engine.status,
                path=engine.path,
                message=engine.message,
                extra=probe,
            )
        except Exception as exc:  # noqa: BLE001 - 诊断命令需要把探测失败写入报告
            jcvi_engine_item = CheckToolItem(status="error", path=engine.path, message=str(exc))

    status = "ok"
    if not all(item.status == "ok" for item in (blastn_item, makeblastdb_item, magick_item, jcvi_engine_item)):
        status = "degraded"

    report = CheckReport(
        status=status,
        blastn=blastn_item,
        makeblastdb=makeblastdb_item,
        magick=magick_item,
        jcvi_engine=jcvi_engine_item,
        install_attempts=installs,
        engine_candidate_names=jcvi_engine_candidates(),
    )

    if args.json:
        print(json.dumps(report.to_json(), ensure_ascii=False, indent=2))
    else:
        print(render_check_report(report))
    return 0 if report.status == "ok" else 5
