#!/usr/bin/env python3
"""
Git Batch Downloader - 批量下载 Git 仓库工具
支持 GitLab 和 GitHub 平台
"""

import sys
from pathlib import Path

# Add custom python-packages directory to path
python_packages = Path('D:/python-packages')
if python_packages.exists():
    sys.path.insert(0, str(python_packages))

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    print("Error: requests module not found. Install with: pip install requests")
    sys.exit(1)


class GitBatchDownloader:
    """Git 批量下载器"""

    def __init__(self, git_url, output_dir, token=None, depth=1):
        self.git_url = git_url.rstrip('/')
        self.output_dir = Path(output_dir).expanduser().resolve()
        self.token = token
        self.depth = depth
        self.platform = self._detect_platform()
        self.api_base = self._get_api_base()
        self.group_path = self._get_group_path()
        self.headers = {}
        if self.token:
            self.headers['Authorization'] = f'Bearer {self.token}'

    def _detect_platform(self):
        """检测 Git 平台类型"""
        parsed = urlparse(self.git_url)
        hostname = parsed.hostname

        if hostname and ('gitlab' in hostname or 'dfcfs' in hostname):
            return 'gitlab'
        elif hostname and 'github' in hostname:
            return 'github'
        else:
            raise ValueError(f"Unsupported Git platform: {hostname}")

    def _get_api_base(self):
        """获取 API 基础 URL"""
        parsed = urlparse(self.git_url)
        scheme = parsed.scheme
        hostname = parsed.hostname

        if self.platform == 'gitlab':
            return f"{scheme}://{hostname}/api/v4"
        elif self.platform == 'github':
            return f"{scheme}://api.{hostname}" if hostname != 'github.com' else 'https://api.github.com'
        return None

    def _get_group_path(self):
        """获取组路径"""
        parsed = urlparse(self.git_url)
        path = parsed.path.strip('/')
        return path

    def get_gitlab_projects(self):
        """获取 GitLab 组的所有项目（包括子组）"""
        projects = []
        groups_to_process = [self.group_path]
        processed_groups = set()

        print(f"[*] 正在获取 GitLab 组的项目列表: {self.group_path}")

        while groups_to_process:
            current_group = groups_to_process.pop(0)

            if current_group in processed_groups:
                continue
            processed_groups.add(current_group)

            # URL encode the group path
            from urllib.parse import quote
            encoded_group = quote(current_group, safe='')

            # 获取组的项目
            projects_url = f"{self.api_base}/groups/{encoded_group}/projects?per_page=100&include_subgroups=true"
            response = requests.get(projects_url, headers=self.headers)

            if response.status_code == 200:
                group_projects = response.json()
                for project in group_projects:
                    # 优先使用 HTTP URL，避免 SSH 主机密钥验证问题
                    http_url = project.get('http_url_to_repo') or project.get('ssh_url_to_repo')
                    # 如果有 token，将其嵌入到 URL 中
                    if self.token and http_url.startswith('http'):
                        http_url = http_url.replace('://', f'://oauth2:{self.token}@', 1)
                    projects.append({
                        'name': project['path_with_namespace'],
                        'url': http_url,
                        'group': current_group
                    })
                print(f"    [+] 从组 '{current_group}' 找到 {len(group_projects)} 个项目")
            else:
                print(f"    [!] 获取组 '{current_group}' 的项目失败: {response.status_code}")

            # 获取子组
            subgroups_url = f"{self.api_base}/groups/{encoded_group}/subgroups?per_page=100"
            response = requests.get(subgroups_url, headers=self.headers)

            if response.status_code == 200:
                subgroups = response.json()
                for subgroup in subgroups:
                    groups_to_process.append(subgroup['full_path'])

        return projects

    def get_github_projects(self):
        """获取 GitHub 组织的所有仓库"""
        projects = []
        org = self.group_path.split('/')[0]

        print(f"[*] 正在获取 GitHub 组织的仓库列表: {org}")

        page = 1
        while True:
            repos_url = f"{self.api_base}/orgs/{org}/repos?per_page=100&page={page}"
            response = requests.get(repos_url, headers=self.headers)

            if response.status_code != 200:
                print(f"    [!] 获取仓库列表失败: {response.status_code}")
                break

            repos = response.json()
            if not repos:
                break

            for repo in repos:
                # 优先使用 clone_url (HTTP)
                clone_url = repo.get('clone_url') or repo.get('ssh_url')
                # 如果有 token，将其嵌入到 URL 中
                if self.token and clone_url.startswith('http'):
                    clone_url = clone_url.replace('://', f'://oauth2:{self.token}@', 1)
                projects.append({
                    'name': repo['full_name'],
                    'url': clone_url,
                    'group': org
                })

            print(f"    [+] 第 {page} 页找到 {len(repos)} 个仓库")
            page += 1

        return projects

    def get_projects(self):
        """获取所有项目列表"""
        if self.platform == 'gitlab':
            return self.get_gitlab_projects()
        elif self.platform == 'github':
            return self.get_github_projects()
        return []

    def clone_project(self, project):
        """克隆或更新单个项目"""
        repo_name = project['name'].replace('/', '_')
        repo_path = self.output_dir / repo_name

        if repo_path.exists():
            # 项目已存在，检查是否有更新
            print(f"    [~] 检查更新: {repo_name}")

            try:
                # 先执行 git fetch 检查远程更新
                os.chdir(repo_path)
                fetch_cmd = 'git fetch --dry-run origin 2>&1'
                fetch_result = subprocess.run(
                    fetch_cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                # 检查是否有可用的更新
                has_update = fetch_result.stdout.strip() != '' or fetch_result.stderr.strip() != ''

                if has_update:
                    print(f"    [↓] 发现更新，正在拉取: {repo_name}")
                    pull_cmd = 'git pull origin'
                    pull_result = subprocess.run(
                        pull_cmd,
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=300
                    )

                    if pull_result.returncode == 0:
                        print(f"    [OK] 更新成功: {repo_name}")
                        return True
                    else:
                        print(f"    [X] 更新失败: {repo_name} - {pull_result.stderr.strip()}")
                        return False
                else:
                    print(f"    [=] 已是最新: {repo_name}")
                    return True

            except subprocess.TimeoutExpired:
                print(f"    [X] 更新超时: {repo_name}")
                return False
            except Exception as e:
                print(f"    [X] 更新错误: {repo_name} - {e}")
                return False
            finally:
                os.chdir(self.output_dir)

        try:
            print(f"    [>] 克隆中: {repo_name}")
            depth_arg = f'--depth {self.depth}' if self.depth > 0 else ''
            cmd = f'git clone {depth_arg} "{project["url"]}" "{repo_path}"'

            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=600  # 10分钟超时
            )

            if result.returncode == 0:
                print(f"    [OK] 克隆成功: {repo_name}")
                return True
            else:
                print(f"    [X] 克隆失败: {repo_name} - {result.stderr.strip()}")
                return False

        except subprocess.TimeoutExpired:
            print(f"    [X] 超时: {repo_name}")
            return False
        except Exception as e:
            print(f"    [X] 错误: {repo_name} - {e}")
            return False

    def run(self):
        """执行批量下载"""
        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)

        print(f"[Git Batch Downloader]")
        print(f"平台: {self.platform}")
        print(f"URL: {self.git_url}")
        print(f"输出目录: {self.output_dir}")
        print(f"克隆深度: {self.depth if self.depth > 0 else '完整'}")
        print("-" * 50)

        # 获取项目列表
        projects = self.get_projects()

        if not projects:
            print("[!] 未找到任何项目")
            return False

        print(f"\n[*] 共找到 {len(projects)} 个项目")
        print("-" * 50)

        # 批量克隆
        success_count = 0
        failed_count = 0

        for i, project in enumerate(projects, 1):
            print(f"\n[{i}/{len(projects)}] {project['name']}")
            if self.clone_project(project):
                success_count += 1
            else:
                failed_count += 1

        # 输出总结
        print("\n" + "=" * 50)
        print(f"[完成] 成功: {success_count}, 失败: {failed_count}, 总计: {len(projects)}")
        print(f"输出目录: {self.output_dir}")

        return failed_count == 0


def main():
    parser = argparse.ArgumentParser(
        description='Git Batch Downloader - 批量下载 Git 仓库',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 下载 GitLab 组的所有项目
  %(prog)s https://gitlab.example.com/my-group d:/projects

  # 下载 GitHub 组织的所有项目（使用 token）
  %(prog)s https://github.com/organization d:/projects --token YOUR_TOKEN

  # 浅克隆（仅最新提交）
  %(prog)s https://gitlab.com/group d:/projects --depth 1
        '''
    )

    parser.add_argument('git_url', help='Git 组/组织的 URL')
    parser.add_argument('output_dir', help='本地输出目录')
    parser.add_argument('--token', help='访问私有仓库的认证 token')
    parser.add_argument('--depth', type=int, default=1, help='浅克隆深度（0=完整克隆，默认:1）')

    args = parser.parse_args()

    try:
        downloader = GitBatchDownloader(
            args.git_url,
            args.output_dir,
            token=args.token,
            depth=args.depth
        )
        success = downloader.run()
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n[!] 用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"[!] 错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
