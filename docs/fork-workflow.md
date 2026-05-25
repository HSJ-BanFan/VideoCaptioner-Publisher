# VideoCaptioner Fork 开发工作流规范

本文档定义了本仓库的“长期分叉（Fork）维护模型”。
目标：维护自定义产品线，持续开发专属功能，并定期、安全地吸收上游补丁。

## 1. 核心概念

我们不是上游仓库的临时贡献者，而是独立产品线的维护者。
因此，我们的开发基于 **长期集成分支模型**，不追求将主分支做成上游镜像。

### 角色定义

- **upstream**: `WEIFENG2333/VideoCaptioner`（上游原仓库，只读）
- **origin**: `HSJ-BanFan/VideoCaptioner-Publisher`（你的 fork 仓库，可写）
- **master**: 本地主分支，跟踪 `upstream/master`，**只用于同步上游更新，不承载直接开发**。
- **feature/***：功能分支，承载你的自定义开发，存放所有的二开特性。

---

## 2. 初始配置与 Remote 规范

为了与业界最佳实践保持一致，避免混淆，Remote 的命名必须遵循标准：

```bash
# 验证 Remote 命名
git remote -v

# 期望输出：
# origin    https://github.com/HSJ-BanFan/VideoCaptioner-Publisher.git (fetch/push)
# upstream  https://github.com/WEIFENG2333/VideoCaptioner (fetch/push)
```

---

## 3. 日常开发流：开新功能

功能分支永远从最新上游同步的 `master` 分支切出。

```bash
# 1. 确保 master 与上游一致
git switch master
git fetch upstream
git merge --ff-only upstream/master

# 2. 创建特性分支
git switch -c feature/your-feature-name

# 3. 开始开发、提交
git add .
git commit -m "feat(scope): 你的特性描述"

# 4. 推送到你的 fork 仓库
git push -u origin feature/your-feature-name
```

---

## 4. 吃上游更新：主线同步

上游有新提交时，通过 `master` 分支进行合并。

```bash
# 1. 切到主分支，获取上游更新
git switch master
git fetch upstream

# 2. 合并上游最新代码（应当是快进合并）
git merge --ff-only upstream/master

# 3. 将同步后的 master 推送到你的 fork
git push origin master
```

---

## 5. 解决上游与特性的冲突：更新特性分支

当你的功能分支做到一半，上游 `master` 更新了，你需要让特性分支跟上主线。

### 方案 A：保守稳妥（推荐用于共享功能分支）

在特性分支中 Merge `master`，保留两条历史的真实轨迹。

```bash
# 前提：master 已完成与 upstream 的同步
git switch feature/your-feature-name
git merge master
# 若有冲突，手工解决 -> git add . -> git commit
git push origin feature/your-feature-name
```

### 方案 B：单人开发（保持特性分支历史线性）

通过 Rebase 将你的提交重排到最新的 `master` 之后。

```bash
# 前提：master 已完成与 upstream 的同步
git switch feature/your-feature-name
git rebase master
# 若有冲突，手工解决 -> git add . -> git rebase --continue
# 由于历史被重写，推送时需要强制覆盖
git push --force-with-lease origin feature/your-feature-name
```

> **注意：** 如果该 `feature/*` 分支有其他人在共同开发，绝对**不要**使用 Rebase。

---

## 6. 与 Worktree 配合使用

强烈建议使用 Git Worktree 来并行处理多个功能，避免频繁的 Checkout 和 Stash。

```bash
# 添加新的工作树进行特定开发
git worktree add ../worktree-feature-name feature/your-feature-name
```

**实践建议：**
- 主目录留给 `master` 分支，负责日常的上游同步。
- 每个新功能在独立的 worktree 目录中进行开发。

---

## 7. 禁忌事项 (Anti-patterns)

- ❌ **直接在 `master` 上开发**：`master` 必须保持纯净，仅作为同步上游的载体。
- ❌ **强制推送 (Force Push) `master`**：`master` 是同步锚点，重写其历史会导致同步混乱。
- ❌ **在 GitHub 上随意使用 "Sync fork" (Discard commits)**：一旦提示需要丢弃提交，说明 `master` 被污染了，此时应先将提交备份到特性分支，再执行同步。
- ❌ **混淆 Origin 和 Upstream**：不要把自己的 fork 命名为 publisher/upstream，这会导致所有自动化脚本和文档失效。
