---
title: AI基础设施与软件商业化研究备忘录：三机构最新15篇
category: reports
date: 2026-07-30
tickers: AMD, NVDA, META, MSFT, PLTR, GOOGL, NOW, BTSG, AGX, MU, CRDO, LITE, SNDK, CLS
tags: 研报, 人工智能, 半导体, 数据中心, 电力, 云计算, 软件商业化, 模型实验室
source: codex
---

# PickAlphas 三机构最近 5 篇研究深度整理

整理日期：2026-07-29  
范围：SemiAnalysis 最近 5 篇、Seeking Alpha Alpha Picks 最近 5 篇、FundaAI 最近 5 篇  
说明：本文为研究摘要和投资分析，基于已登录 PickAlphas 后可读内容整理；不复刻原文，不构成个性化投资建议。

## 一、总览结论

这 15 篇文章放在一起看，核心不是单一股票推荐，而是 AI 产业链从“GPU 算力竞赛”进入“系统工程、供电约束、软件生态、商业化回款”四条主线同时定价的新阶段。

第一，GPU 竞争正在从单卡性能转向整机柜、网络、软件和 TCO。SemiAnalysis 对 AMD MI455/Helios 与 NVIDIA Vera Rubin 的拆解显示，AMD 在理论算力、HBM 带宽、价格/股权返利上有非常强的进攻性，但生产爬坡、背板可靠性、SerDes、ROCm/vLLM 自动化测试和内部开发集群不足，仍是抢份额的最大短板。NVIDIA Rubin 则展示了系统级成熟度：VR NVL72 在推理的每兆瓦性能和每美元 TCO 上显著优于 GB200，软件支持也已经向 CUDA、PyTorch、vLLM、Triton 上游推进。

第二，AI 数据中心的瓶颈已经明确转向电力。FundaAI 对 xAI/SPCX 8GW 建设的分析显示，GPU、服务器、资本、部分配电并非核心障碍，真正的不确定性在发电和许可。需求端 8GW 订单看似已经锁定，但供应端渠道只能支撑 3.5-5GW 的可信建设能力，文章给出的基准情形是 2027 年底 5GW 左右，满额 8GW 仅是低概率上行情形。

第三，软件商业化已经出现分化。Anthropic 通过 Claude Code 和 API/B2B 用例展示出极强 ARR 增长和更好毛利结构；Microsoft Copilot 席位在 2026 年二季度大幅上升，Azure GPU 定价改善；Palantir 政府业务强到接近国家级 AI 基础设施平台；ServiceNow 虽然 AI ACV 过 10 亿美元，但真实使用和独立变现仍需要 4Q 续约季验证。

第四，Alpha Picks 的策略重点是纪律，而不是盲目追涨。7 月两篇市场回顾都强调：市场从 AI/半导体拥挤交易转为风险厌恶时，高质量成长股也会先被卖出，但系统化选股在反弹阶段往往恢复更快。AGX 是典型“AI 电力基建收益股涨太多后规则锁盈”的案例，BTSG 是“高增长医疗服务+专业药房+估值仍折价”的新增买入案例。

## 二、逐篇整理：SemiAnalysis

### 1. Can AMD break the CUDA Moat? AMD Advancing AI 2026

来源：https://pickalphas.com/reports/email-c736015784d0a2c10cac  
日期：2026-07-24

核心结论：AMD 的 AI 机会真实存在，但成败不取决于发布会参数，而取决于 Helios 机柜能否顺利量产，以及 ROCm/vLLM/SGLang 软件生态能否把理论 TCO 优势变成客户可用的吞吐。文章的基调是“看多潜力、严厉指出执行风险”。

关键数据与逻辑：MI455X/Helios 是 AMD 第一代真正 rack-scale AI 系统。MI455 使用 2nm 数据中心硅，封装规模约 5.5 倍 reticle，总逻辑硅约 3,470 平方毫米；单芯片理论 FP8 约 20PF，高于 Rubin 的 17.5PF；12 组 HBM4 带来约 23.3TB/s 带宽。但系统级难点也非常重：Helios 缺少类似 Rubin Oberon 的 cableless 设计，SerDes 能力偏弱，背板大面积需要 retimer，文中提到每机柜需要超过 550 个 Broadcom 以太网 retimer，且背板可靠性正在影响爬坡。

