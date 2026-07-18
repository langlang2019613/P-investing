# 飘投资 · P-Investing 研究库

个人投资研究的永久知识库网站。五大分类：公司 / 行业 / 期权 / 宏观 / 经济历史。
全文搜索，手机可安装（PWA），离线可查。

## 日常用法

在 Claude Code 或 Codex 里做完分析后说一句 **「记录到网站」**，AI 会按
[CLAUDE.md](CLAUDE.md) / [AGENTS.md](AGENTS.md) 里的规则把内容写入
`content/<分类>/` 并运行 `python record.py` 发布。

手动操作也一样：写 md 文件 → `python record.py`。

## 本地预览

```
python build.py
python -m http.server 8000 -d docs
# 打开 http://localhost:8000
```

## 发布到 GitHub Pages（一次性设置）

1. 在 github.com 新建仓库 `p-investing`（Private 也可以，但 Pages 网站本身公开）
2. 本目录下执行：
   ```
   git remote add origin https://github.com/<你的用户名>/p-investing.git
   git push -u origin main
   ```
   首次推送会弹出浏览器登录 GitHub 授权。
3. 仓库页面 → Settings → Pages → Source 选 `Deploy from a branch`，
   Branch 选 `main`，目录选 `/docs`，保存。
4. 一两分钟后网站上线：`https://<你的用户名>.github.io/p-investing/`

## 手机安装（一次性）

- **iPhone**：Safari 打开网站 → 分享 → 添加到主屏幕
- **Android**：Chrome 打开网站 → 菜单 → 安装应用

安装后图标出现在桌面，联网打开会自动同步最新内容；之后**没有网络也能
打开查询**（显示最后一次同步的全部内容，搜索也可用）。

## 结构

```
content/          研究笔记（Markdown + frontmatter），永久档案
  companies/      公司基本面、动态数据、新闻
  industries/     行业研究
  options/        期权研究
  macro/          宏观经济
  history/        经济历史
build.py          content → docs/data.json，并更新离线缓存版本
record.py         构建 + git 提交 + 推送（= 发布）
docs/             网站本体（GitHub Pages 从这里发布）
```
