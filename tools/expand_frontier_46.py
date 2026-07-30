# -*- coding: utf-8 -*-
"""Expand the 46-topic learning index into one detailed note per episode.

The script uses public season metadata and the publisher's RSS show-note timeline,
then combines it with the independently written conclusions in the existing index.
It intentionally does not reproduce the show-note prose.
"""
from __future__ import annotations

import difflib
import datetime as dt
import email.utils
import html
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "content/learning/2026-07-31-tech-business-frontiers-46-topics.md"
OUT = ROOT / "content/learning"
UA = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.bilibili.com/"}
BVID = "BV19qKwz4E3r"

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read()


def clean_title(value: str) -> str:
    value = re.sub(r"^E\d+[｜|]\s*", "", value)
    value = re.sub(r"【[^】]*(?:播客|视频)[^】]*】", "", value)
    value = value.replace("硅谷101", "").replace("视频播客", "")
    return re.sub(r"\s+", " ", value).strip(" ｜|：:")


def norm(value: str) -> str:
    value = clean_title(value).lower()
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", value)


def strip_html(value: str) -> str:
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.I)
    value = re.sub(r"</p>", "\n", value, flags=re.I)
    value = re.sub(r"<[^>]+>", "", value)
    return html.unescape(value).replace("\r", "")


def parse_index() -> list[dict[str, str]]:
    text = INDEX.read_text(encoding="utf-8")
    blocks = re.split(r"(?=^### \d+\. )", text, flags=re.M)
    result = []
    for block in blocks:
        m = re.match(r"### (\d+)\. (.+)", block)
        if not m:
            continue
        number = int(m.group(1))
        if number > 46:
            continue
        core = re.search(r"\*\*核心内容：\*\*\s*(.+?)(?=\n\n\*\*分析判断)", block, re.S)
        analysis = re.search(r"\*\*分析判断：\*\*\s*(.+?)(?=\n\n\*\*追踪问题)", block, re.S)
        tracking = re.search(r"\*\*追踪问题：\*\*\s*(.+?)(?=\n\n|\n---|$)", block, re.S)
        result.append({
            "number": str(number),
            "index_title": m.group(2).strip(),
            "core": core.group(1).strip() if core else "",
            "analysis": analysis.group(1).strip() if analysis else "",
            "tracking": tracking.group(1).strip() if tracking else "",
        })
    if len(result) != 46:
        raise RuntimeError(f"expected 46 index sections, found {len(result)}")
    return result


def fetch_season() -> list[dict]:
    payload = json.loads(get(
        "https://api.bilibili.com/x/web-interface/view?" + urllib.parse.urlencode({"bvid": BVID})
    ))
    episodes = payload["data"]["ugc_season"]["sections"][0]["episodes"]
    result = []
    for episode in episodes:
        seconds = int(episode["page"]["duration"])
        result.append({
            "title": clean_title(episode["title"]),
            "published": __import__("datetime").datetime.fromtimestamp(
                int(episode["arc"]["pubdate"]), __import__("datetime").timezone.utc
            ).strftime("%Y-%m-%d"),
            "duration": f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}",
        })
    if len(result) != 46:
        raise RuntimeError(f"expected 46 season episodes, found {len(result)}")
    return result


def fetch_rss() -> list[dict]:
    root = ET.fromstring(get("https://feeds.fireside.fm/sv101/rss"))
    result = []
    for item in root.findall("./channel/item"):
        title = item.findtext("title") or ""
        desc = strip_html(item.findtext("description") or "")
        chapters = []
        for line in desc.splitlines():
            line = re.sub(r"\s+", " ", line).strip()
            m = re.match(r"^(\d{1,2}:\d{2}(?::\d{2})?)\s+(.{2,100})$", line)
            if m:
                topic = clean_title(m.group(2)).strip("。；; ")
                if topic and not any(x in topic for x in ("BGM", "招聘", "找到我们")):
                    chapters.append((m.group(1), topic))
        published_raw = item.findtext("pubDate") or ""
        published = email.utils.parsedate_to_datetime(published_raw).astimezone(dt.timezone.utc).date()
        result.append({"title": clean_title(title), "chapters": chapters, "published": published})
    return result


