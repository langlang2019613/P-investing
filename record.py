# -*- coding: utf-8 -*-
"""
record.py — 一条命令把新写的研究笔记发布到网站。

流程: 校验并构建 data.json -> git add/commit -> git push（手机端随即可同步）。

用法:
    python record.py              构建 + 提交 + 推送
    python record.py --no-push    只构建和本地提交，不推送
"""
import subprocess
import sys
from pathlib import Path

# Windows 控制台默认 cp1252/gbk，中文输出会崩
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent


def run(*args, check=True):
    r = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    if check and r.returncode != 0:
        print(f"命令失败: {' '.join(args)}\n{r.stdout}{r.stderr}")
        sys.exit(1)
    return r


def main():
    no_push = "--no-push" in sys.argv

    # 1. 构建（含 frontmatter 校验，失败则中止）
    r = subprocess.run([sys.executable, str(ROOT / "build.py")], cwd=ROOT)
    if r.returncode != 0:
        sys.exit(1)

    # 2. 提交
    run("git", "add", "-A")
    status = run("git", "status", "--porcelain").stdout.strip()
    if not status:
        print("没有新改动，无需提交。")
    else:
        changed = [l[3:] for l in status.splitlines() if l[3:].startswith("content/")]
        title = changed[0].split("/")[-1] if changed else "site update"
        msg = f"record: {title}" + (f" (+{len(changed)-1} more)" if len(changed) > 1 else "")
        run("git", "commit", "-m", msg)
        print(f"已提交: {msg}")

    # 3. 推送
    if no_push:
        print("跳过推送 (--no-push)。")
        return
    remotes = run("git", "remote").stdout.strip()
    if not remotes:
        print("尚未配置 GitHub 远程仓库，本次只保存在本地。")
        print("配置方法见 README.md 的「发布到 GitHub Pages」一节。")
        return
    r = run("git", "push", check=False)
    if r.returncode == 0:
        print("已推送到 GitHub，手机端联网后即可看到更新。")
    else:
        print(f"推送失败（内容已在本地提交，不会丢失）:\n{r.stderr.strip()}")


if __name__ == "__main__":
    main()