软件层面，AMD 有进步但节奏不够。文章称 ROCm 关键团队持续修复问题，GEAK/Hyperloom 等 agentic kernel 工具能用自动化方法生成、测试、优化 Triton/HIP/FlyDSL kernel，但内部 GPU 集群和 CI 稳定性不足，使 vLLM 的 CUDA parity 进展被拖慢。MI455 的 gfx1250 ISA 与 MI355 的 gfx950 差异很大，意味着新 kernel 和测试路径不能简单继承。

投资含义：AMD 的股价弹性来自三个变量：Helios 量产、OpenAI/Meta 等大客户落地、ROCm 生态突破。若三者兑现，AMD 可能从“二供”变成真正的 AI 加速器份额竞争者；若任一环节失败，TCO 和融资返利优势会被交付风险吃掉。我的判断是：AMD 适合高风险仓位，不适合按 NVDA 级别核心仓持有；买点应等交付和软件指标被验证，不能只买“反 CUDA 叙事”。

### 2. Vera Rubin NVL72 vs GB200 NVL72? Inference TCO & Architecture Analysis

来源：https://pickalphas.com/reports/email-37444c83b4deb2494a7b  
日期：2026-07-22

核心结论：Rubin 的重点是推理经济性，而不是单纯训练算力。文章认为 VR NVL72 相比 GB200 NVL72 在 DeepSeek R1 推理上可达到约 5.4 倍每兆瓦性能、约 5 倍每美元性能；即使与后续优化后的 GB200/GB300 比，Rubin 也能提供更多高速交互模式。

关键数据与逻辑：Rubin 的 3-bit LUT Tensor Core 用查表方式压缩权重，对低比特推理更友好；Rubin 软件栈已经公开进入 CUDA 13.4，并向 PyTorch、vLLM、OpenAI Triton 上游合入。文章还估算 VR NVL72 Max-Q 配置的 server-level power 约 185kW，不含网络，GPU TDP 约 1,800W。文中强调 CoreWeave 的早期 Rubin 测试需要谨慎看待，因为对比基线可能是 2025 早期 GB200，但 SemiAnalysis 用自身 InferenceX 数据重新归一化后，仍认为 Rubin 推理 TCO 优势明显。

投资含义：这篇对 NVDA 是强支撑。NVIDIA 的护城河正在从 CUDA 扩展为“芯片架构、NVLink/NVL 机柜、软件上游、TCO 数据、客户迁移成本”的组合。风险在于 Rubin 到 Feynman 会是更复杂的 kernel 迁移，未来软件磨合仍有风险；但就可投资性而言，NVDA 仍是 AI 硬件链最核心资产，只是市值已经很大，回报更多取决于盈利兑现和估值消化。

### 3. Meta’s Infrastructure Team Needs A Culture Reset

来源：https://pickalphas.com/reports/email-df66f7a539a61cca9cb7  
日期：2026-07-21

核心结论：Meta 的 AI 资源不是不够，而是基础设施组织可能把局部优化凌驾于公司整体目标之上。文章指出 Rivos 收购、Grand Teton、Ariel、DSF 网络、定制 AMD MI450/MI455 方案中，都存在“为了某个指标好看而牺牲整体 TCO 和模型团队效率”的问题。

关键数据与逻辑：Rivos 收购金额超过 25 亿美元，但 Meta 原本主要想要其 GPU/加速器团队和 IP，最终却接收了整家公司，整合效果不佳，部分 Rivos 人员离开或被裁。Grand Teton 为增加 SSD 和非 NVIDIA 依赖引入额外 Broadcom PCIe switch，但最终既没有真正摆脱 NVIDIA 网络依赖，还提高了成本和复杂度。Ariel 是 Meta 定制 GB200 Catalina rack，每块板去掉一个 B200 GPU，造成 LLM 团队拿到的系统反而弱于其他 hyperscaler 买到的标准 SKU。

投资含义：Meta 是 AI 应用和广告现金流的优质资产，但投资者要区分“Zuckerberg 强烈投入 AI”与“基础设施组织能否高效执行”。这篇并非否定 META，而是提醒：Meta 的资本开支效率、定制硬件选择、网络架构和组织治理，会直接影响未来 FCF 和 AI 领先性。我的判断是 META 仍适合核心持有，但跟踪重点要放在 capex ROI、Reels/AI 广告现金流、MSL 模型进展和基础设施纠偏。

