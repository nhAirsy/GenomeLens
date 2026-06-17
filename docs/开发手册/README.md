# 开发手册

## 环境

开发环境统一使用 `genomelens` conda 环境，解释器版本为 Python 3.12。

```powershell
conda activate genomelens
python --version
```

`platform/` 和 `engines/jcvi/` 是两个 editable package(可编辑安装包)，但使用同一个解释器环境。

## 当前架构

- `platform/`：GenomeLens shell(外壳) / 平台核心雏形，不直接导入 `jcvi`。包名仍为 `genomelens`。
- `engines/jcvi/`：第一个正式 engine(引擎)，持有 vendored JCVI(随包 JCVI)。包名仍为 `jcvi_genomelens`。
- `engines/`：引擎层目录，未来可平级接入第二个比较基因组学引擎。
- `gui/`、`agents/`：为 Tauri GUI 与 Agent 预留的路线图目录（当前仅占位）。
- `integrations/haiant_plugin/`：HAIant adapter(智然体适配器)。
- `references/`：示例数据与本地参考。`references/upstream/` 是本地上游对照镜像，已不进入 Git 跟踪。
- `toolchains/`：本地 runtime cache(运行时缓存)，不进入 Git 跟踪。

补充文档：

- `架构调整/README.md`：平台化、多平台、Tauri GUI 与 Agent 相关架构文档索引。
- `架构调整/多平台兼容方案.md`：说明共享核心、多平台薄外壳的运行与发布策略。
- `架构调整/最终架构目标.md`：说明平台核心、多引擎、Tauri GUI、深度学习和 Agent 的长期目标。
- `../历史文档/分析命令改版计划.md`：说明 `genomelens analyze` 命令如何改为统一 request(JSON 请求) 与 dispatcher(调度器) 架构。该计划已落地并归档。
- `协作开发方案.md`：2~3 人核心团队 + 开源贡献者的分支模型、PR 流程与 `main` 分支保护规则。

当前代码实现的是：

- 双物种真实 JCVI 端到端链路。
- 多物种 all-vs-all pairwise(全组合两两比较) 编排与汇总。
- 以参考物种目标基因为中心的 `local_synteny` 局部共线性链路。
- 把成功 pairwise 共线性边聚合成一张全局核型总图（`graphics_karyotype_global`）。

## 测试

```powershell
python -m pytest platform/tests
python -m pytest engines/jcvi/tests
python -m pytest integrations/haiant_plugin/tests
```

完整烟测应覆盖：

- BED+CDS 双物种输入。
- GFF+FASTA 双物种输入。
- `graphics_synteny` 默认 dotplot + synteny 输出。
- `graphics_dotplot` 独立点图。
- `graphics_karyotype` 独立核型共线性图。
- `catalog_ortholog` 双向 ortholog 输出。
- `local_synteny` 目标基因局部共线性。
- 多物种 all-vs-all pairwise 编排与全局核型总图。
- HAIant plugin(智然体插件) 参数翻译。

## 构建

```powershell
conda run -n genomelens powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_split_packages.ps1
conda run -n genomelens powershell -NoProfile -ExecutionPolicy Bypass -Command "Push-Location integrations\haiant_plugin; python -m PyInstaller pyinstaller\genomelens_haiant.spec --clean --noconfirm; Pop-Location; .\scripts\build_haiant_plugin.ps1"
```

构建输出写入 `app/`，不进入 Git 跟踪。
