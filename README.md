# 飘投资 · P-Investing 研究库

个人投资研究的永久知识库网站，并带有自动更新的美股动量追踪工具。
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

## AI 行业景气度每周监测

网站会在每周一 07:15（新加坡时间）自动生成一期 AI 行业景气度周报，保留历史快照，并重建 GitHub Pages 数据。自动化入口是 `.github/workflows/ai-weekly.yml`，核心口径和数据源位于 `tools/ai_weekly_sources.json`。

本地可用以下命令复现：

```
python tools/ai_weekly_tracker.py
python build.py
```

自动抓取包括 GPU 云报价、SEC 财务数据、OpenRouter 模型目录、Hugging Face 下载量、GitHub 开源项目和市场风险指标。电话会中的 CapEx 指引、RPO、付费席位、HBM 长约、大集群真实成交价和通电 MW 保留为人工复核项；来源失效时会在周报中明确标记，不静默填充未知数据。

## 动量追踪每日更新

网站导航提供两个独立入口：“10倍股雷达”和“动量移动追踪”。前者完整呈现 33 项增长、质量、估值、催化和结论指标，后者完整呈现 51 项现货、期权、期限、Gamma、波动和结论指标。页面支持代码/公司搜索、行业与信号筛选、分数/市值/估值/增速阈值、全字段排序、分页、行级明细和全字段 CSV 导出。

“10倍股雷达”内置使用指南、完整方法论和交互式权重实验室。研究优先级三项权重、经营质量五维权重及三类风险扣分均可调整，也可直接选择原版平衡、成长优先、质量优先或催化动量预设。浏览器会按当前权重即时重算全部股票的经营质量分、研究优先级分、状态和排名；参数只保存在当前设备的浏览器中，并会继续应用于后续每日更新的数据。

`.github/workflows/momentum-daily.yml` 会在每个美股交易日收盘后自动运行。数据由 `tools/momentum_tracker.py` 从公开的 Nasdaq 股票筛选器和 Yahoo Finance JSON 数据计算，不使用或保存任何第三方订阅账号、会话或付费附件。需要完整期权链、Gamma、Reddit 或分析师预期历史的指标会保留列位并显示“待授权源”，不会生成猜测值。可在本地复现：

```
python tools/momentum_tracker.py
```
