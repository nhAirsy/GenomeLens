"""MCscan 方法插件"""

# region import
from __future__ import annotations

import argparse

from genomelens.analysis.methods.mcscan_provider import McscanWorkflowProvider
from genomelens.analysis.methods.mcscan_request_mapping import to_mcscan_request
from genomelens.analysis.methods.registry import ArtifactDeclaration, MethodPlugin
from genomelens.analysis.request_models import AnalysisRequest
from genomelens.analysis.request_normalizer import mcscan_auto_request_from_cli
from genomelens.app.controller.workflow_provider import WorkflowProvider

# endregion


class McscanPlugin(MethodPlugin):
    """McscanPlugin(MCscan 方法插件)：把 MCscan/JCVI 接入平台注册表"""

    @property
    def name(self) -> str:
        """返回方法唯一标识名"""

        return "mcscan"

    @property
    def description(self) -> str:
        """返回供 CLI/GUI 展示的一行描述"""

        return "JCVI 共线性分析与绘图"

    @property
    def stable(self) -> bool:
        """MCscan 是平台当前的主要稳定方法"""

        return True

    def validate_request(self, request: AnalysisRequest) -> None:
        """通过构造 McscanRequest 来校验输入是否满足 MCscan 要求"""

        to_mcscan_request(request)

    def get_provider(self) -> WorkflowProvider:
        """返回 MCscan 工作流提供者"""

        return McscanWorkflowProvider()

    def add_cli_arguments(self, parser: argparse.ArgumentParser) -> None:
        """按功能分组注册 `analyze mcscan` 的全部参数"""

        # region 输入输出
        io_group = parser.add_argument_group("输入输出")
        io_group.add_argument("input_dir", help="输入目录（自动发现同名物种文件对）")
        io_group.add_argument("output_dir", help="输出目录")
        io_group.add_argument(
            "jcvi_config_positional",
            nargs="?",
            default="",
            help="可选：JCVI 配置文件路径（也可使用 --jcvi-config）",
        )
        io_group.add_argument("-c", "--config", default="", help="GenomeLens 主配置 JSON 路径")
        io_group.add_argument("--jcvi-config", default="", help="JCVI 配置 JSON 路径（优先级高于位置参数）")
        io_group.add_argument("--force", action="store_true", help="允许复用已有输出目录")
        io_group.add_argument("-j", "--json", action="store_true", help="输出机器可读的原始 JSON 摘要")

        # endregion

        # region 物种与参考
        species_group = parser.add_argument_group("物种与参考")
        species_group.add_argument("--reference", default="", help="参考物种名称或 1-based 索引；默认第一个物种")

        # endregion

        # region 运行时与工具链
        runtime_group = parser.add_argument_group("运行时与工具链")
        runtime_group.add_argument("--threads", type=int, default=None, help="线程数")
        runtime_group.add_argument("--jcvi-engine", default="", help="显式指定 jcvi-genomelens 引擎")
        runtime_group.add_argument("--blastn", default="", help="显式指定 blastn 可执行文件")
        runtime_group.add_argument("--makeblastdb", default="", help="显式指定 makeblastdb 可执行文件")

        # endregion

        # region 同源搜索与共线性
        homology_group = parser.add_argument_group("同源搜索与共线性")
        homology_group.add_argument(
            "--align-soft",
            choices=["blast", "last", "diamond_blastp"],
            default="",
            help="比对后端：blast / last / diamond_blastp",
        )
        homology_group.add_argument(
            "--dbtype",
            choices=["nucl", "prot"],
            default="",
            help="序列类型：nucl（核酸）/ prot（蛋白）",
        )
        homology_group.add_argument("--cscore", type=float, default=None, help="同源匹配过滤强度，默认 0.7")
        homology_group.add_argument("--dist", type=int, default=None, help="共线性锚点间最大基因距离，默认 20")
        homology_group.add_argument("--iter", type=int, default=None, help="Block 过滤迭代次数，默认 1")
        homology_group.add_argument("--min-block-size", type=int, default=None, help="最小共线性 block(区块) 大小")

        # endregion

        # region 目标基因局部共线性
        local_group = parser.add_argument_group("目标基因局部共线性")
        local_group.add_argument("--target-genes", default="", help="目标基因 ID，多个用逗号分隔")
        local_group.add_argument("--up", type=int, default=None, help="目标基因上游取多少个基因，默认 20")
        local_group.add_argument("--down", type=int, default=None, help="目标基因下游取多少个基因，默认 20")
        local_group.add_argument("--split-targets", action="store_true", help="多个目标基因时各自单独出图")
        local_group.add_argument("--label-targets", action="store_true", help="在图中标注目标基因名称")

        # endregion

        # region 图件样式
        style_group = parser.add_argument_group("图件样式")
        style_group.add_argument("--formats", default="", help="输出格式，例如 png 或 png,pdf")
        style_group.add_argument("--glyphstyle", choices=["box", "arrow"], default="", help="基因形状：box / arrow")
        style_group.add_argument(
            "--glyphcolor",
            choices=["orientation", "orthogroup"],
            default="",
            help="基因着色：orientation / orthogroup",
        )
        style_group.add_argument("--shadestyle", choices=["curve", "line"], default="", help="连线样式：curve / line")
        style_group.add_argument("--figsize", default="", help="画布尺寸，例如 10x5")
        style_group.add_argument("--dpi", type=int, default=None, help="图片分辨率，默认 300")

        # endregion

        # region 诊断开关
        diag_group = parser.add_argument_group("诊断开关")
        diag_group.add_argument(
            "--allow-simplified-fallback",
            action="store_true",
            help="保留诊断开关；正式流程会拒绝简化降级",
        )
        diag_group.add_argument("--jcvi-workflow", default="", help="JCVI workflow(工作流) 名称")
        diag_group.add_argument("--jcvi-layout", default="", help="JCVI layout(布局) 文件")
        diag_group.add_argument("--jcvi-seqids", default="", help="JCVI seqids(序列编号) 文件")

        # endregion

    def build_request(self, args: argparse.Namespace) -> AnalysisRequest:
        """把解析后的 CLI 参数转成 AnalysisRequest"""

        return mcscan_auto_request_from_cli(args)

    def list_artifacts(self) -> list[ArtifactDeclaration]:
        """返回 MCscan 方法可能产出的主要产物"""

        return [
            ArtifactDeclaration("blast_table", "table", "BLAST 同源比对表", required=True),
            ArtifactDeclaration("anchors", "table", "共线性锚点文件", required=True),
            ArtifactDeclaration("simple", "table", "简化共线性边文件", required=False),
            ArtifactDeclaration("blocks", "table", "共线性 block 文件", required=False),
            ArtifactDeclaration("figures", "image", "共线性图件", required=False),
            ArtifactDeclaration("global_karyotype", "image", "全局核型总图", required=False),
        ]