### 4. The Future of Meta Superintelligence: A 1 Year Progress Update

来源：https://pickalphas.com/reports/email-0de2136e3590f8ec1136  
日期：2026-07-09

核心结论：Meta Superintelligence Labs 虽然还没证明模型能力，但 Meta 可能是少数同时具备数据、人才、算力三要素的 hyperscaler。文章认为 Meta 有机会追赶 OpenAI/Anthropic，甚至比 Google 更有可能重回 frontier。

关键数据与逻辑：文章把 RL 环境/任务视为新的稀缺数据。Meta 的优势在于内部拥有广告、销售、工程、运营等大量真实白领工作流，可以用屏幕记录和内部专家构造更真实的 RL 任务、工具环境和验证器。文章还提到 Meta 约 3000 名工程师转向 RL task/environment 相关工作。算力方面，Meta 同时推进 5 个 1GW+ “titan” 集群，包括 Prometheus、Hyperion 和其他未命名园区；SemiAnalysis 的 Tokenomics 模型认为 Meta 到 2026 年底可能拥有超过 OpenAI 和 Anthropic 的 AI compute。

投资含义：META 的 AI 赔率很特殊：下行有广告业务和社交网络现金流，上行有超级智能团队、数据和算力。如果 MSL 追上第一梯队，市场可能重估 Meta 从广告公司到 AI 平台公司的可能性。但成功远未确定，大公司文化、基础设施执行和人才整合仍是主要风险。

### 5. Anthropic 3Q26 Profit Over $1B: The Anthropic IPO Financials Sneak Peak

来源：https://pickalphas.com/reports/email-d18212742e341b53724e  
日期：2026-07-08

核心结论：Anthropic 可能是当前 AI Lab 里财务质量最强的商业化样本。文章认为 Claude Code 推动 Anthropic ARR 在 2026 年一季度从 90 亿美元跃升至 300 亿美元，OpenAI 与 Anthropic 合计 ARR 接近 1000 亿美元量级；Anthropic 的优势在 B2B/API/编码用例，毛利结构比偏消费者订阅的模式更好。

关键数据与逻辑：文章估计 Claude Code 是 Anthropic 2026 年商业化拐点，1 月新增 ARR 约 30 亿美元、2 月约 70 亿美元、3 月约 110 亿美元。编码用例占 Lab ARR 超过 65%，Cursor、Cognition、Lovable、Replit 等生态公司合计也形成数十亿美元 ARR。文章认为长期稳态 30-40% EBIT/FCF margin 有可能，毛利率可走向 75% 中段；若 2027 年月新增 ARR 可达 150 亿美元，年末 ARR 可能达到 3000 亿美元，并以 20 倍 2027 年末 ARR 作为基础估值框架。

投资含义：这对未来 Anthropic IPO 是强看多，但需要价格纪律。对二级市场间接影响是：AI 模型商业化若真实成立，将继续支撑 NVDA、云厂商、内存、网络、电力、数据中心资本开支；但也会加剧 hyperscaler FCF 下行，因为最强云公司都需要发行权益/融资来支持 2027 以后资本开支。

## 三、逐篇整理：Seeking Alpha Alpha Picks

### 6. Alpha Picks Market Recap & Portfolio Review

来源：https://pickalphas.com/reports/sa-6320390  
日期：2026-07-24

核心结论：市场从 mega-cap tech 集中上涨转向更分散的风格切换。能源、公用事业和部分高质量成长股跑赢，Magnificent Seven 出现一年多最差 5 日表现之一。Alpha Picks 强调，不要把短期回撤误判为基本面恶化。

关键数据与逻辑：10 年期美债收益率升至约 4.71%，Brent 一度突破 100 美元/桶，资金流向能源、公用事业和现金流稳定板块。Alpha Picks 中 MU、CRDO、MXL、LITE、SNDK 等 AI 基础设施相关标的短期表现强，说明 AI 交易并非只有七巨头，市场正在奖励内存、光通信、连接、数据中心硬件供应链。

