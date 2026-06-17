"""读取、写入 analysis request(分析请求)"""

# region import
from __future__ import annotations

import json
from pathlib import Path

from genomelens.analysis.request_models import AnalysisRequest
from genomelens.app.errors.exceptions import InputValidationError

# endregion


def load_analysis_request(path: str | Path) -> AnalysisRequest:
    """从 JSON 文件读取 AnalysisRequest(分析请求)"""

    source = Path(path).expanduser().resolve(strict=False)
    data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise InputValidationError(f"analysis request 必须是 JSON object(对象)：{source}")

    # request loader 只负责协议层校验，不在这里补齐目录发现或默认值
    request = AnalysisRequest.from_json(data)
    if request.kind != "analysis_request":
        raise InputValidationError(f"不支持的 request kind(请求类型)：{request.kind}")
    if request.schema_version != 1:
        raise InputValidationError(f"不支持的 analysis request schema version：{request.schema_version}")
    return request


def write_analysis_request(request: AnalysisRequest, path: str | Path) -> Path:
    """写出 AnalysisRequest(分析请求)"""

    target = Path(path).expanduser().resolve(strict=False)
    target.parent.mkdir(parents=True, exist_ok=True)

    # 按稳定 JSON 快照落盘，方便 CLI、插件和后续 GUI 回放实际执行参数
    target.write_text(json.dumps(request.to_json(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target
