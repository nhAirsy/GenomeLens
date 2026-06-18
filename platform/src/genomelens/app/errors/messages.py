"""messages(用户文案)：CLI/GUI 中对外展示的中文提示常量

注意：
- 常量名以使用场景命名，便于检索。
- 需要占位符的文案使用 `{name}` 风格，由调用方 `.format(...)` 填充。
- 本模块只覆盖当前改进计划修改过的路径；未覆盖的硬编码字符串可逐步迁移。"""

# region import
from __future__ import annotations

# endregion


# region 工具链
TOOLCHAIN_BLAST_NOT_FOUND = "BLAST+ 未找到，自动下载也失败了：{message}"
TOOLCHAIN_LAST_NOT_FOUND = (
    "LAST 比对后端未找到。请安装 LAST 并确保它在 PATH 中，或使用 --align-soft blast 切换回 BLAST+ 后端。"
)
TOOLCHAIN_ENGINE_NOT_FOUND = "JCVI 引擎未找到：{message}"
TOOLCHAIN_GENERIC_NOT_FOUND = "工具链检查失败：{message}"

# endregion


# region 输入与请求
INPUT_DIRECTORY_NOT_FOUND = "auto 输入目录不存在：{path}"
INPUT_TOO_FEW_SPECIES = "auto 输入目录至少需要两个同名物种文件对"
INPUT_REFERENCE_OUT_OF_RANGE = "--reference 索引 {index} 超出范围（共 {count} 个物种）"
INPUT_REFERENCE_NOT_FOUND = "--reference 物种 '{name}' 不存在于输入目录；可用：{available}"
REQUEST_UNSUPPORTED_METHOD = "不支持的分析方法：{method}"
REQUEST_TOO_FEW_SPECIES = "mcscan 至少需要两个物种"
REQUEST_REFERENCE_INDEX_OUT_OF_RANGE = "reference_index {index} 超出物种范围"
LOCAL_SYNTENY_TARGET_GENES_NOT_IN_REFERENCE = (
    "目标基因 ID {genes} 在参考物种 '{reference}' 的 BED 中未找到。"
    "请检查 --reference 或 config.mcscan.reference 是否指向包含这些目标基因的物种。"
)
CONFIG_INVALID = "配置文件无效：{message}"

# endregion


# region 引擎与运行
ENGINE_PROBE_FAILED = "探测 JCVI 引擎失败：{message}"
ENGINE_RUN_FAILED = "JCVI 引擎运行失败：{message}"
SUMMARY_PARSE_FAILED = "解析引擎摘要失败：{message}"

# endregion


# region 评分占位
SCORING_NOT_RUN = "机器学习评分模块尚未接入当前工作流。"

# endregion


# region 通用
CHECK_STATUS_OK = "ok"
CHECK_STATUS_DEGRADED = "degraded"
CHECK_STATUS_UNKNOWN = "unknown"
CLI_ANALYSIS_SUCCEEDED = "分析完成"
CLI_ANALYSIS_FAILED = "分析失败"

# endregion
