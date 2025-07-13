 # Pull Request 提交教程

本文档详细介绍如何向开源项目提交 Pull Request (PR)，从 fork 仓库到最终提交 PR 的完整流程。

## 目录

1. [准备工作](#准备工作)
2. [Fork 原始仓库](#fork-原始仓库)
3. [克隆 Fork 仓库到本地](#克隆-fork-仓库到本地)
4. [设置上游仓库](#设置上游仓库)
5. [创建分支](#创建分支)
6. [修改代码](#修改代码)
7. [提交更改](#提交更改)
8. [推送到远程仓库](#推送到远程仓库)
9. [创建 Pull Request](#创建-pull-request)
10. [跟进 PR 状态](#跟进-pr-状态)
11. [如何查看 PR 是否被采纳](#如何查看-pr-是否被采纳)
12. [更新 PR](#更新-pr)
13. [常见问题](#常见问题)

## 准备工作

在开始之前，确保您已经：

- 安装了 Git
- 拥有 GitHub 账号
- 了解基本的 Git 命令

## Fork 原始仓库

1. 访问您想要贡献的项目仓库页面
2. 点击右上角的 "Fork" 按钮
3. 选择将仓库 Fork 到您的个人账号下

这将在您的 GitHub 账号下创建一个原始仓库的副本。

## 克隆 Fork 仓库到本地

```bash
git clone https://github.com/您的用户名/仓库名.git
cd 仓库名
```

## 设置上游仓库

为了保持您的 Fork 与原始仓库同步，需要添加原始仓库作为远程上游仓库：

```bash
git remote add upstream https://github.com/原始作者/仓库名.git
```

验证远程仓库设置：

```bash
git remote -v
```

您应该能看到 `origin`（您的 Fork）和 `upstream`（原始仓库）。

## 创建分支

始终在新的分支上进行修改，而不是直接在 main/master 分支上工作：

```bash
git checkout -b feature-branch-name
```

分支名应该简洁地描述您的修改，例如 `fix-login-bug` 或 `add-new-feature`。

## 修改代码

在您的分支上进行必要的代码修改。确保您的修改：

- 遵循项目的代码风格和规范
- 解决特定问题或添加有价值的功能
- 包含适当的测试（如果项目有测试框架）
- 不包含不必要的文件或更改

## 提交更改

添加您修改的文件到暂存区：

```bash
git add .
```

提交更改，附带清晰的提交信息：

```bash
git commit -m "简洁描述您的更改"
```

好的提交信息应该：
- 简洁明了
- 使用现在时态（"Fix bug"而不是"Fixed bug"）
- 描述做了什么以及为什么做，而不是如何做

## 推送到远程仓库

将您的分支推送到您的 GitHub Fork 仓库：

```bash
git push origin feature-branch-name
```

## 创建 Pull Request

1. 访问您的 Fork 仓库页面
2. 您应该会看到一个提示，显示您最近推送了一个分支，并提供创建 Pull Request 的按钮
3. 点击 "Compare & pull request" 按钮

如果没有看到上述提示：
1. 点击 "Pull requests" 标签
2. 点击 "New pull request" 按钮
3. 选择正确的分支：
   - base repository：原始仓库
   - base：通常是 main 或 master 分支
   - head repository：您的 Fork
   - compare：您的功能分支

4. 填写 PR 信息：
   - 标题：简洁描述您的更改
   - 描述：详细说明您所做的修改，包括：
     - 修改了什么
     - 为什么进行这些修改
     - 如何测试这些修改
     - 相关的 issue 编号（如果有）

5. 点击 "Create pull request" 按钮提交 PR

## 跟进 PR 状态

提交 PR 后：

1. 项目维护者会审核您的代码
2. 他们可能会提出修改建议或直接合并您的 PR
3. 保持关注 PR 页面上的评论和状态变化
4. 及时回应维护者的评论和建议

## 如何查看 PR 是否被采纳

有几种方法可以查看您的 PR 是否被采纳（合并）：

### 在 GitHub 网站上查看

1. 访问原始仓库的 Pull Requests 页面
2. 找到您提交的 PR（可以通过筛选器选择 "Closed" 状态的 PR）
3. 查看 PR 的状态标签：
   - 如果显示紫色的 "Merged" 标签，表示您的 PR 已被采纳并合并
   - 如果显示红色的 "Closed" 标签但没有合并，表示 PR 被关闭但未被采纳

### 查看 PR 详情页面

1. 点击进入您的 PR 详情页面
2. 在 PR 页面顶部会显示 PR 的状态：
   - 如果显示 "[用户名] merged [您的分支] into [目标分支] [时间]"，表示 PR 已被合并
   - 如果显示 "This pull request is closed" 但没有合并信息，表示 PR 被关闭但未被采纳

### 通过命令行检查

您也可以通过命令行检查原始仓库的主分支是否包含您的提交：

```bash
# 获取上游仓库的最新更改
git fetch upstream

# 检查上游仓库的主分支日志
git log upstream/main
```

查看日志中是否包含您的提交信息。

## 更新 PR

如果您需要对 PR 进行更新（例如，根据维护者的反馈进行修改）：

1. 在本地切换到您的功能分支：
   ```bash
   git checkout feature-branch-name
   ```

2. 进行必要的修改

3. 添加并提交更改：
   ```bash
   git add .
   git commit -m "根据反馈进行修改"
   ```

4. 推送到同一分支：
   ```bash
   git push origin feature-branch-name
   ```

5. PR 会自动更新，无需创建新的 PR

## 常见问题

### 如何解决合并冲突？

如果您的 PR 显示有合并冲突：

1. 将上游仓库的主分支合并到您的功能分支：
   ```bash
   git fetch upstream
   git checkout feature-branch-name
   git merge upstream/main
   ```

2. 解决冲突，然后提交并推送更改：
   ```bash
   git add .
   git commit -m "解决合并冲突"
   git push origin feature-branch-name
   ```

### 如何同步 Fork 仓库与原始仓库？

定期同步您的 Fork 与原始仓库：

```bash
git fetch upstream
git checkout main
git merge upstream/main
git push origin main
```

### PR 被拒绝怎么办？

如果您的 PR 被拒绝：
1. 仔细阅读维护者提供的拒绝原因
2. 考虑是否可以按照反馈进行修改
3. 如果确实需要这个功能，可以考虑在自己的 Fork 中维护这个功能

### 如何关闭一个 PR？

如果您决定不再继续这个 PR：
1. 在 PR 页面底部找到 "Close pull request" 按钮
2. 可以选择添加关闭原因的评论

---

记住，提交高质量的 PR 不仅有助于项目的发展，也是提升自己技能和在开源社区建立声誉的好方法。祝您贡献顺利！