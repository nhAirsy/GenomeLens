# 第三方组件与许可声明

GenomeLens 自有代码以 MIT License 授权，许可全文见根目录 `LICENSE`。

本项目同时分发或依赖以下第三方组件，它们各自保留其原始许可，**不受 MIT 覆盖**：

## vendored JCVI（随包上游源码）

- 位置：`engines/jcvi/src/jcvi/`
- 许可：BSD 2-Clause 风格许可，版权归 Haibao Tang 及 JCVI 贡献者所有。
- 许可全文：`engines/jcvi/licenses/JCVI-LICENSE.txt`
- 本地相对上游的改动记录见 `engines/jcvi/上游修改汇总.md`。

## 运行时工具链（不随源码仓库分发）

以下工具链通过自动下载或独立交付获取，不进入 Git 跟踪，各自适用其官方许可：

- BLAST+（NCBI 公共领域 / 适用其官方条款）
- ImageMagick（ImageMagick License，Apache-2.0 风格）

## Python 运行期依赖

`engines/jcvi/pyproject.toml` 与 `platform/pyproject.toml` 声明的第三方 Python 包（如 biopython、matplotlib、networkx、numpy、scipy、ete3 等）各自适用其上游许可，本项目不改变其授权条款。

## 说明

MIT License 仅覆盖 GenomeLens 自有代码（`platform/`、`engines/jcvi/src/jcvi_genomelens/`、`integrations/`、`scripts/` 等本项目原创部分），不覆盖上述第三方组件。如对某一文件的归属有疑问，以该文件或其所在目录的许可声明为准。