投资含义：更合理的 AI 持仓不应只押 NVDA/MSFT/META，也应包含“卖铲子但市值更小”的上游零部件和数据中心供应链；同时需要用分批买入和再平衡控制波动。

### 7. The Dip Is Here. Are You Ready?

来源：https://pickalphas.com/reports/sa-6317752  
日期：2026-07-17

核心结论：回调已经从板块轮动变成风险厌恶。地缘、油价、芯片和 AI 拥挤交易同时施压，Alpha Picks 组合也被拖累，但其建议是保持纪律、准备买入高质量回撤。

关键数据与逻辑：文章回顾 2025 年类似阶段，组合 trailing 3-month return 曾从 -17% 在两个月内修复到 +18%，用来说明高质量成长股在恐慌中先跌，但在情绪稳定后也可能先修复。策略上不主张一次性抄底，而是等待压力释放、分批买入基本面仍强的公司。

投资含义：这对当前仓位管理很重要。AI 链条高景气并不等于股价不会深回调；在高估值阶段，买点纪律比方向判断更重要。

### 8. AGX: Locking In Additional Gains

来源：https://pickalphas.com/reports/sa-6317664  
日期：2026-07-17

核心结论：Argan 是电力基建超级景气的赢家，但 Alpha Picks 按规则继续锁定部分收益。AGX 自 2024-10-15 加入组合后上涨约 331.24%；此前 2026-01-20 已卖出初始本金，这次因 Hold 评级维持 180 天，再卖出一笔等同初始投资的仓位。

关键数据与逻辑：AGX 服务电力行业，覆盖工程、建设、项目开发、运营管理和咨询，受益于 AI 数据中心、电动车充电、制造业回流、可再生能源和电网现代化。Q1 FY27 收入增长约 50%，Power segment 执行强，授权 2 亿美元回购至 2030 年。估值已高，约 45 倍 forward P/E，对比行业约 21 倍；但 forward EPS growth 约 34%，ROE 接近 40%，每股现金约 25.38 美元。

投资含义：AGX 是 AI 电力链的高 beta 代表，但涨幅过大后应该“让利润奔跑，同时拿回本金”。新资金不宜追高，适合等待订单延续但估值回撤的窗口。

### 9. Stock Buy: Top Health Care Services Stock Delivers Double-Digit Growth

来源：https://pickalphas.com/reports/sa-6316639  
日期：2026-07-15

核心结论：Alpha Picks 新买入 BrightSpring Health Services（BTSG）。逻辑不是 AI，而是高增长、复杂医疗服务、专业药房、家庭/社区护理的垂直整合平台，兼具增长和估值折价。

关键数据与逻辑：BTSG Q1 2026 收入约 36 亿美元，同比增长 25.6%；调整后 EBITDA 约 1.9 亿美元，同比增长约 45%；全年收入指引增长 14-18%，调整后 EBITDA 增长 29-34%。Pharmacy Solutions 中 specialty/infusion 收入增长约 35%，处方量增长约 30%，每张处方毛利增长接近 50%；Provider Services 收入增长近 28%，home health 增长近 49%。杠杆从 2024 年的 4.6 倍降至约 2.3 倍。估值方面，forward PEG 约低于行业中位数 49%，PS 指标约低于行业 73%。

投资含义：BTSG 适合被归入“非 AI、但基本面改善和估值折价”的组合平衡资产。风险在 Medicare/Medicaid 报销、监管、整合 Amedisys/LHC、债务和劳动力成本。若想降低 AI 组合波动，BTSG 比追高型 AI 小票更适合作为分散。

### 10. Alpha Picks Market Recap & Portfolio Review

来源：https://pickalphas.com/reports/sa-6315356  
日期：2026-07-10

核心结论：7 月上旬市场在中东、能源和通胀担忧下仍保持韧性，AI 基建和能源是主要支撑。Alpha Picks 自 2022 年 7 月以来累计回报约 386.71%，对比 S&P 500 约 98.86%。

关键数据与逻辑：油价上涨约 4%，10 年期美债收益率回到 4.5% 以上，FedWatch 当时显示年底前至少加息一次的概率超过 80%。组合强势股包括 PARR、CRDO、LITE、SNDK、CLS，分别受益于能源价格、AI 光通信、内存/存储、AI 服务器制造。弱势股包括 CDE、SSRM、SYF、EZPW、W，反映贵金属、消费信贷和利率敏感消费承压。

