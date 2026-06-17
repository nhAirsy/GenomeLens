# engines/ — 引擎层

本目录承载 GenomeLens 的**分析引擎**。每个引擎都是与平台核心平级、可独立打包、可替换的计算单元，平台核心通过稳定协议调度它们，而不依赖任何引擎的私有命令格式。

## 当前引擎

- `jcvi/`：当前唯一正式引擎（JCVI-backed 共线性分析）。持有 vendored JCVI 源码，只对外暴露 `probe` 和 `run` 两个稳定入口。

## 引擎契约

任何新引擎都应通过以下统一接口被平台调度（参见 `docs/开发手册/架构调整/最终架构目标.md` 第 2 节）：

- `probe`：声明引擎身份、版本、运行模式与已加载扩展。
- `run`：接受标准化 `manifest(清单)`，输出标准化 `summary(摘要)`。
- `manifest schema` / `result schema` / `artifact declaration`。

平台核心（`platform/`）只通过 `jcvi_engine_manifest.json` 与 `engine_run_summary.json` 跨层通信，不直接 `import` 任何引擎包。

## 未来引擎（规划，尚未实现）

按 `最终架构目标.md`，后续引擎应与 `jcvi/` **平级**接入，而不是挂在它下面：

- `mcscanx/`、`syri/`、`pangenome/`、`orthology/`
- 机器学习评分类：`orthology-scoring/`、`promoter-risk/`、`region-scoring/`

新引擎接入顺序参见 `温和架构过渡.md`：先稳协议，再接第二引擎。