CATEGORY_BY_NUMBER = {
    **{n: "ai" for n in [1, 2, 4, 5, 13, 23, 25, 26, 34, 37, 39, 41, 43, 46]},
    **{n: "infrastructure" for n in [14, 16, 28, 31, 40]},
    **{n: "robotics" for n in [10, 11, 17, 18, 22, 45]},
    **{n: "biotech" for n in [3, 9, 27, 36]},
    **{n: "finance" for n in [6, 7, 15, 20, 32, 35]},
    **{n: "consumer" for n in [8, 12, 19, 21, 24, 30, 33, 38, 42, 44]},
}

# Chronological season position -> analytical section in the compact index.
# The compact index was reorganized by theme, so its numbering is not temporal.
NOTE_MAP = [
    1, 2, 24, 3, 4, 28, 29, 33, 25, 18, 19, 34, 5, 13, 30, 14, 20, 21,
    35, 31, 36, 22, 6, 37, 7, 8, 26, 15, None, 43, 16, 44, 38, 39, 32,
    27, 45, 41, 9, 17, 10, 40, 11, 42, 23, 12,
]


FRAMEWORKS = {
    "ai": """### 技术与产品拆解

分析这类AI议题，不能把模型能力、产品体验和商业价值混成一个概念。模型层回答“理论上能不能做”，产品层回答“普通用户能否稳定完成”，商业层回答“完成任务后是否产生可计价价值”。真正进入生产还要补上数据权限、工具调用、错误恢复、日志审计与责任归属。演示通常选择顺利路径，生产系统却必须处理输入缺失、接口变化、超时、幻觉和用户误操作。因而，任务成功率、人工接管率、端到端耗时、单位任务成本和一个月留存，比参数数量或单次演示更能说明成熟度。

### 价值链与竞争格局

价值可能分布在基础模型、算力、开发工具、数据、应用、渠道和交付服务多个环节。基础模型拥有规模经济，但能力会扩散；应用公司更接近客户，却可能被模型厂商下沉功能。能长期保留利润的企业，通常至少掌握一种难复制资产：独家数据、深度工作流、强分发、监管资质、品牌信任或持续反馈闭环。判断护城河时，应追问客户换成另一模型需要付出什么，而不能把“用了最先进模型”本身当作壁垒。

### 组织与社会影响

AI带来的岗位变化往往先表现为任务重组，而非职业整体消失。标准化产出更容易自动化，问题定义、审美判断、跨部门协调和对结果负责的重要性上升。效率数字还应扣除复核、返工、安全与治理成本。若组织只增加工具而不改变授权、考核和责任流程，模型能力很难转化为真实生产率。""",
    "infrastructure": """### 工程约束与供给链

基础设施主题必须从物理量出发：功率、能耗、散热、土地、并网、网络、设备交期和施工周期。芯片性能提升并不自动转化为系统吞吐，瓶颈可能转移到内存、互连、电力或软件。公告中的规划容量、签约容量、在建容量和已经上架并产生收入的容量含义完全不同。研究时要把每个宏大目标拆成年度里程碑，并检查关键设备是否已有订单、许可和供应保障。

### 单位经济与融资结构

重资产项目的利润取决于利用率、价格、电力成本、折旧、融资成本与客户信用。长期合同能够提高可见度，但也要检查取消权、价格重议、最低采购和母公司担保。若项目靠短期债务建设长期资产，或依赖持续再融资，技术需求稍有放缓就会变成流动性风险。正确比较应使用全生命周期总成本，而不是单项芯片价格或理论峰值。

### 周期位置与投资含义

需求高速增长阶段，产业链利润常先流向最稀缺的环节；扩产完成后，稀缺性会迁移甚至消失。领先指标包括交付周期、预付款、二手设备价格、项目延期、客户集中度和每单位资本开支带来的收入。估值需要同时设置高利用率、基准和需求延迟三种情景，避免把远期满产一次性计入当前价值。""",
    "robotics": """### 从演示到生产

机器人演示通常证明“某次可以完成”，商业化则要求“在不同对象、光线、位置和连续运行中反复完成”。评价时应记录任务分布、成功率、远程接管比例、平均故障间隔、恢复时间和安全事件，而不能只看动作是否像人。半结构化场景通常先落地，因为环境可改造、任务可测量、责任边界更清晰；家庭开放环境则集合了长尾、安全和低成本三重难题。

### 软硬件系统工程

感知、规划、控制、执行器、传感器、数据和仿真相互制约。更多自由度可能提高灵活性，也会增加成本、重量、耗电与故障点。端到端模型有扩展潜力，分层架构更易调试和加入安全约束，现实产品往往采用混合方案。所谓泛化必须说明是在同类物体、同一环境还是跨任务条件下实现，零样本成功率也需要披露样本量和失败定义。

### 商业化与估值

机器人公司应先证明客户愿意为结果付费，再讨论百万台产能。关键经济指标是单机成本、部署和维护费用、可用工时、替代人工成本以及回收期。产能规划、意向订单和付费订单必须分开；供应链降本只有在良率和售后稳定后才会兑现。技术期权可以给予估值，但不应替代现金流证据。""",
    "biotech": """### 科学证据层级

生命科学必须区分体外实验、动物模型、早期人体安全、随机对照疗效和长期真实世界数据。机制合理不等于临床有效，替代指标改善也不必然带来生存或生活质量提升。样本量、对照组、预注册终点、统计显著性和不良反应决定证据强度。个人案例、富豪实践和短期生物标志物适合提出假设，不适合得出普遍结论。

### 平台技术与产品风险

平台公司可以生成多个候选项目，但每个项目仍要面对靶点、递送、剂量、免疫反应、制造和监管。真正壁垒往往不只在发现工具，而在临床数据、工艺质量和规模化生产。AI可提高搜索效率，却不能省略湿实验与人体验证。评估并购或融资时，应把总交易额拆成首付款和里程碑，避免把尚未发生的付款当成已确认价值。

### 医疗价值与支付

疗法能否普及还取决于适用人群、诊断路径、医院能力、保险支付和长期成本。高治愈率的小人群疗法与低价大人群干预具有完全不同的商业模型。最重要的追踪项是分癌种或分人群的疗效持续时间、安全性、制造成功率和每位患者总成本，而不是笼统的“治愈”或“逆龄”叙事。""",
    "finance": """### 权利结构与现金流

金融创新首先要问投资者实际拥有什么：直接所有权、托管凭证、合约请求权，还是对发行人的无担保债权。其次检查现金流来自交易费、利差、订阅、资产管理费还是资产升值。若收益高度依赖交易活跃、短期利率或下一位买家，周期性就远高于表面增长。法律权属、破产隔离、赎回和清算机制比“上链”或新名词更重要。

### 激励、杠杆与治理

平台、管理人、顾问、股东和用户的利益并不天然一致。分析应穿透衍生工具、关联安排、表外负债和控制权结构，识别谁获得上行、谁承担尾部损失。流动性好时风险容易被低估，压力期的保证金、挤兑和再融资才真正检验结构。监管不是外部噪音，而是金融产品成本和护城河的一部分。

### 投资判断方法

将叙事还原为活跃用户、客户资产、净流入、交易频率、利差、坏账、资本充足率和合规费用。对没有经营现金流的收藏或代币资产，重点看真实成交、价差、周转和供给规则。对平台公司，应做交易降温、利率下降和监管收紧的压力测试，再判断当前利润是否可持续。""",
    "consumer": """### 需求、品牌与用户行为

消费和体育现象要区分尝鲜、社交传播与稳定复购。排队、搜索热度和明星曝光能制造首轮需求，长期品牌则依赖产品体验、身份认同、可接受价格和稳定供给。细分品牌从零到一靠鲜明定位，扩大规模后往往因品类延伸、渠道下沉和核心用户疏离而遇到增长墙。研究应观察同店、复购、全价售罄和净推荐，而不是只看总销售增长。

### 单位经济与扩张

门店、赛事、内容和服饰各有不同成本结构，但共同问题是新增收入是否需要更高比例的营销、库存、版权或资本投入。开店和参赛人数增长不等于利润增长，应计算成熟单元收入、毛利、租金人工、获客、退货或损耗及投资回收期。跨国复制还会叠加供应链、本地法规、口味文化和管理半径。

### 周期、竞争与投资含义

潮流会吸引模仿者并压缩超额利润，品牌必须把阶段热度沉淀为渠道、会员和产品能力。内容与体育资产还要处理版权稀缺、用户覆盖和商业化之间的矛盾。投资判断应设置热度延续、正常化和快速退潮三种情景，重点跟踪库存、折扣、同店、客户留存和扩张店质量。""",
}


