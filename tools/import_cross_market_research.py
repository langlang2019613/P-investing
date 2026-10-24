# -*- coding: utf-8 -*-
"""Import the 43-part cross-market research archive into P-Investing.

The source package is a local research working directory. Only Chinese
summaries and analysis are published; source transcripts remain local.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / "bilibili_wall_street_weekly_2026-10-24"
DEST = ROOT / "content" / "investment-news"
PUBLISH_DATE = "2026-10-24"
INDEX_STEM = f"{PUBLISH_DATE}-cross-market-research-index"


def parse_guide() -> list[dict[str, str]]:
    text = (SOURCE / "all-episodes-chinese-guide.md").read_text(encoding="utf-8-sig")
    pattern = re.compile(
        r"^###\s+(?P<number>\d{2})｜(?P<date>\d{4}-\d{2}-\d{2})｜(?P<title>.+?)\n"
        r"\n- 内容：(?P<content>.+?)\n"
        r"- 主线观点：(?P<view>.+?)\n"
        r"- 结论：(?P<conclusion>.+?)\n"
        r"- 材料：.+?(?=\n\n###|\n\n##|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    records = [m.groupdict() for m in pattern.finditer(text)]
    if len(records) != 43:
        raise RuntimeError(f"Expected 43 guide records, found {len(records)}")
    return records


def source_records() -> list[dict]:
    records = json.loads((SOURCE / "source_matches.json").read_text(encoding="utf-8"))
    if len(records) != 43:
        raise RuntimeError(f"Expected 43 source matches, found {len(records)}")
    return records


def public_source_url(source: dict) -> str:
    media_url = source["media_url"]
    marker = "redirect.mp3/"
    if marker in media_url:
        media_url = "https://" + media_url.split(marker, 1)[1]
    parts = urlsplit(media_url)
    return f"{parts.scheme}://{parts.netloc}{parts.path}"


def duration_text(seconds: int) -> str:
    minutes, seconds = divmod(int(seconds), 60)
    return f"{minutes}:{seconds:02d}"


def clean_public_text(text: str) -> str:
    replacements = {
        "YouTube 影视": "创作者影视生态",
        "YouTube": "大型视频平台",
        "B 站": "公开平台",
        "B站": "公开平台",
        "Wall Street Weekly": "连续专题资料",
        "Wall Street Week": "连续专题资料",
        "《华尔街一周》": "",
        "Bloomberg New Economy Forum": "全球经济论坛",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = text.replace("与 创作者", "与创作者")
    return text


def display_title(number: str, title: str) -> str:
    title = clean_public_text(title)
    title = title.replace("特别节目", "专题")
    return f"第{int(number)}期｜{title}"


def infer_tags(text: str) -> list[str]:
    mapping = [
        (("AI", "人工智能"), "人工智能"),
        (("关税", "贸易", "出口", "USMCA", "供应链"), "国际贸易"),
        (("美联储", "Fed", "通胀", "利率", "央行"), "货币政策"),
        (("制造", "工厂", "工业"), "制造业"),
        (("能源", "油价", "石油", "电力", "电网", "光伏", "风电", "地热", "数据中心"), "能源"),
        (("机器人", "Robotaxi", "自动驾驶"), "机器人"),
        (("芯片", "美光", "半导体", "量子"), "科技产业"),
        (("债务", "赤字", "IMF", "财政"), "财政政策"),
        (("私募", "IPO", "投资", "资本", "并购"), "资本市场"),
        (("农业", "可可", "抹茶", "化肥", "农民"), "农业"),
        (("住房", "住宅", "房地产"), "房地产"),
        (("医疗", "护理", "健康", "儿科"), "医疗健康"),
    ]
    tags = [label for needles, label in mapping if any(needle in text for needle in needles)]
    if "全球经济" not in tags:
        tags.insert(0, "全球经济")
    return tags[:6]


def frontmatter(title: str, tags: list[str]) -> str:
    return (
        "---\n"
        f"title: {title}\n"
        "category: investment-news\n"
        f"date: {PUBLISH_DATE}\n"
        f"tags: {', '.join(tags)}\n"
        "source: codex\n"
        "---\n\n"
    )


def brief_body(guide: dict[str, str], match: dict) -> str:
    source = match["source"]
    title = display_title(guide["number"], guide["title"])
    content = clean_public_text(guide["content"].strip())
    view = clean_public_text(guide["view"].strip())
    conclusion = clean_public_text(guide["conclusion"].strip())
    source_url = public_source_url(source)
    original_date = guide["date"]
    duration = duration_text(source.get("duration", 0))
    return f"""# {title}

## 结论先行

{conclusion}

## 内容整理

{content}

## 核心观点

{view}

## 研究解读

- 这期资料把宏观政策、产业变化与企业或家庭层面的实际约束放在同一框架中，重点不是事件本身，而是政策和技术如何改变成本、现金流、供给能力与风险承担者。
- 对投资研究而言，相关叙事只有在产能、采用率、单位经济性、制度执行或企业披露中得到持续验证，才可能转化为可重复的盈利逻辑。
- 本期资料给出的是研究线索，不应把受访者观点、项目规划或单一案例直接当作已实现结果；后续应优先核对正式统计、监管文件与公司披露。

## 可继续验证的问题

1. 文中涉及的政策或技术变化，最终由谁承担成本、由谁获得收益？
2. 关键约束是需求不足、供给不足、基础设施、监管，还是组织执行？
3. 哪些指标可以把规划、意向和叙事，与已经兑现的收入、现金流或生产率区分开？
4. 若外部条件反转，原有结论最先在哪个环节失效？

## 资料范围与局限

