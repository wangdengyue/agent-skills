---
name: git-batch-downloader
description: "Batch Git repository downloader for downloading all projects from a Git organization/group to a local directory. Use when user asks to: (1) Download all projects from a Git organization/group, (2) Batch clone multiple Git repositories, (3) Download GitLab/GitHub group projects including subgroups, (4) Clone all repos from a Git URL, (5) Update existing local repositories with latest changes. Examples: Help me download all projects from https://gitlab.example.com/my-group, Clone all projects from this GitLab group to d:/projects, Update all projects in d:/projects."
---

# Git Batch Downloader

批量下载 Git 仓库工具，支持从 GitLab/GitHub 等平台的组织/组下载所有项目到本地目录，并支持更新已有项目。

## Quick Start

使用 Python 脚本批量下载或更新：

```bash
python scripts/batch_clone.py <git-url> <output-dir>
```

### 示例

```bash
# 下载 GitLab 组的所有项目
python scripts/batch_clone.py https://gitlab.example.com/my-group d:/projects

# 更新已有项目（检查并拉取最新代码）
python scripts/batch_clone.py https://gitlab.example.com/my-group d:/projects

# 下载 GitHub 组织的所有项目
python scripts/batch_clone.py https://github.com/organization d:/projects
```

## 工作流程

1. **检测 Git 平台**: 自动识别 GitLab 或 GitHub
2. **获取项目列表**: 通过 API 获取组/组织下的所有项目（包括子组/子项目）
3. **智能处理**:
   - **新项目**: 使用 `git clone` 下载到指定目录
   - **已有项目**: 检查更新并执行 `git pull` 获取最新代码
4. **进度显示**: 实时显示下载/更新进度

## 脚本参数

`batch_clone.py` 接受以下参数：

- `git-url`: Git 组/组织的 URL
- `output-dir`: 本地输出目录
- `--token`: 可选，访问私有仓库的认证 token
- `--depth`: 可选，浅克隆深度（默认：1，仅对新项目生效）

## 输出标识

- `[>]` - 正在克隆新项目
- `[~]` - 检查已有项目更新
- `[↓]` - 发现更新，正在拉取
- `[=]` - 已是最新版本
- `[OK]` - 操作成功
- `[X]` - 操作失败

## 注意事项

- 确保已安装 `git` 命令行工具
- 对于私有项目，需要提供访问 token
- 大量项目下载/更新可能需要较长时间
- 已有项目会自动检查更新并拉取最新代码