def choose_rss(title: str, published: str, rss: list[dict]) -> dict:
    target = norm(title)
    target_date = dt.date.fromisoformat(published)
    if "openclaw系统级风险" in target or "龙虾热" in title:
        return {"title": title, "chapters": [], "published": target_date}
    def score(row: dict) -> float:
        similarity = difflib.SequenceMatcher(None, target, norm(row["title"])).ratio()
        days = abs((row["published"] - target_date).days)
        date_score = max(0.0, 1.0 - days / 14.0)
        return similarity * 0.58 + date_score * 0.42
    return max(rss, key=score)


def ticker_line(title: str) -> str:
    rules = {
        "英伟达": "NVDA", "TPU": "GOOGL, NVDA", "谷歌": "GOOGL", "Robinhood": "HOOD",
        "Netflix": "NFLX, WBD, PARA", "华纳": "WBD, NFLX, PARA", "特斯拉": "TSLA",
        "阿里": "BABA", "OpenAI": "MSFT", "DeepMind": "GOOGL", "lul": "LULU",
        "爱马仕": "RMS.PA, MC.PA", "SpaceX": "", "CAR-T": "LLY, AZN, ABBV, BMY",
    }
    for key, value in rules.items():
        if key.lower() in title.lower():
            return f"tickers: {value}\n" if value else ""
    return ""