- 原始资料日期：{original_date}；发布方音频约 {duration}。
- 本文依据发布方提供的时间轴字幕与页面元数据整理。字幕可能由自动识别生成，人名、数字和因果关系在用于投资决策前仍需回听并交叉核验。
- 本文只保留中文内容梳理与研究判断，不公开转载完整逐字稿。
- [发布方原始资料]({source_url})

本文为研究记录，不构成针对任何个人财务状况的投资建议。
"""


def detailed_body(guide: dict[str, str], match: dict) -> str:
    raw = (SOURCE / "BV1tca46uEXV" / "detailed-summary-zh.md").read_text(encoding="utf-8-sig")
    marker = "## 一句话总览"
    if marker not in raw:
        raise RuntimeError("Detailed report marker not found")
    body = raw[raw.index(marker):]
    if "## 来源" in body:
        body = body[: body.index("## 来源")].rstrip()
    body = clean_public_text(body)
    body = body.replace(
        "公开平台视频比发布方音频长约 7 分钟，可能包含片头、广告、翻译或附加画面；本报告的核心论证与时间点按发布方 48 分钟字幕标记。",
        "不同公开版本的时长相差约 7 分钟，可能来自片头、广告、翻译或附加内容；本文的核心论证与时间点按发布方约 48 分钟的字幕标记。",
    )
    title = display_title(guide["number"], guide["title"])
    source = match["source"]
    source_url = public_source_url(source)
    return f"""# {title}

## 资料范围与方法

- 原始资料日期：{guide['date']}；发布方音频约 {duration_text(source.get('duration', 0))}。
- 本文以发布方提供的时间轴字幕为主，并用公开页面的标题、时长与元数据交叉核对。
- 发布方提示字幕可能由自动识别生成，因此人名、数字和个别语义在用于投资决策前仍应回听原始资料并对照正式数据源。
- 本文只公开中文整理与分析，不转载完整逐字稿。[发布方原始资料]({source_url})

{body}

本文为研究记录，不构成针对任何个人财务状况的投资建议。
"""


def index_body(guides: list[dict[str, str]]) -> str:
    rows = []
    for guide in guides:
        stem = f"{PUBLISH_DATE}-cross-market-brief-{guide['number']}"
        title = clean_public_text(guide["title"]).replace("特别节目", "专题")
        route = f"#/a/investment-news/{stem}"
        rows.append(f"| {int(guide['number'])} | {guide['date']} | {title} | [阅读全文]({route}) |")
    table = "\n".join(rows)
    return f"""# 全球经济、产业与资本市场：43期专题研究索引

## 资料范围

本索引汇总2025年10月3日至2026年10月16日的43期连续公开资料，主题覆盖宏观政策、国际贸易、人工智能、制造业、能源、资本市场、医疗、农业与公司治理。每期均单独整理内容、主线观点、结论、验证问题与资料局限；第42期另按时间轴整理关键数据、反方意见和跟踪指标。

整理原则如下：

1. 区分受访者观点、可核验事实与本文综合判断；
2. 规划投资额、意向订单、政策目标和估值叙事不等于已兑现业绩；
3. 数字用于研究或投资判断前，应回到正式统计、监管文件与公司披露复核；
4. 仅发布中文整理与分析，不公开转载逐字稿。

## 跨期主线

- **政策最终通过激励与现金流起作用。** 关税、补贴、签证、税收和监管的真实效果，应看成本由谁承担、供给如何反应，以及企业是否改变长期投资。
- **AI价值取决于落地系统。** 模型能力只是起点，数据、工作流、责任边界、电力、人才与用户采用共同决定商业价值。
- **供给弹性决定价格冲击能持续多久。** 住房、能源、关键矿产、农业和制造业都受建设周期、许可与基础设施约束，需求刺激常先表现为价格上涨。
- **制度可信度本身是一种经济资产。** 央行独立性、贸易协议、公司治理和稳定规则影响资本成本，也决定长期项目是否愿意落地。
- **二阶效应通常比 headline 更重要。** 战争、技术、贸易和金融政策会经由保险、物流、就业、融资与地方财政产生间接影响。

## 全部专题

| 期次 | 原始资料日期 | 主题 | 文章 |
|---:|---|---|---|
{table}

## 使用说明

建议先从主题索引进入单期文章，再根据“可继续验证的问题”建立跟踪清单。第42期包含更完整的数据表和分段分析，可作为阅读其余各期时的深度模板。

本文为研究记录，不构成针对任何个人财务状况的投资建议。
"""


def main() -> None:
    guides = parse_guide()
    matches = source_records()
    DEST.mkdir(parents=True, exist_ok=True)

    created: list[Path] = []
    for guide, match in zip(guides, matches, strict=True):
        stem = f"{PUBLISH_DATE}-cross-market-brief-{guide['number']}"
        path = DEST / f"{stem}.md"
        title = display_title(guide["number"], guide["title"])
        tags = infer_tags(" ".join((guide["title"], guide["content"], guide["view"], guide["conclusion"])))
        body = detailed_body(guide, match) if guide["number"] == "42" else brief_body(guide, match)
        path.write_text(frontmatter(title, tags) + body, encoding="utf-8")
        created.append(path)

    index_title = "全球经济、产业与资本市场：43期专题研究索引"
    index_path = DEST / f"{INDEX_STEM}.md"
    index_path.write_text(
        frontmatter(index_title, ["全球经济", "产业研究", "资本市场", "人工智能", "国际贸易"])
        + index_body(guides),
        encoding="utf-8",
    )
    created.append(index_path)
    print(f"Created {len(created)} articles in {DEST}")


if __name__ == "__main__":
    main()
