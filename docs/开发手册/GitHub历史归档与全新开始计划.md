# GitHub 历史归档与全新开始计划

> 状态：待实施  
> 触发条件：当前紧急问题全部解决后  
> 目标：将杂乱历史归档到本地，GitHub 上只保留 `v1.0.0` 正式发布的干净起点。

---

## 1. 背景与目标

### 1.1 背景

- 仓库历史较长、较杂乱，且可能混入敏感信息（本地路径、IDE 状态、实验性配置等）。
- 仓库目前为 public，但实际仅个人/AI 协作使用，无外部贡献者。
- 即将发布 `v1.0.0`，希望对外呈现一个干净的发布起点。

### 1.2 目标

- **本地**：保留一份完整历史镜像，供必要时回溯、取证或提取旧代码。
- **GitHub**：`main` 分支仅保留一个代表 `v1.0.0` 正式版的提交，历史从该点重新开始。
- **后续开发**：继续沿用分支流程（feature/fix → PR → main），保护新的干净历史。

---

## 2. 前置条件

在实施前必须完成：

- [ ] 当前所有紧急 bug 已修复并合并到 `main`
- [ ] 所有待合并的远程分支已处理（合并或关闭）
- [ ] 本地无未提交的重要改动
- [ ] 已确认 `v1.0.0` 功能清单和版本号
- [ ] 已准备好本地归档存储位置（如外接硬盘、私有 NAS、加密压缩包）

---

## 3. 详细执行步骤

### 步骤 1：本地完整归档（保留一切历史）

```bash
# 进入临时目录
cd D:\myself\GenomeLens-archives

# 创建裸仓库镜像（包含所有分支、标签、PR 引用）
git clone --mirror git@github.com:nhAirsy/GenomeLens.git GenomeLens-pre-1.0.0-mirror.git

# 可选：打包压缩并设置密码
7z a -p GenomeLens-pre-1.0.0-mirror.7z GenomeLens-pre-1.0.0-mirror.git
```

验证归档完整性：

```bash
cd GenomeLens-pre-1.0.0-mirror.git
git log --oneline --all | head -20
git branch -a
git tag -l
```

### 步骤 2：在本地主仓库中创建干净的 orphan 分支

```bash
cd D:\myself\GenomeLens

# 确保本地 main 是最新的
git checkout main
git pull origin main

# 创建无历史的 orphan 分支
git checkout --orphan clean-main

# 添加当前所有文件（不包含 .git 历史）
git add -A

# 提交为 v1.0.0 正式发布
# 注意：提交信息应包含 1.0.0 完整功能摘要
git commit -m "release: v1.0.0" -m "GenomeLens 1.0.0 正式发布。" -m "包含功能：..." -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```

### 步骤 3：强制替换 GitHub 上的 main

```bash
# 将 clean-main 强制推送到 origin/main
git push origin --force clean-main:main

# 删除本地 orphan 分支（可选，main 已经指向它）
git checkout main
git branch -D clean-main
```

### 步骤 4：清理远程旧分支和标签

```bash
# 列出所有远程分支
git branch -r

# 删除所有非 main 的远程分支
git push origin --delete fix/issue-3 fix/issue-5 ...

# 删除所有旧标签（如果不需要保留）
git push origin --delete tag 1.0.0-preview-1 1.0.0-preview-2 ...
```

### 步骤 5：创建 v1.0.0 标签和 GitHub Release

```bash
# 在干净的 main 上打标签
git tag -a v1.0.0 -m "release: v1.0.0"
git push origin v1.0.0
```

然后在 GitHub 上创建 Release，附上 Release Note。

### 步骤 6：重新配置分支保护

由于 main 历史被重写，之前的 branch protection 仍然生效，但需要确认：

- `Settings → Branches → main` 保护规则是否仍在
- 是否需要重新启用 required status checks

### 步骤 7：更新所有本地克隆和工作区

所有使用该仓库的设备/工作区都需要重置：

```bash
# 在每台设备上执行
git fetch origin
git checkout main
git reset --hard origin/main
```

对于 worktree：

```bash
git worktree remove D:\myself\GenomeLens-fix-worktree --force
# 需要时重新创建
```

---

## 4. 发布说明（Release Note）模板

```markdown
## GenomeLens 1.0.0

### 主要功能
- 双物种真实 JCVI 端到端分析
- 多物种 all-vs-all pairwise 编排与全局核型总图
- 以目标基因为中心的局部共线性分析
- 配置文件驱动与 HAIant 插件集成
- Windows 优先的 CLI 与打包支持

### 技术栈
- Python 3.12
- platform + engines/jcvi 分层架构
- pytest + ruff CI

### 注意
本次发布为 GitHub 上的干净起点，完整开发历史已归档到本地私有存储。
```

---

## 5. 回滚方案

如果强制推送后发现严重问题：

```bash
# 从本地归档恢复
cd D:\myself\GenomeLens-archives\GenomeLens-pre-1.0.0-mirror.git
git push --force --all origin
git push --force --tags origin
```

⚠️ 回滚会再次重写 GitHub 历史，仅在必要时使用。

---

## 6. 风险与注意事项

| 风险 | 应对措施 |
|------|---------|
| 本地归档损坏或丢失 | 至少保留两份备份（如本地磁盘 + 云盘加密压缩包） |
| 强制推送后旧 issue/PR 引用失效 | 提前截图或导出重要 issue 讨论 |
| GitHub Actions / Webhook 异常 | 检查后重新启用必要的 CI workflow |
| 敏感信息已泄露 | 如果历史中有真实密钥，务必在清理前轮换撤销 |
| 以后想开源展示历史 | 可在私有仓库或本地 archive 中保留 |

---

## 7. 实施检查清单

- [ ] 本地归档镜像已创建并验证
- [ ] 归档已复制到安全位置（至少 2 份）
- [ ] 所有敏感信息已确认并处理（轮换密钥等）
- [ ] 干净 orphan 分支已创建并检查文件内容
- [ ] `main` 已强制推送到 GitHub
- [ ] 旧远程分支和标签已清理
- [ ] `v1.0.0` 标签已推送
- [ ] GitHub Release 已创建
- [ ] 分支保护规则已确认
- [ ] 所有本地 worktree/克隆已同步到新的 main

---

## 8. 后续规范

全新开始后：

- 所有开发继续走 feature/fix 分支 + PR 流程
- 禁止直接 push 到 main（启用 branch protection）
- 提交信息遵循 Conventional Commits
- 定期打 tag：`v1.1.0`、`v1.1.1` 等
- 不再重写 main 历史