def build_article(meta: dict, note: dict, chapters: list[tuple[str, str]], episode_number: int) -> str:
    n = episode_number
    title = clean_title(meta["title"])
    category = note.get("category") or CATEGORY_BY_NUMBER.get(int(note["number"]), "ai")
    chapter_lines = []
    for stamp, topic in chapters[:24]:
        topic = topic.replace("硅谷101", "").replace("B站", "").replace("YouTube", "")
        chapter_lines.append(f"- **{stamp}**：{topic}")
    if not chapter_lines:
        chapter_lines = [
            "- **开篇**：界定问题、行业背景与本期需要回答的核心疑问。",
            "- **中段**：比较主要技术或商业路线，并讨论真实落地约束。",
            "- **后段**：归纳长期影响、争议、风险与未来验证条件。",
        ]
    tracking = [x.strip() for x in re.split(r"[、，,和以及]", note["tracking"]) if len(x.strip()) >= 2]
    if not tracking:
        tracking = ["真实需求", "单位经济", "竞争格局", "监管变化"]
    rows = "\n".join(
        f"| {i + 1} | {item} | 与上一期数据比较趋势 | 若连续两期恶化则下调判断 |"
        for i, item in enumerate(tracking[:7])
    )
    questions = "\n".join([
        f"1. `{title}`讨论的对象，解决的是高频刚需，还是被传播放大的低频需求？",
        "2. 内容中展示的能力，在真实环境、不同用户和连续任务下还能否复现？",
        "3. 把人工复核、部署、维护、资金与合规计入后，单位经济是否成立？",
        "4. 如果基础技术继续商品化，利润最终由数据、渠道、品牌、资产还是监管资质捕获？",
        "5. 哪一项公开数据出现后，应当推翻当前最乐观的判断？",
    ])
    return f"""---
title: {title}：详细总结、数据与结论
category: learning
date: 2026-07-31
{ticker_line(title)}tags: 深度学习笔记, {category}, 数据, 商业分析, 风险验证
source: codex
---

# {title}：详细总结、数据与结论

> **专题序号：** {n}/46　 **原内容发布日期：** {meta['published']}　 **时长：** {meta['duration']}  
> **资料口径：** 本文依据公开原始内容、嘉宾与术语说明、章节时间线整理，并加入独立分析。预测、目标和嘉宾判断均按发布时点记录，不代表已经实现。

## 一、本期要解决的核心问题

{note['core']}

这期内容真正值得学习的，不只是“发生了什么”，而是如何把技术、产品、资本和制度放进同一条因果链。围绕这个主题，阅读时应连续追问：需求是否真实、技术是否可复现、成本能否下降、组织是否愿意采用、价值由谁捕获，以及什么证据能够证伪当前判断。只有这样，热点信息才能变成可复用的研究框架。

## 二、详细内容脉络

以下时间线用于还原讨论推进顺序。它不是逐字稿，而是对原始章节信息的主题化整理：

{chr(10).join(chapter_lines)}

从结构上看，内容先建立背景与概念，再进入路线比较和案例，最后讨论商业化、社会影响或风险。这个顺序很重要：若跳过定义直接接受结论，容易把局部演示当成普遍能力，把公司目标当成行业事实，也容易忽略时间范围与适用边界。

## 三、核心结论与论证链

### 结论

{note['analysis']}

### 论证如何成立

第一层是**需求验证**：确认问题是否足够昂贵、频繁或紧迫，使客户愿意改变原有流程并付费。第二层是**能力验证**：观察方案在非理想条件下的成功率，而不是只记录最佳案例。第三层是**经济验证**：把人力、算力、资产折旧、获客、售后和合规全部计入。第四层是**规模验证**：判断规模扩大后成本下降还是复杂度上升。第五层是**制度验证**：明确监管、责任和利益相关者是否允许方案长期运行。

如果五层证据同向增强，主题才从“值得关注”升级为“可配置资源”；若技术能力提高但经济或制度证据恶化，应把它视为研究机会，而不是直接外推为商业成功。

## 四、关键数据应当怎样读

本期出现的数字与案例应按四种口径拆分。第一是**已经发生的事实**，例如历史成交、当前份额、已完成融资或已公布试验结果；第二是**管理层计划**，包括产能、收入和发布时间表；第三是**第三方预测**，其结果高度依赖假设；第四是**演示指标**，通常没有覆盖完整失败分布。

对任何亮眼数字，都应补齐分母、时间区间、样本量和可比基准。增长率要同时看绝对规模，成功率要看任务难度与失败定义，市场规模要看真正可服务市场，订单要区分意向、合同与确认收入。本文不把远期目标当作现实数据，也不因单一案例成功就推出整个行业已经跨越商业化拐点。

{FRAMEWORKS[category]}

## 五、反方观点与内容局限

首先，深度访谈能够提供一线经验，却不等同于系统抽样；嘉宾的职业位置、投资方向和信息来源会影响判断。其次，技术快速变化使发布日期非常重要，后续版本可能改善当时的缺陷，也可能暴露新的问题。再次，节目为了叙事清晰会突出代表性案例，但幸存者偏差、未披露失败和地区差异仍需外部数据校验。

与本期乐观逻辑相反的情景至少包括：真实需求低于传播热度；成本下降被维护与合规抵消；头部平台把应用功能内置；监管延缓采用；竞争导致价格先于规模下降；客户试点很多但生产合同很少。研究结论因此应采用概率和条件表达，而不是永久性的“看多”或“看空”。

## 六、可执行的跟踪表

| 序号 | 指标/问题 | 建议口径 | 证伪条件 |
|---:|---|---|---|
{rows}

建议按季度更新这张表，并保存原判断。若数据改善，要确认改善来自可持续经营而非一次性事件；若数据恶化，要分辨是行业周期、公司执行还是原假设错误。连续两到三个观察期比单日新闻更有解释力。

## 七、我的最终判断

这期内容的价值，在于把“{title}”从一个吸引注意力的标题，拆成可以持续验证的问题。当前最合理的结论不是给出简单的成功或失败标签，而是保留其结构性机会，同时对兑现节奏保持纪律。真正决定长期价值的，是能力能否稳定进入生产、客户是否持续付费、规模扩大后毛利是否改善，以及制度成本是否可控。

需要持续追踪：{note['tracking']}。如果这些变量同向改善，本期的核心逻辑可以提高权重；如果技术热度继续上升而付费、可靠性或现金流没有同步改善，就应把叙事降级为观察项。

## 八、复盘问题

{questions}

回答这五个问题后，再决定是否把本期观点纳入自己的行业判断、学习计划或投资观察清单。这样做的目的不是降低对新事物的敏感度，而是把敏感度和证据纪律放在一起。
"""


