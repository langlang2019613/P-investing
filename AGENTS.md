# 飘投资研究库 (P-Investing Research Vault)

个人投资研究的永久知识库。内容以 Markdown 存于 `content/`，`build.py` 编译为
`docs/data.json`，`docs/` 是静态 PWA 网站（GitHub Pages 发布，手机可安装、可离线）。

## 记录指令（重要）

当用户说「记录到网站」「存到飘投资」「保存这次分析」等，执行：

1. 把本次分析/总结整理成完整 Markdown，保存为：
   `content/<分类>/YYYY-MM-DD-<英文短slug>.md`

   分类目录（八选一）：
   - `companies`  公司基本面研究、动态数据、个股新闻
   - `industries` 行业研究
   - `options`    期权研究
   - `macro`      宏观经济研究
   - `reports`    研报分析（投行/机构研报的摘要与解读）
   - `learning`   学习（课程笔记、方法论、框架、技能积累）
   - `books`      书刊笔记（书籍与杂志的阅读笔记）
   - `history`    经济历史

   注意：网站内容不出现「5+2」提法（统一用 18维度），不出现视频平台
   （B站/YouTube等）及其博主/栏目名称，也不出现「视频总结」等字样。

2. 文件开头必须有 frontmatter：

   ```
   ---
   title: 中文标题（简洁说明主题）
   category: companies
   date: 2026-07-18
   tickers: NVDA, TSM
   tags: 财报, AI, 估值
   source: claude
   ---
   ```

   - `tickers`/`tags` 可省略；`source` 填 claude 或 codex
   - date 用当天日期，格式 YYYY-MM-DD

3. 运行 `python record.py`（在本目录下）。它会构建、提交并推送到 GitHub，
   手机端自动同步。若推送失败内容也已在本地提交，不会丢。

## 内容要求

- 保存**完整**的分析内容，不要压缩成几句话——这是永久档案，详细为佳
- 正文用标准 Markdown：小标题、表格、列表都支持
- 同一主题的后续更新写新文件（按日期），不要覆盖旧文件——保留研究演进过程

## 其他命令

- `python build.py` — 只构建不提交（本地预览用）
- 本地预览：`python -m http.server 8000 -d docs` 然后开 http://localhost:8000