投资含义：AI 基建仍强，但宏观利率和能源通胀会影响估值倍数。组合层面应同时拥有 AI 基建、能源/现金流、防御型或低相关资产，而不是单一押注长久期成长。

## 四、逐篇整理：FundaAI

### 11. Deep|SPCX: xAI 8GW Buildout Mapping

来源：https://pickalphas.com/reports/email-760937369a1ade3b0ac7  
日期：2026-07-29

核心结论：xAI 的 8GW 不是空想，需求端订单基本锁定，但能否通电才是核心。FundaAI 将问题拆成芯片、发电、许可、输配电、资本五道门，认为芯片和资本不是瓶颈，发电和环保许可才是决定 2027 年底真实容量的关键。

关键数据与逻辑：需求侧由现有约 1.5GW、2026 年 13k GB300 racks 约 2.5GW、2027 年 15k Rubin racks 超过 4GW 组成，合计接近 8GW。现有 Colossus 2 约 946MW，被定位为全球最大单体 AI 数据中心之一。但六个供应链渠道对可交付能力的交叉验证集中在 3.5-5GW。文章给出 2027 年底 nameplate 场景：Bear 4GW 概率约 25%，Base 5GW 概率约 50%，Bull 8GW installed 仅约 15-20%，且 8GW installed 对应可用容量约 5.5-6GW。

关键跟踪信号：Solaris/ProEnergy 类发电资产收购、第二个 GW 级 Jereh 订单、PSD 许可批准或监管和解。Jereh x FTAI JV 已有 14.65 亿美元、超过 1GW 的涡轮订单，交付到 2027 年 11 月。最大尾部风险是 Memphis/Colossus 相关燃气轮机许可和 Clean Air Act 诉讼，若监管要求停机，不只是 8GW 上行受阻，既有涡轮支撑容量也会受损。

投资含义：直接押 SPCX/xAI 不一定可行，但这篇对电力设备、燃气轮机、变压器、数据中心 EPC、电网服务、备用电源是强景气验证。对 NVDA/服务器链的含义是：需求不是最大问题，电力交付才是订单转收入的节奏瓶颈。

### 12. Preview|PLTR: 2Q26 Growth Momentum Remains Strong

来源：https://pickalphas.com/reports/email-17aff21115473fc4a66d  
日期：2026-07-28

核心结论：Palantir 2Q26 增长动能很强，政府业务可能继续加速，商业端暂无明显减速。公司正在从项目制软件供应商变成国家级 AI 基础设施平台。

关键数据与逻辑：FundaAI 用政府合同义务推演收入，历史上 T 季度政府 obligations 约 23% 会转化为 T+1 增量收入。1Q26 obligations 约 6.3 亿美元，推导 2Q26 美国政府增量收入约 1.48 亿美元，美国政府收入约 8.35 亿美元；国际政府收入回归估计约 1.95 亿美元；合计政府收入约 10.30 亿美元，同比增长约 86%，较 1Q 的约 76% 继续加速。商业端，美国 Commercial 增长假设维持约 133%，国际 Commercial 仍偏弱。总 2Q 收入估算约 19 亿美元，可能明显高于指引上限。

护城河和风险：PLTR 的 Ontology、AIP、FDE、AI FDE、Mindkit、垂直操作系统（如 Warp Speed）使其不是单纯模型层公司，而是把数据、工作流和执行闭环嵌进客户系统。风险在欧洲和民权/隐私争议、NHS 退出条款、国际商业转化弱、估值过高、零售持股情绪波动。

投资含义：PLTR 业务质量非常高，但估值也极端高。更适合“核心观察+回撤买入”，不适合在情绪最热时重仓追涨。

### 13. Preview|MSFT 2Q26

来源：https://pickalphas.com/reports/email-93a9bf883fd80f96dab8  
日期：2026-07-28

核心结论：Microsoft Copilot 销售可能明显超预期，Azure GPU 租赁价格改善，传统云保持稳定，AI 产品体验改善但竞争仍强。

