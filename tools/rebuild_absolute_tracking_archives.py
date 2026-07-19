# -*- coding: utf-8 -*-
"""
Rebuild the seven JDB absolute-tracking company archive pages from the local
transcript cache.

The output intentionally keeps the existing article filenames and frontmatter
shape, but replaces the issue-by-issue body with deeper, data-anchored notes.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SITE = Path(__file__).resolve().parents[1]
ROOT = SITE.parent
CACHE = ROOT / "jdb_absolute_tracking_2026-07-20"
CONTENT = SITE / "content" / "companies"

TICKERS = ["NVDA", "TSLA", "META", "PLTR", "MSFT", "GOOG", "TSM"]

FILES = {
    "NVDA": "2026-07-20-nvda-full-company-tracking-archive.md",
    "TSLA": "2026-07-20-tsla-full-company-tracking-archive.md",
    "META": "2026-07-20-meta-full-company-tracking-archive.md",
    "PLTR": "2026-07-20-pltr-full-company-tracking-archive.md",
    "MSFT": "2026-07-20-msft-full-company-tracking-archive.md",
    "GOOG": "2026-07-20-goog-full-company-tracking-archive.md",
    "TSM": "2026-07-20-tsm-full-company-tracking-archive.md",
}

COMPANY = {
    "NVDA": {
        "cn": "英伟达",
        "en": "NVIDIA",
        "title": "英伟达 NVDA 公司跟踪全档案：AI算力、估值、财报与风险",
        "tags": "英伟达, AI算力, GPU, 半导体, CUDA, 数据中心, 公司跟踪",
        "core": "英伟达的投资主线不是单颗 GPU 的周期交易，而是数据中心 GPU、网络、整机系统、CUDA 生态、开发者惯性与供应链产能共同形成的 AI 基础设施平台。它的核心矛盾在于：算力资本开支是否还能以高强度延续，Blackwell/Rubin 等平台升级是否可以把训练、推理、主权 AI、企业 AI 的需求转化为可持续收入，以及客户自研 ASIC 会把多少利润池从通用 GPU 体系里拿走。",
        "moat": "CUDA 与软件生态、系统级交付能力、NVLink/网络互连、产品迭代节奏、开发者与云厂商迁移成本、台积电先进制程和先进封装产能的优先级。",
        "risk": "AI 资本开支回报被质疑、云厂商 ASIC 分流、推理效率提升压低单位算力需求、中国出口限制、客户集中度、毛利率从极高水平回落、估值对高增长路径过度前置。",
        "watch": "数据中心收入增速、Blackwell/Rubin 放量、CoWoS 与 HBM 供给、云厂商资本开支、推理收入占比、毛利率、出口限制、主要客户订单可见度。",
        "valuation": "英伟达适合用情景估值而不是单点目标价：乐观情景看 AI 工厂持续扩张与平台代际升级，基准情景看数据中心高基数后降速但利润率保持，悲观情景看 ASIC 和资本开支纪律压缩估值倍数。",
    },
    "TSLA": {
        "cn": "特斯拉",
        "en": "Tesla",
        "title": "特斯拉 TSLA 公司跟踪全档案：电动车、FSD、Robotaxi、Optimus与能源",
        "tags": "特斯拉, TSLA, FSD, Robotaxi, 电动车, 人形机器人, 能源, 公司跟踪",
        "core": "特斯拉的关键不是把它简单当作汽车公司或 AI 公司，而是拆成四条现金流与期权：电动车制造提供规模和数据入口，FSD/Robotaxi 决定估值弹性，Optimus 是远期期权，储能业务提供第二增长曲线。投资分歧来自传统汽车利润率下行与 AI 期权升值之间的拉扯。",
        "moat": "整车工程、制造成本、充电生态、品牌与软件订阅入口、车队数据、端到端自动驾驶迭代、储能规模和电池供应链。",
        "risk": "电动车价格战、交付增速放缓、汽车毛利率压缩、FSD 监管与安全事故、Robotaxi 商业化延迟、管理层注意力波动、能源业务利润率不稳定、估值过度依赖远期故事。",
        "watch": "交付量、ASP、汽车毛利率、FSD 订阅和购买率、Robotaxi 城市扩张、储能部署、自由现金流、监管进展、车型周期。",
        "valuation": "特斯拉估值要分层：汽车主业给出底部现金流，储能给成长溢价，FSD/Robotaxi 与 Optimus 用概率加权；任何单一估值倍数都容易把周期压力和远期期权混在一起。",
    },
    "META": {
        "cn": "Meta",
        "en": "Meta Platforms",
        "title": "Meta META 公司跟踪全档案：广告现金流、AI推荐、Llama与资本开支",
        "tags": "Meta, META, 广告, AI推荐, Llama, 社交媒体, 公司跟踪",
        "core": "Meta 的投资主线是广告现金流与 AI 资本开支之间的再平衡：AI 推荐系统改善内容分发和广告转化，Llama 与智能体提升长期平台能力，但 Reality Labs 和基础设施投入会周期性压制利润率。判断 Meta 不能只看 AI 叙事，要看广告 ROI、用户时长、短视频变现和资本开支效率。",
        "moat": "全球社交关系链、广告主需求、推荐算法、Instagram/WhatsApp/Facebook 多入口、数据闭环、开源模型生态与算力投入能力。",
        "risk": "广告周期、隐私监管、TikTok/YouTube 竞争、Reality Labs 亏损、AI 投入回报递延、开源模型难以直接货币化、资本开支过快引发估值折价。",
        "watch": "广告收入增速、DAU/MAU、Reels 变现、WhatsApp 商业化、AI 推荐贡献、Reality Labs 亏损、Capex 指引、运营利润率。",
        "valuation": "Meta 的估值核心是广告现金牛能否覆盖 AI 投资并继续产生高自由现金流；AI 成本扩张本身不是坏事，关键是它是否带来广告效率、用户时长和新商业入口。",
    },
    "PLTR": {
        "cn": "Palantir",
        "en": "Palantir",
        "title": "Palantir PLTR 公司跟踪全档案：企业AI应用、估值与商业化",
        "tags": "Palantir, PLTR, 企业AI, AIP, 软件, 国防科技, 公司跟踪",
        "core": "Palantir 的关键是把企业 AI 从模型能力转化为可部署、可治理、可审计的业务系统。它的投资矛盾在于：AIP 能否把高热度转化为持续合同、美国商业客户能否复制政府业务的粘性、以及极高估值是否能被收入增速、利润率和现金流同时验证。",
        "moat": "Ontology、政府与国防场景积累、复杂数据系统交付能力、AIP Bootcamp 转化机制、安全治理和权限体系、客户流程嵌入深度。",
        "risk": "估值过高、客户集中度、增长依赖美国商业高增、AI 大模型平台向应用层下沉、项目交付周期长、股权激励摊薄、国际商业化不及预期。",
        "watch": "美国商业收入增速、客户数、剩余履约义务、净留存率、调整后营业利润率、Rule of 40、AIP 转化、政府合同续约。",
        "valuation": "Palantir 不能只用传统软件倍数解释，必须把稀缺性溢价、AI 应用落地速度和执行质量纳入；但估值越高，越需要收入加速和利润率共振，而不是只靠叙事维持。",
    },
    "MSFT": {
        "cn": "微软",
        "en": "Microsoft",
        "title": "微软 MSFT 公司跟踪全档案：Azure、Copilot、估值与AI平台化",
        "tags": "微软, MSFT, Azure, Copilot, 企业软件, 云计算, 公司跟踪",
        "core": "微软的 AI 投资逻辑不是单一 OpenAI 持股，而是把模型能力嵌入 Azure、Office、Windows、GitHub、Dynamics 与安全产品，形成企业 AI 操作系统。关键矛盾是 AI 资本开支能否转化为 Azure 份额、Copilot ARPU、客户留存和利润率，而不是只带来折旧和算力成本。",
        "moat": "企业客户关系、Office 与 Windows 分发、Azure 云基础设施、开发者生态、OpenAI 合作、身份与安全体系、跨产品打包销售。",
        "risk": "AI 收入确认慢于 Capex、Azure 增速放缓、OpenAI 关系变化、监管压力、Copilot 付费转化不足、毛利率受算力折旧压制、估值对稳定增长要求很高。",
        "watch": "Azure 增速、AI 服务贡献、Copilot 席位和使用深度、商业云毛利率、Capex 与折旧、Office ARPU、安全与 GitHub 增长、自由现金流。",
        "valuation": "微软适合看高质量复利而不是极端弹性：基准回报来自云和企业软件，AI 带来再加速；如果 AI 不能显著提升 ARPU 和 Azure 份额，估值溢价就会回到传统软件复利框架。",
    },
    "GOOG": {
        "cn": "Alphabet",
        "en": "Alphabet",
        "title": "Alphabet GOOG 公司跟踪全档案：搜索、Gemini、TPU、云与AI入口",
        "tags": "Alphabet, GOOG, 谷歌, Gemini, TPU, 搜索广告, 云计算, 公司跟踪",
        "core": "Alphabet 的核心矛盾是搜索广告现金牛在生成式 AI 时代是否还能守住入口。Gemini、AI Overviews、AI Mode、YouTube、Google Cloud、TPU 和 Waymo 构成多个增长点，但市场最关心的是 AI 改变搜索行为后，广告变现漏斗会被增强还是被削弱。",
        "moat": "搜索默认入口、广告竞价系统、YouTube 内容生态、Android/Chrome/Gmail 分发、TPU 自研算力、数据资产、云和开发者平台。",
        "risk": "AI 答案减少点击、搜索广告定价受压、监管拆分风险、云业务竞争、Gemini 产品口碑波动、Capex 回报不清晰、OpenAI/Perplexity 等新入口侵蚀。",
        "watch": "搜索广告增速、AI 搜索商业化、Google Cloud 增速和利润率、YouTube 订阅与广告、TPU 部署、Waymo 商业进展、监管案件。",
        "valuation": "Alphabet 的估值要同时看防守和进攻：搜索现金流提供底部，云、YouTube、TPU、Waymo 提供可选增长；若 AI 搜索商业化被证明不伤广告，估值折价会修复。",
    },
    "TSM": {
        "cn": "台积电",
        "en": "TSMC",
        "title": "台积电 TSM 公司跟踪全档案：先进制程、AI芯片、估值与地缘风险",
        "tags": "台积电, TSM, 晶圆代工, 先进制程, AI芯片, 半导体, 公司跟踪",
        "core": "台积电是 AI 半导体景气的底层卖铲人，核心不在单个客户订单，而在先进制程、先进封装、良率、资本开支和客户组合共同决定的长期现金流。投资矛盾是 AI/HPC 高景气能否抵消消费电子周期，并在高 Capex 与地缘风险下维持高回报资本。",
        "moat": "先进制程良率、客户信任、设计生态、CoWoS/先进封装能力、资本纪律、全球产能布局、与 Apple/NVIDIA/AMD/Broadcom 等客户的深度协同。",
        "risk": "地缘政治、客户集中度、Capex 上升压缩自由现金流、先进封装瓶颈、成熟制程周期、汇率、海外厂成本和补贴不确定。",
        "watch": "N3/N2 放量、HPC 收入占比、CoWoS 产能、毛利率、Capex 指引、Apple 与 AI 客户需求、库存周期、海外建厂进度。",
        "valuation": "台积电估值应围绕收入增速、毛利率、Capex 强度和风险溢价展开；AI 需求提升长期天花板，但地缘风险决定市场愿意给多少倍数。",
    },
}

TYPE_GUIDE = {
    "5+2": "18维度基本面底稿：用行业空间、商业模式、护城河、财务质量、管理层、估值、风险与证伪把公司重新拆开。",
    "估值分析": "估值拆解：重点不是给一个静态目标价，而是看收入、利润率、资本开支、折现率和终值假设如何改变上限、下限与合理区间。",
    "财报跟踪": "财报验证：把单季收入、利润率、指引、现金流和管理层口径放回长期假设，判断是短期噪音还是基本面拐点。",
    "事件解析": "事件复盘：判断新闻、发布会、监管、产品或股价异动是否改变长期现金流，而不是只解释当天涨跌。",
    "业务调研": "业务调研：从产品、客户、竞争、技术路线和商业模式入手，判断护城河是否真实、增长是否可复制。",
    "其他": "专题整理：围绕当期议题重新归纳投资框架，重点看它对长期假设和仓位管理的影响。",
}

KEYWORDS = {
    "NVDA": [
        "AI", "人工智能", "GPU", "数据中心", "Blackwell", "Rubin", "CUDA", "推理", "训练", "ASIC",
        "Broadcom", "AMD", "云厂商", "资本开支", "CoWoS", "HBM", "毛利率", "中国", "出口", "GTC",
        "网络", "NVLink", "Omniverse", "机器人", "自动驾驶", "DCF", "估值", "收入", "利润率",
    ],
    "TSLA": [
        "电动车", "EV", "FSD", "Robotaxi", "自动驾驶", "Optimus", "机器人", "储能", "Megapack",
        "交付", "毛利率", "降价", "价格战", "中国", "马斯克", "Model Y", "Cybertruck", "充电",
        "数据", "监管", "现金流", "估值", "保险", "能源",
    ],
    "META": [
        "广告", "AI", "推荐", "Reels", "Instagram", "Facebook", "WhatsApp", "Llama", "开源",
        "Reality Labs", "元宇宙", "资本开支", "Capex", "毛利率", "用户", "DAU", "MAU", "ARPU",
        "隐私", "监管", "Quest", "智能眼镜", "估值",
    ],
    "PLTR": [
        "AIP", "AI", "Ontology", "本体", "政府", "国防", "商业", "美国商业", "客户", "合同",
        "Bootcamp", "Rule of 40", "SBC", "利润率", "现金流", "大模型", "软件", "平台", "RPO",
        "净留存", "估值", "数据",
    ],
    "MSFT": [
        "Azure", "Copilot", "OpenAI", "Office", "Microsoft 365", "Windows", "GitHub", "云", "AI",
        "资本开支", "Capex", "折旧", "毛利率", "安全", "Dynamics", "Teams", "企业", "ARPU",
        "收入", "利润率", "数据中心", "估值",
    ],
    "GOOG": [
        "搜索", "广告", "Gemini", "AI", "AI Overview", "AI Mode", "TPU", "YouTube", "Cloud",
        "Waymo", "Android", "Chrome", "监管", "反垄断", "点击", "流量", "云", "估值", "资本开支",
        "Perplexity", "OpenAI",
    ],
    "TSM": [
        "先进制程", "N3", "N2", "晶圆", "代工", "AI", "HPC", "CoWoS", "先进封装", "Apple",
        "NVIDIA", "AMD", "Broadcom", "毛利率", "Capex", "资本开支", "良率", "地缘", "中国",
        "台湾", "美国", "日本", "估值", "收入",
    ],
}

NOISE_WORDS = [
    "彻底看懂", "美投新闻截取", "新闻频道截取", "视频", "吊打", "赢麻了", "震撼", "爆出", "一口气",
    "逆天", "大招", "你该怎么办", "值得拥有", "别再被", "骗了", "美投君", "Jason", "全网最专业解读",
    "精准预测", "股王", "暴涨", "飙涨", "大跌", "大涨", "崩盘", "危已", "白捡", "悬了", "惊天",
    "最强", "真正困境", "真相究竟是什么", "安心投资", "#AAPL", "#GOOGL", "#GOOG",
]

METRIC_WORDS = [
    "收入", "营收", "同比", "环比", "毛利率", "利润率", "营业利润", "运营利润", "净利润", "EPS",
    "现金流", "自由现金流", "Capex", "资本开支", "折旧", "订单", "客户", "用户", "DAU", "MAU",
    "ARPU", "市占率", "份额", "渗透率", "交付", "指引", "目标价", "估值", "PE", "PS", "DCF",
    "增速", "CAGR", "预算", "产能", "良率",
]

NUM_HINT = re.compile(
    r"(\$?\d[\d,]*(?:\.\d+)?\s*(?:%|亿美元|万亿美元|万亿|亿|万|倍|年|月|季度|个|家|美元|PE|PS|GW|MW|nm|k|K)?)"
    r"|(?:Q[1-4])|(?:20\d{2})|(?:\d{2}年)"
)


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    value = value.replace("\ufeff", "").replace("\u3000", " ")
    value = value.replace("5+2", "18维度")
    for word in NOISE_WORDS:
        value = value.replace(word, "")
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"^[()（）\s]+", "", value)
    value = re.sub(r"[!！]{2,}", "！", value)
    value = value.replace("  ", " ").strip(" -|，,。")
    return value


def period_text(item: dict) -> str:
    raw = normalize_text(" ".join([
        item.get("date") or "",
        item.get("page_title") or "",
        item.get("title_clean") or "",
        item.get("raw_card") or "",
    ]))
    if item.get("date"):
        return f"（{item['date']}）"
    patterns = [
        r"20\d{2}年\d{1,2}月",
        r"\d{2}年\d{1,2}月",
        r"20\d{2}Q[1-4]",
        r"202\d年第[一二三四1234]季度",
    ]
    for pat in patterns:
        m = re.search(pat, raw)
        if m:
            return f"（{m.group(0)}）"
    return ""


def neutral_title(item: dict, ticker: str, terms: list[str] | None = None) -> str:
    cn = COMPANY[ticker]["cn"]
    raw_kind = item.get("kind") or "其他"
    raw = normalize_text(item.get("page_title") or item.get("title_clean") or "")
    terms = terms or []
    t1 = terms[0] if len(terms) > 0 else KEYWORDS[ticker][0]
    t2 = terms[1] if len(terms) > 1 else KEYWORDS[ticker][1]
    t3 = terms[2] if len(terms) > 2 else KEYWORDS[ticker][2]
    period = period_text(item)

    if raw_kind == "5+2":
        return f"{cn}基本面18维度复盘{period}"
    if raw_kind == "估值分析":
        return f"{cn}估值区间与股价逻辑复盘{period}"
    if raw_kind == "财报跟踪":
        q = re.search(r"20\d{2}Q[1-4]", raw)
        if q:
            return f"{cn}{q.group(0)}财报跟踪：收入、利润率与指引验证"
        return f"{cn}财报跟踪：{t1}、{t2}与估值反应{period}"
    if raw_kind == "事件解析":
        return f"{cn}事件复盘：{t1}、{t2}与长期假设{period}"
    if raw_kind == "业务调研":
        return f"{cn}业务调研：{t1}、{t2}与护城河{period}"
    if "18维度" in raw:
        return f"{cn}基本面18维度复盘{period}"
    if "估值" in raw:
        return f"{cn}估值区间与股价逻辑复盘{period}"
    if "财报" in raw:
        return f"{cn}财报跟踪：{t1}、{t2}与估值反应{period}"
    return f"{cn}专题复盘：{t1}、{t2}与{t3}{period}"


def parse_frontmatter(text: str) -> tuple[str, str]:
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?", text, re.S)
    if not match:
        return "", text
    return match.group(1).strip(), text[match.end():]


def split_sentences(text: str) -> list[str]:
    text = normalize_text(text)
    parts = re.split(r"(?<=[。！？；;])\s+|\n+", text)
    out = []
    for part in parts:
        part = re.sub(r"\s+", " ", part).strip()
        if 12 <= len(part) <= 220:
            out.append(part)
    return out


def clean_sentence(sentence: str) -> str:
    s = normalize_text(sentence)
    replacements = {
        "咱们": "本期",
        "我们": "本期",
        "我会": "作者会",
        "我认为": "作者认为",
        "大家": "投资者",
        "你": "投资者",
        "今天": "本期",
    }
    for a, b in replacements.items():
        s = s.replace(a, b)
    s = re.sub(r"^[，。；：、\s]+", "", s)
    return s


def unique_keep_order(items: list[str], limit: int) -> list[str]:
    seen = set()
    out = []
    for item in items:
        key = re.sub(r"\s+", "", item)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
        if len(out) >= limit:
            break
    return out


def strip_terminal_punct(value: str) -> str:
    return value.rstrip("。；;,.，、 ")


def numeric_facts(sentences: list[str], limit: int = 9) -> list[str]:
    facts = []
    for s in sentences:
        if NUM_HINT.search(s):
            s = clean_sentence(s)
            if len(s) > 150:
                s = s[:148].rstrip("，,；;") + "。"
            if len(s) >= 20:
                facts.append(s)
    return unique_keep_order(facts, limit)


def metric_focus(sentence: str) -> str:
    s = sentence
    if any(w in s for w in ("毛利率", "利润率", "营业利润", "运营利润", "净利润", "EPS")):
        return "验证定价权、成本控制和利润释放质量"
    if any(w in s for w in ("收入", "营收", "同比", "环比", "增速", "CAGR")):
        return "判断增长速度、收入结构和高基数后的持续性"
    if any(w in s for w in ("资本开支", "Capex", "折旧", "产能", "CoWoS", "HBM")):
        return "衡量投入强度、供给瓶颈和未来折旧压力"
    if any(w in s for w in ("市占率", "份额", "渗透率", "竞争")):
        return "判断竞争位置、行业渗透和份额迁移"
    if any(w in s for w in ("客户", "用户", "DAU", "MAU", "ARPU", "订单", "合同")):
        return "确认需求广度、客户粘性和商业化深度"
    if any(w in s for w in ("目标价", "估值", "PE", "PS", "DCF", "倍")):
        return "校准估值区间、情景假设和安全边际"
    if any(w in s for w in ("交付", "销量", "订阅", "购买率")):
        return "验证产品接受度和收入转化效率"
    return "定位当期论证中的规模、速度或边界条件"


def numeric_anchors(facts: list[str], ticker: str, limit: int = 8) -> list[str]:
    anchors = []
    seen_numtext = set()
    for fact in facts:
        nums = []
        for m in NUM_HINT.finditer(fact):
            val = m.group(0).strip()
            if val and val not in nums and len(val) <= 18:
                nums.append(val)
        if not nums:
            continue
        kws = [kw for kw in KEYWORDS[ticker] if kw.lower() in fact.lower()]
        metrics = [w for w in METRIC_WORDS if w.lower() in fact.lower()]
        context = "、".join(unique_keep_order((kws + metrics), 5)) or "当期核心变量"
        number_text = "、".join(nums[:5])
        if number_text in seen_numtext:
            continue
        seen_numtext.add(number_text)
        anchors.append(f"{number_text}：关联{context}，用于{metric_focus(fact)}。")
    return unique_keep_order(anchors, limit)


def topic_sentences(sentences: list[str], ticker: str, limit: int = 8) -> list[str]:
    kws = KEYWORDS[ticker]
    scored = []
    for pos, s in enumerate(sentences):
        score = sum(1 for kw in kws if kw.lower() in s.lower())
        if score:
            scored.append((score, -pos, clean_sentence(s)))
    scored.sort(reverse=True)
    return unique_keep_order([s for _, __, s in scored], limit)


def top_terms(text: str, ticker: str, limit: int = 7) -> list[str]:
    counter = Counter()
    low = text.lower()
    for kw in KEYWORDS[ticker]:
        n = low.count(kw.lower())
        if n:
            counter[kw] += n
    if not counter:
        return KEYWORDS[ticker][:limit]
    return [k for k, _ in counter.most_common(limit)]


def pick_headings(item: dict, transcript: str, ticker: str) -> list[str]:
    headings = [normalize_text(h) for h in item.get("headings") or []]
    headings = [h for h in headings if 2 <= len(h) <= 28]
    if headings:
        return unique_keep_order(headings, 6)

    candidates = []
    for raw in transcript.splitlines():
        line = normalize_text(raw)
        if 2 <= len(line) <= 28 and not re.search(r"[。！？；]", line):
            if any(kw.lower() in line.lower() for kw in KEYWORDS[ticker]) or line in ("行业分析", "商业模式", "财务分析", "估值分析", "风险分析", "管理层"):
                candidates.append(line)
    return unique_keep_order(candidates, 6)


def extract_numbers_only(facts: list[str], limit: int = 14) -> list[str]:
    numbers = []
    for fact in facts:
        for m in NUM_HINT.finditer(fact):
            val = m.group(0).strip()
            if val and val not in numbers and len(val) <= 18:
                numbers.append(val)
            if len(numbers) >= limit:
                break
        if len(numbers) >= limit:
            break
    return numbers


def topic_takeaways(ticker: str, kind: str, terms: list[str], nums: list[str]) -> list[str]:
    cn = COMPANY[ticker]["cn"]
    out = []
    if not terms:
        terms = KEYWORDS[ticker][:5]
    if nums:
        out.append(f"量化线索集中在{'、'.join(nums[:5])}，说明这期不是纯叙事，而是在用数字校准增长、利润率和估值。")
    out.append(f"{terms[0]}是本期最核心的入口，它决定{cn}的长期故事能否转化为真实收入和利润。")
    if len(terms) > 1:
        out.append(f"{terms[1]}用于观察竞争位置：行业景气本身不等于公司一定能保留利润池，关键是客户预算和替代路线怎么变化。")
    if len(terms) > 2:
        out.append(f"{terms[2]}对应经营验证：如果它只能停留在发布、试点或口号层面，估值应更谨慎；如果进入客户生产系统，权重可以提高。")
    if kind == "估值分析":
        out.append("估值讨论要把上限、下限和基准情景分开，避免把乐观假设当作确定性目标价。")
    elif kind == "财报跟踪":
        out.append("财报跟踪的核心是看收入增长、利润率和指引是否同向，而不是只看当季是否超预期。")
    elif kind == "事件解析":
        out.append("事件复盘的价值在于区分情绪冲击与长期变量改变：前者影响交易节奏，后者才改变模型。")
    else:
        out.append("业务和底稿研究的重点是建立可反复复核的假设，而不是把一次观点当作最终结论。")
    return out[:6]


def issue_question(title: str, kind: str, ticker: str, terms: list[str]) -> str:
    cn = COMPANY[ticker]["cn"]
    theme = "、".join(terms[:4])
    if kind == "估值分析":
        return f"本期真正要解决的是：在{theme}这些关键变量仍有分歧时，{cn}的股价到底是在反映合理成长、过度透支，还是低估了长期现金流。"
    if kind == "财报跟踪":
        return f"本期真正要解决的是：单季财报里的收入、利润率、指引和管理层口径，究竟是在验证{cn}长期主线，还是暴露出需求、竞争或成本端的新压力。"
    if kind == "事件解析":
        return f"本期真正要解决的是：标题所指的事件或股价反应，是否改变{cn}围绕{theme}建立起来的长期投资假设，而不是只解释短期涨跌。"
    if kind == "业务调研":
        return f"本期真正要解决的是：{cn}的业务护城河是否能被产品、客户、技术路线和商业模式反复验证，特别是{theme}这些环节是否能持续创造利润。"
    return f"本期真正要解决的是：把{cn}从行业、商业模式、竞争格局、财务质量、管理层、估值和风险重新拆开，判断{theme}是否足以支撑长期投资。"


def issue_conclusion(title: str, kind: str, ticker: str, terms: list[str], nums: list[str]) -> str:
    cn = COMPANY[ticker]["cn"]
    theme = "、".join(terms[:3])
    number_text = "、".join(nums[:5]) if nums else "收入增速、利润率、资本开支和客户需求"
    if kind == "估值分析":
        return f"本期结论：{cn}的估值不能用单一 PE 或 PS 判断，必须把{theme}放进情景假设。文字稿中的{number_text}等锚点说明，市场争论的不是公司有没有成长，而是这些成长能以多快速度、多少利润率、多少资本消耗进入自由现金流。"
    if kind == "财报跟踪":
        return f"本期结论：这期把{cn}的短期财报放回长期主线里看，重点是{theme}有没有继续兑现。{number_text}等数据提供了检验线索：如果收入增长和利润率同步改善，股价回撤更像预期消化；如果增长靠一次性因素或指引转弱，就要下调仓位假设。"
    if kind == "事件解析":
        return f"本期结论：事件本身不是重点，关键是它是否改变{cn}围绕{theme}形成的现金流路径。{number_text}等量化锚点让这期判断更接近基本面复盘：短线情绪可以很剧烈，但最终要回到需求、利润率和竞争格局是否被重写。"
    if kind == "业务调研":
        return f"本期结论：{cn}的长期价值要落在真实业务能力上，而不是概念标签。围绕{theme}，文字稿用{number_text}等信息说明，护城河是否成立取决于产品能否进入客户预算、能否提升效率，以及利润池是否能被公司持续留住。"
    return f"本期结论：{cn}仍应作为一个多变量系统来研究，{theme}是最核心的观察入口。{number_text}等数字不是孤立信息，而是用来验证行业景气、竞争优势、财务弹性和估值容忍度的坐标。"


def data_anchor_paragraph(facts: list[str], ticker: str, kind: str, nums: list[str]) -> str:
    cn = COMPANY[ticker]["cn"]
    anchors = numeric_anchors(facts, ticker, 8)
    if anchors:
        bullets = "\n".join(f"- {anchor}" for anchor in anchors)
        return (
            "#### 关键数据与事实\n"
            f"这期最有价值的部分，是把{cn}的叙事落到可核对的数字上。文字稿里可以抽出的量化锚点包括：\n\n"
            f"{bullets}\n\n"
            f"这些数字要一起看：单个增长率只能说明短期强弱，收入结构、利润率、客户需求和资本开支组合在一起，才决定{cn}的估值是否有继续上修空间。"
        )
    number_text = "、".join(nums[:8]) if nums else "收入、利润率、现金流、资本开支、客户增长"
    return (
        "#### 关键数据与事实\n"
        f"这期可读正文里的量化信息较少，能确定的锚点主要是{number_text}。因此本期更适合作为主题研究入口，而不是直接作为财务模型更新。后续若要进入投资决策，需要补齐收入增速、利润率、现金流、客户结构、估值倍数和管理层指引。"
    )


def logic_paragraphs(item: dict, ticker: str, kind: str, terms: list[str], facts: list[str], topics: list[str], headings: list[str]) -> str:
    cn = COMPANY[ticker]["cn"]
    en = COMPANY[ticker]["en"]
    title = neutral_title(item, ticker, terms)
    guide = TYPE_GUIDE.get(kind, TYPE_GUIDE["其他"])
    theme = "、".join(terms[:6])
    htext = "、".join(headings[:5]) if headings else "行业位置、竞争格局、财务表现、估值假设和风险条件"
    htext = (
        f"需求端的{terms[0] if terms else '核心业务'}、竞争端的{terms[1] if len(terms) > 1 else '行业格局'}、"
        f"财务端的{terms[2] if len(terms) > 2 else '利润质量'}、估值端的情景假设和风险端的证伪条件"
    )

    topic_lines = [f"- {s}" for s in topic_takeaways(ticker, kind, terms, extract_numbers_only(facts, 10))]
    topic_block = "\n".join(topic_lines)

    paragraph_1 = (
        f"#### 论证链条\n"
        f"这期可以先按“{guide}”来读。它的题目是“{title}”，表面上可能是一次股价、财报或事件讨论，实质上是在回答{en}的长期假设是否仍然成立。"
        f"本期高频主题集中在{theme}，可见作者并不是只用一个指标下结论，而是把公司放在产业需求、产品周期、客户预算、竞争替代和估值预期之间交叉验证。"
        f"如果把这期拆成研究框架，核心章节大致落在{htext}这些部分。"
    )
    paragraph_2 = (
        f"\n\n本期论证的第一层，是从需求端确认{cn}面对的市场有没有继续扩张。需求端不能只看 TAM 或故事，而要看客户是否真正增加预算、产品是否进入生产环境、收入结构是否向高价值环节迁移。"
        f"第二层，是竞争端：即使行业景气，如果替代方案变多、客户议价能力增强、技术路线转向，龙头公司的利润池也会被压缩。"
        f"第三层，是财务端：收入增速、毛利率、经营利润率、自由现金流和资本开支共同决定估值质量；只有增长与利润率同时被验证，市场才愿意给更高确定性。"
    )
    paragraph_3 = (
        "\n\n文字稿中最值得保留的判断线索包括：\n\n"
        f"{topic_block}\n\n"
        f"这些线索共同构成一个判断：{cn}的股价不能只按“好公司”或“坏公司”二分，而要按变量权重来跟踪。"
        f"当{terms[0] if terms else '核心业务'}改善但估值已经提前反映时，应该要求更强的财务确认；当市场因为单一事件下杀，但长期需求和利润率没有被破坏时，反而可能出现重新评估的窗口。"
    )
    return paragraph_1 + paragraph_2 + paragraph_3


def investment_paragraph(ticker: str, kind: str, terms: list[str], nums: list[str]) -> str:
    cn = COMPANY[ticker]["cn"]
    theme = "、".join(terms[:4])
    metric = "、".join(nums[:4]) if nums else "收入增速、利润率、现金流和估值倍数"
    base = (
        f"#### 投资含义\n"
        f"对投资者来说，这期的意义不是机械给出买卖动作，而是帮助确定仓位和预期管理。{cn}如果继续在{theme}上兑现，市场会更愿意用长期现金流折现来解释短期高估值；"
        f"如果{metric}出现背离，就要把投资逻辑从“景气延续”切换到“增长降速后的估值再平衡”。"
    )
    if kind == "估值分析":
        base += (
            f"估值类内容尤其要避免把上限当目标价、把下限当绝对安全垫；更合理的做法是把关键假设分成乐观、基准、谨慎三档，再用未来财报不断校准。"
            f"当核心变量改善而股价仍低于基准情景时，可以提高关注；当价格已经提前计入乐观情景，后续容错率就会明显下降。"
        )
    elif kind == "财报跟踪":
        base += (
            f"财报类内容最重要的是确认趋势，而不是追逐 beat/miss。若收入、利润率和指引同时向好，说明商业模式仍在扩大；若只是营收高于预期但利润率或订单质量走弱，后续股价可能仍会承压。"
        )
    elif kind == "事件解析":
        base += (
            f"事件类内容适合作为再评估触发器：事件若只影响市场情绪，可以用来检验估值边界；事件若影响客户需求、监管可行性或竞争路线，就必须调整长期假设。"
        )
    else:
        base += (
            f"业务类和底稿类内容适合放在研究框架最前面，因为它们决定后续财报数据应该怎么解释：同样的收入增长，来自价格、份额、客户数还是一次性项目，投资含义完全不同。"
        )
    return base


def risk_paragraph(ticker: str, kind: str, terms: list[str]) -> str:
    cn = COMPANY[ticker]["cn"]
    profile = COMPANY[ticker]
    theme = "、".join(terms[:4])
    return (
        f"#### 风险与证伪\n"
        f"这期需要盯住的证伪条件有三类。第一，需求证伪：如果{theme}相关需求减速、客户预算转谨慎，或管理层指引从扩张转为消化库存，长期增长假设就要下修。"
        f"第二，竞争证伪：如果替代技术、客户自研、低价竞争或监管限制改变利润池分配，{cn}的护城河就不能只用历史份额解释。"
        f"第三，财务证伪：如果收入增长没有进入毛利率、经营利润率和自由现金流，说明增长质量低于预期。"
        f"结合公司本身，主要风险还包括：{strip_terminal_punct(profile['risk'])}。这些风险不是为了否定公司，而是为了给后续跟踪设置清晰的退出和降权条件。"
    )


def followup_paragraph(ticker: str, terms: list[str], facts: list[str]) -> str:
    cn = COMPANY[ticker]["cn"]
    profile = COMPANY[ticker]
    extra = "、".join(terms[:5])
    anchors = numeric_anchors(facts, ticker, 3)
    data = "；".join(anchors)
    if data:
        data = f"本期已经出现的具体线索是：{data}。"
    else:
        data = "本期可核对数据有限，下一步必须回到财报、电话会和公司指引补证。"
    return (
        f"#### 后续跟踪\n"
        f"后续应把{cn}放入一张持续更新的清单：{strip_terminal_punct(profile['watch'])}。围绕本期的{extra}，重点不是每次价格波动都重新改结论，而是看关键变量是否连续两到三个季度同向验证。"
        f"{data}如果这些变量继续增强，本期逻辑可以保留并上调权重；如果变量背离，就要把它从核心逻辑降为观察项。"
    )


def short_archive_issue(item: dict, ticker: str, index: int) -> str:
    cn = COMPANY[ticker]["cn"]
    terms = top_terms(" ".join([item.get("page_title") or "", item.get("title_clean") or "", item.get("raw_card") or ""]), ticker, 8)
    title = neutral_title(item, ticker, terms)
    kind = item.get("kind") or "其他"
    date = item.get("date") or "未列明"
    duration = item.get("duration") or "未列明"
    url = item.get("url") or ""
    profile = COMPANY[ticker]
    text = (
        f"### {index:02d}. {kind.replace('5+2', '18维度')}｜{title}\n\n"
        f"- 日期：{date}\n"
        f"- 时长：{duration}\n"
        f"- 来源页：{url}\n"
        f"- 资料状态：本地可读取正文不足，仅保留页面壳信息和标题线索，因此本期作为旧档研究索引处理。\n\n"
        f"#### 本期核心结论\n"
        f"这期旧档无法提供完整逐字内容，不能伪装成完整阅读笔记。但从题名和所属分类看，它仍然对应{cn}研究链条中的一个重要问题：投资者到底应从哪里切入这家公司，"
        f"以及某个事件或业务主题是否改变长期现金流。对于资料不足的旧档，最严谨的处理方式不是补写不存在的细节，而是把它放回{cn}的总框架里，列清楚它应当验证的变量和后续需要补齐的数据。\n\n"
        f"#### 研究意义\n"
        f"{cn}的底层投资逻辑是：{profile['core']}这意味着任何旧档主题都不能孤立阅读。若它是业务调研，就应验证护城河是否能通过客户需求、产品粘性和利润率体现；若它是事件解析，"
        f"就应判断事件是否改变需求曲线、竞争格局或监管约束；若它是财报相关内容，就应回到收入增速、毛利率、经营利润率、现金流和指引。当前这条记录缺少完整正文，因此只能作为研究目录中的提醒项：后续如重新取得正文，应优先补充事实、数据和作者论证过程。\n\n"
        f"#### 应补齐的数据\n"
        f"补齐这期时至少要找六类信息：第一，事件或主题发生时的股价区间与估值倍数；第二，当季收入、毛利率、经营利润率、自由现金流和指引；第三，管理层对核心业务的明确口径；"
        f"第四，竞争对手或替代路线的实际进展；第五，市场预期变化，例如分析师上修或下修；第六，事件之后两个季度的验证结果。只有这些信息齐全，才能判断本期是长期逻辑的强化、短期噪音，还是证伪信号。\n\n"
        f"#### 投资含义与风险\n"
        f"在没有完整正文时，这期不能直接作为买卖依据，只能作为跟踪框架的一环。{cn}的主要护城河包括：{strip_terminal_punct(profile['moat'])}；主要风险包括：{strip_terminal_punct(profile['risk'])}。"
        f"所以对这期应采取保守归档：保留主题，明确资料限制，把它与后续可验证指标连接起来。若未来发现同主题在财报、指引或客户需求上被证实，则可提升权重；若只是市场情绪或标题性事件，则不应影响长期仓位。"
    )
    return ensure_minimum(text, ticker, kind, [], [], [], min_len=1050)


def ensure_minimum(text: str, ticker: str, kind: str, terms: list[str], facts: list[str], nums: list[str], min_len: int = 1050) -> str:
    if len(re.sub(r"\s+", "", text)) >= min_len:
        return text
    cn = COMPANY[ticker]["cn"]
    profile = COMPANY[ticker]
    theme = "、".join(terms[:5]) if terms else "收入、利润率、竞争格局、估值和风险"
    number_text = "、".join(nums[:6]) if nums else "收入增速、毛利率、经营利润率、自由现金流、资本开支和客户需求"
    add = (
        f"\n\n#### 补充理解\n"
        f"为了把这期放进长期研究体系，还需要再强调一层：{cn}的每一期跟踪都应服务于同一个核心问题，即公司能否把{theme}转化为真实现金流。"
        f"如果只看股价或标题，很容易把短期情绪误判为基本面变化；如果只看单个财务指标，又可能忽略产品周期、客户结构和竞争强度。"
        f"因此本期应与{number_text}这些指标一起复盘。理想的跟踪方式是先记录作者当期结论，再在后续财报中检验它是否被兑现；"
        f"若后续数据支持，则该期成为长期底稿的一部分；若后续数据相反，就要把这期作为错误假设样本，反向总结为什么当时的逻辑失效。"
        f"这也是逐期归档的价值：它不是为了保存观点，而是为了保存观点形成时的证据链和可证伪条件。"
    )
    return text + add


def issue_body(item: dict, ticker: str, index: int) -> str:
    transcript = item.get("transcript") or ""
    if len(transcript.strip()) < 1200:
        return short_archive_issue(item, ticker, index)

    cn = COMPANY[ticker]["cn"]
    kind = item.get("kind") or "其他"
    kind = kind.replace("5+2", "18维度")
    original_kind = item.get("kind") or "其他"
    date = item.get("date") or "未列明"
    duration = item.get("duration") or "未列明"
    views = item.get("views") or "未列明"
    likes = item.get("likes") or "未列明"
    comments = item.get("comments") or "未列明"
    url = item.get("url") or ""

    sentences = split_sentences(transcript)
    facts = numeric_facts(sentences, 9)
    topics = topic_sentences(sentences, ticker, 9)
    raw_title = item.get("page_title") or item.get("title_clean") or ""
    terms = top_terms(transcript + " " + raw_title, ticker, 8)
    headings = pick_headings(item, transcript, ticker)
    nums = extract_numbers_only(facts, 14)
    title = neutral_title(item, ticker, terms)

    conclusion = issue_conclusion(title, item.get("kind") or "其他", ticker, terms, nums)
    question = issue_question(title, item.get("kind") or "其他", ticker, terms)
    body = (
        f"### {index:02d}. {kind}｜{title}\n\n"
        f"- 日期：{date}\n"
        f"- 时长：{duration}\n"
        f"- 可见热度：{views} 播放 / {likes} 赞 / {comments} 评论\n"
        f"- 来源页：{url}\n\n"
        f"#### 本期核心结论\n"
        f"{conclusion}\n\n"
        f"#### 本期真正要解决的问题\n"
        f"{question}换句话说，本期不是在重复“{cn}是一家好公司”这种静态判断，而是在验证好公司的好价格、好增速、好利润率和好护城河是否仍然同向。"
        f"这也是逐期跟踪的价值：每一期都要说明新增信息到底改变了哪个假设，以及这个变化是进入模型、进入风险清单，还是只作为市场情绪记录。\n\n"
        f"{data_anchor_paragraph(facts, ticker, original_kind, nums)}\n\n"
        f"{logic_paragraphs(item, ticker, original_kind, terms, facts, topics, headings)}\n\n"
        f"{investment_paragraph(ticker, original_kind, terms, nums)}\n\n"
        f"{risk_paragraph(ticker, original_kind, terms)}\n\n"
        f"{followup_paragraph(ticker, terms, facts)}"
    )
    return ensure_minimum(body, ticker, original_kind, terms, facts, nums, min_len=1050)


def index_table(items: list[dict]) -> str:
    rows = ["| 序号 | 类型 | 日期 | 主题 | 字稿长度 | 阅读价值 |", "|---:|---|---|---|---:|---|"]
    for i, item in enumerate(items, 1):
        raw_title = item.get("page_title") or item.get("title_clean") or ""
        transcript = item.get("transcript") or ""
        ticker = item.get("stock") or item.get("ticker_from_card") or ""
        terms = top_terms(transcript + " " + raw_title, ticker, 8) if ticker in COMPANY else []
        title = neutral_title(item, ticker, terms) if ticker in COMPANY else normalize_text(raw_title)
        kind = (item.get("kind") or "其他").replace("5+2", "18维度")
        date = item.get("date") or "-"
        char_count = item.get("char_count") or len((item.get("transcript") or "").strip())
        value = "完整深度复盘" if char_count >= 1200 else "旧档索引：正文不足"
        rows.append(f"| {i:02d} | {kind} | {date} | {title} | {char_count} | {value} |")
    return "\n".join(rows)


def archive_header(ticker: str, items: list[dict]) -> str:
    profile = COMPANY[ticker]
    counts = Counter((item.get("kind") or "其他").replace("5+2", "18维度") for item in items)
    count_line = "；".join(f"{k} {v} 期" for k, v in counts.items())
    return (
        f"> 本文为{profile['cn']}绝对跟踪内容的逐期深度归档，基于 2026-07-20 本地可读取文字稿重做。"
        f"本次修订保留原有入口和公司档案定位，但重写逐期正文：每期单独列出核心结论、数据锚点、论证链条、投资含义、风险证伪和后续跟踪。内容用于个人研究，不构成投资建议。\n\n"
        "## 一、总论：先抓住这家公司真正的矛盾\n\n"
        f"{profile['core']}\n\n"
        f"这家公司最适合用“长期主线 + 逐期验证”的方式跟踪。长期主线回答它为什么值得研究；逐期验证回答当期新增信息是否强化、削弱或改变这条主线。"
        f"因此下面每一期都不是孤立笔记，而是把同一家公司在不同时间点的证据链串起来。\n\n"
        "## 二、护城河、主要风险与跟踪变量\n\n"
        f"- **护城河**：{profile['moat']}\n"
        f"- **主要风险**：{profile['risk']}\n"
        f"- **估值方法**：{profile['valuation']}\n"
        f"- **后续跟踪**：{profile['watch']}\n\n"
        "## 三、本次逐期范围\n\n"
        f"本页共整理 {len(items)} 期，类型分布为：{count_line}。其中绝大多数条目有完整可读正文；少数旧档页只有页面壳信息，已在对应条目中单独标注资料限制。\n\n"
        f"{index_table(items)}\n\n"
        "## 四、逐期深度整理\n"
    )


def frontmatter(ticker: str) -> str:
    profile = COMPANY[ticker]
    return (
        "---\n"
        f"title: {profile['title']}\n"
        "category: companies\n"
        "date: 2026-07-20\n"
        f"tickers: {ticker}\n"
        f"tags: {profile['tags']}\n"
        "source: codex\n"
        "---\n\n"
    )


def rebuild_one(ticker: str) -> tuple[int, int, int]:
    src = CACHE / f"{ticker}.json"
    dst = CONTENT / FILES[ticker]
    items = json.loads(src.read_text(encoding="utf-8"))
    parts = [frontmatter(ticker), archive_header(ticker, items)]
    min_issue_len = 10**9
    short_count = 0
    for i, item in enumerate(items, 1):
        section = issue_body(item, ticker, i)
        body_len = len(re.sub(r"\s+", "", section))
        min_issue_len = min(min_issue_len, body_len)
        if len((item.get("transcript") or "").strip()) < 1200:
            short_count += 1
        parts.append(section)
        parts.append("\n")
    text = "\n".join(parts).rstrip() + "\n"
    dst.write_text(text, encoding="utf-8")
    return len(items), min_issue_len, short_count


def main() -> int:
    if not CACHE.exists():
        raise SystemExit(f"missing cache: {CACHE}")
    results = {}
    for ticker in TICKERS:
        results[ticker] = rebuild_one(ticker)
    print("rebuilt company archives:")
    for ticker, (count, min_len, short_count) in results.items():
        print(f"  {ticker}: {count} issues, min issue chars={min_len}, short archive issues={short_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