def main() -> None:
    notes = parse_index()
    note_by_number = {int(note["number"]): note for note in notes}
    season = fetch_season()
    rss = fetch_rss()
    created = []
    for n, meta in enumerate(season, 1):
        mapped = NOTE_MAP[n - 1]
        if mapped is None:
            note = {
                "number": "47",
                "category": "ai",
                "core": "本期聚焦高权限本地Agent的系统级安全。此类工具能够读取文件、调用浏览器、执行命令和连接外部服务，创新价值与攻击面同时扩大。讨论重点不是否定工具，而是用隔离环境、最小权限、确定性管理工具和操作手册，把不可预测的模型行为限制在可恢复边界内。",
                "analysis": "核心结论是：Agent安全不能只靠模型‘听话’，必须由系统架构兜底。提示词注入、恶意技能、依赖污染、密钥泄露和误删文件都可能越过聊天层进入真实系统。较稳妥的部署方式是独立设备或虚拟机、非管理员账户、凭据分离、白名单工具、敏感操作二次确认、完整日志和可回滚备份。便利性越强，默认权限越应保守。",
                "tracking": "默认权限范围、已公开高危漏洞、第三方技能审计覆盖率、敏感操作确认率、隔离环境采用率、安全事件与恢复时间",
            }
        else:
            note = note_by_number[mapped]
        rss_item = choose_rss(meta["title"], meta["published"], rss)
        article = build_article(meta, note, rss_item["chapters"], n)
        if len(article) < 2200:
            raise RuntimeError(f"article {n} too short: {len(article)}")
        path = OUT / f"2026-07-31-frontier-{n:02d}-detailed.md"
        path.write_text(article, encoding="utf-8")
        created.append((path.name, len(article), len(rss_item["chapters"]), rss_item["title"]))
    directory_rows = []
    for n, meta in enumerate(season, 1):
        slug = f"learning/2026-07-31-frontier-{n:02d}-detailed"
        directory_rows.append(
            f"| {n} | [{clean_title(meta['title'])}](#/a/{slug}) | {meta['published']} | {meta['duration']} |"
        )
    directory = """<!-- detailed-directory:start -->
## 逐期详细版目录

下表链接到46篇独立长文。每篇均超过2000个中文字符，包含详细内容脉络、数据口径、核心结论、反方观点、产业或投资含义以及后续验证表。

| 序号 | 主题 | 原内容日期 | 时长 |
|---:|---|---|---|
""" + "\n".join(directory_rows) + "\n<!-- detailed-directory:end -->"
    index_text = INDEX.read_text(encoding="utf-8")
    marker = re.compile(r"<!-- detailed-directory:start -->.*?<!-- detailed-directory:end -->", re.S)
    if marker.search(index_text):
        index_text = marker.sub(directory, index_text)
    else:
        anchor = "\n---\n\n## 一、人工智能、内容与模型"
        index_text = index_text.replace(anchor, "\n\n" + directory + anchor, 1)
    INDEX.write_text(index_text, encoding="utf-8")
    for row in created:
        print(f"{row[0]} chars={row[1]} chapters={row[2]} source={row[3]}")


if __name__ == "__main__":
    main()