关键数据与逻辑：Copilot 席位模型显示，2024 年底约 630 万席，2025 年底约 1810 万席，2026 年 3 月约 2200 万席，到 2026 年 6 月跃升至约 3700 万席，其中企业席位约 3400 万。增量主要来自大客户从部门级试点扩展到全公司部署，约 300 万增量来自免费用户转付费。E7 仍早期，估计约 150 万用户，下一季度可能增加 100-150 万，到 9 月底约 300 万；FY27 目标可能是转换约 10% E3/E5 客户，约 2000 万席。

Azure 方面，FundaAI 估计 GPU pricing 本季度上调 7-15%，主要通过降低续约折扣、缩短合同期、调整企业协议实现，而不是直接提 list price。CPU 价格也通过折扣收窄和新实例迁移实现高个位数提升。Azure Foundry 的多模型采用提高了企业对 OpenAI、Claude 等模型的统一采购便利性，但 OpenAI 模型分发到 AWS 等平台后，也削弱 Azure 独家流量。

投资含义：MSFT 是 AI 软件商业化和云基础设施最均衡的核心仓。风险是 Copilot FY27 销售计划激进、客户重新评估 Claude/OpenAI/其他 AI 工具、E7 迁移有合同摩擦。我的判断：MSFT 适合核心持有，回调时加仓优先级高于许多高估值软件股。

### 14. Weekly|Kimi K3 / NOW / GOOG / IFX / AI Labs ARR Tracker

来源：https://pickalphas.com/reports/email-fe6df6d2060a22b02487  
日期：2026-07-27

核心结论：市场把 Kimi K3 的 KV cache 变小解读为内存利空，FundaAI 认为方向反了：更高效的 KV cache 让 NAND offload 大规模可行，而模型本身更大、专家更多、并行更复杂，反而需要更多 HBM、GPU、scale-up networking、DRAM/NAND。

关键数据与逻辑：Kimi K3 是 2.8T 参数 MoE，激活 16/896 experts，建议至少 64 加速器高带宽 supernode。其 KV compression 约 75%，低于 DeepSeek V4 的约 90%，但已足以让 NAND offload 更经济。周报还强调 GOOG 是重要增量：GCP 2Q26 增长约 82%，剔除 Wiz 约 79%，说明 AI capex 正开始转化为收入，而非单纯沉淀为折旧。IFX 方面，市场担心高压直流机柜导致份额流失，但 FundaAI 认为 SiC/GaN 内容提升可抵消担忧。周内 30 个专家电话还显示：ServiceNow 需求稳但 AI 变现早期；Google Cloud AI 基建需求改变 GPU 定价和承诺模式；企业存储采购偏紧，DRAM/NAND 价格强势从 spot 扩散到 LTA。

投资含义：这篇对 MU/存储、GOOGL、数据中心电力半导体、光通信和网络是正面；对“AI 越高效越不需要硬件”的简单熊市叙事构成反驳。

### 15. Review|NOW 2Q26: Pull-Forward Expected, Restrained Full-Year Guide

来源：https://pickalphas.com/reports/email-f0fcc0ad52feb0735ba1  
日期：2026-07-23

核心结论：ServiceNow 2Q26 全面 beat，但全年上调克制，说明部分增长来自价格切换前的提前续约和 on-prem 收入提前确认，而非完全可持续的需求加速。AI 叙事改善，但真实使用还需验证。

关键数据与逻辑：2Q26 cRPO 同比 constant currency 增长 21.5%，高于指引约 200bps；subscription revenue 约 38.48 亿美元，同比增长 23.0% cc；OPM 29.5%，高于指引 300bps；总 RPO 约 290 亿美元，同比增长 22%；超过 100 万美元 net new ACV 的交易数 123 个，同比增长 40%；续约率 98%。但全年 subscription revenue 中点仅上调 1500 万美元，低于 2Q beat 的 3100 万美元，且 3Q subscription revenue 指引 39.75-39.80 亿美元，低于一致预期约 40.05 亿美元。

AI 层面，AI ACV 过 10 亿美元，管理层维持年末 15 亿美元目标，AI net new ACV 环比增长超过 40%；AI Control Tower 六个月内超过 500 客户；但渠道反馈显示真实 Now Assist 使用、AI consumption 和独立变现仍早期，AI 扩张更多来自 SKU 重构和 bundling。4Q 约 40% 客户续约，其中 10-15% 若升级 Prime，才会证明 AI 变现拐点。

投资含义：NOW 是优质软件公司，但当前更像“持有/等待确认”，不是强追。若 4Q Prime 升级和 token consumption 兑现，估值可以继续撑住；若 AI 仍停留在打包销售，市场可能压低倍数。

## 五、投资优先级与组合建议

### 第一梯队：核心长期资产

MSFT：Copilot 席位跃升、E7/Agent 365/AI Credits 提供新打包方式，Azure GPU 定价改善。适合作为 AI 软件商业化核心仓。主要风险是 Copilot 使用深度不及席位增长、FY27 销售目标过高。

GOOGL：GCP 82% 增长是资本开支 ROI 的硬证据，估值相对便宜，且 TPU/Gemini/Vertex/广告 AI 均有支撑。主要风险是搜索被 AI 改写、capex 过快、监管。

META：广告现金流强，AI 数据和内部 RL 环境优势独特，估值相对不贵。主要风险是基础设施组织效率、capex 失控、MSL 追赶不及预期。

NVDA：Rubin/NVL72/TCO/软件栈仍是最强系统级护城河。主要风险是市值巨大、供应链/客户集中、未来 Rubin 到 Feynman 软件迁移成本。

### 第二梯队：高弹性但需择时

AMD：若 Helios 量产和 ROCm 生态兑现，弹性巨大；但当前风险也最大，尤其是生产爬坡、背板可靠性、内部开发集群和软件 parity。适合事件驱动和回撤分批，不宜满仓追。

PLTR：基本面极强，政府业务加速、商业端无明显减速，平台嵌入深。问题是估值太贵，适合等财报后波动或市场回调。

MU/CRDO/LITE/SNDK/CLS：AI 基建二线弹性方向，受益于内存、光模块、连接、存储和服务器制造。适合篮子持有，单票波动会很大。

### 第三梯队：非 AI 或 AI 电力链分散

AGX：AI 电力基建受益明显，但涨幅过大、估值高。策略是持有利润、分批兑现，不宜追高。

BTSG：医疗服务高增长、估值相对折价，适合作为组合里低相关成长股。风险是政府报销、监管和整合。

NOW：业务质量好，但 2Q beat 的可持续性要打折，4Q 续约季是验证点。当前更适合观察或已有仓持有。

### 当前行情参考

截至 2026-07-29 15:53 UTC 附近，实时行情显示：AMD 约 428.81 美元、PE 约 140.6；NVDA 约 192.05 美元、PE 约 29.2；META 约 588.18 美元、PE 约 21.4；MSFT 约 395.20 美元、PE 约 23.5；PLTR 约 124.88 美元、PE 约 140.3；GOOGL 约 333.53 美元、PE 约 16.8；NOW 约 115.54 美元、PE 约 71.3；BTSG 约 71.13 美元、PE 约 50.8；AGX 约 495.45 美元、PE 约 43.5。

## 六、我的组合动作建议

如果是 3-5 年 AI 主线组合，我会把核心仓放在 MSFT、GOOGL、META、NVDA，原因是它们分别代表企业 AI 商业化、云/TPU/搜索广告再加速、社交数据和广告现金流、GPU 系统级垄断。AMD 和 PLTR 是高弹性观察仓，必须用价格和事件验证约束仓位。AI 基建二线用篮子比单押更好，尤其是内存、光模块、数据中心网络、电力 EPC 和电力设备。

短期策略上，不建议在 AI 情绪最热、个股连续上行时一次性重仓。更好的做法是：核心仓已有则持有；新资金分 3-5 次买入；把 AMD、PLTR、NOW、AGX 这类估值/执行敏感股设为“财报后验证再加仓”；把 BTSG 这类低相关增长股作为组合平衡。

最重要的跟踪指标：Rubin 量产和 InferenceX 公开数据、AMD Helios 交付和 vLLM/SGLang parity、Meta capex ROI 和 MSL 模型进展、Anthropic/OpenAI ARR 和 IPO 定价、xAI/SPCX 电力许可与 Jereh/ProEnergy/Solaris 订单、MSFT Copilot 真实使用和 E7 转化、PLTR 政府 obligations 和国际商业转化、NOW 4Q Prime 升级率与 AI consumption。
