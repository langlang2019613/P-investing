---
title: 研报终端本期4篇深度解读 — AI基础设施瓶颈转移：光互连/高压供电/NAND/代工
category: reports
date: 2026-06-14
tags: CPO, 光模块, Marvell, Kioxia, Intel, 研报解读
source: gmail
---

> 核心主线：AI 基础设施的瓶颈正从"算力"转向"互连(光学)+供电(高压)+存储(NAND)+产能(代工)"。并提示短期杠杆过重、有回调风险（锚定 Anthropic ARR）。

## 第1篇 · CPO/800V HVDC 延期讨论点评（6月10日）

**A. CPO——担忧过度，NPO 加速是亮点**
- 黄仁勋 Computex 明确 CPO 按计划放量；NCP客户（CoreWeave、Lambda）、Oracle、一家主要CSP均按计划推进。焦点是产能/良率/认证，非取消。
- 光学逻辑不只靠CPO：scale-up带宽翻倍是强力顺风。
- Lumentum(LITE) 核心论点：行业进入 **InP 和激光器产能受限阶段**——最稀缺=InP外延片/InP芯片/激光器产能/良率，供应商定价权极强。LITE 的问题是产能不足而非需求不足。
- LITE与Coherent(COHR)还受益于OCS、光模块、ITLA、泵浦激光器、Coherent Lite。

**B. 800V——影响被过度解读**
- Rubin Ultra 大概率续用 Oberon 架构（单柜功耗降到500kW以下）是"延期"论主因；但单柜>300kW后PSU/CBU必须外置，电源柜采用只会加速。
- ±400V HVDC sidecar 将用于 Google 和 Meta 的 VR200 机柜。
- 投资指向：DC/DC 价值向**板级降压器件和半导体**转移。

## 第2篇 · Marvell (MRVL) FY1Q27 财报点评

- F1Q27营收$24.18亿符合预期；F2Q27指引$27.0亿超街道4%。管理层上调：FY27 ~$115亿、FY28 ~$165亿；数据中心FY27 +50%、互连+70%、定制FY28"翻倍以上"。
- 分析更乐观（高于管理层）：FY27数据中心~60%、互连~90%。依据：1.6T DSP放量、TIA/驱动器年化$10亿+、DCI FY28 $10亿目标、Coherent lite 200G/lane、scale-up光学FY28 >$3亿。
- **Agentic AI 驱动 Google XPU-attach（DPU+CXL）：FY27 0 → FY28 ~$18亿 → FY29 ~$51亿**。
- EPS预测：2027/2028上调至$7.80/$13.17；营收2024 $55亿→2028E $331亿。
- 万亿市值路径：更多Google生意（TPU角色），正为Google设计网络芯片（Intel 18A制造、2027底量产）。

## 第3篇 · 周报（6月6日）— 6篇子报告要点

- 宏观：Computex期间AI半导体暴涨后暴跌；Marvell因"下一个万亿公司"评价3天涨~45%后SOXX单日-10%。杠杆ETF AUM>$3000亿，1%波动→$120-180亿日内再平衡。关键锚=Anthropic ARR（Claude Code拉动）。SpaceX IPO流动性担忧。
- Coherent Lite：真正放量驱动是与OCS配对（让OCS-based TPU集群进入2.4T/3.2T时代）。
- NVL576 Scale-up：NPO把每GPU光引擎含量从~2.25提到~4.0（+78%），Rubin Ultra光引擎需求~1200万套。**CPO利好先进封装，NPO利好光模块厂商**。
- Kioxia：NAND超级周期，供给紧到2027下半年；ASP 2026下半年环比+40%。
- PANW：平台化稳固；PL(Planet Labs)：估值已price in。

## 第4篇 · "Intel 应该融资"（6月11日，SemiAnalysis）

- 观点：Intel最糟已过、巨额capex在前，应趁股价高增发约$400亿（而非回购）。
- 估值极贵便于增发：EV/Sales 11.4倍（2000年峰值16倍）、EV/EBITDA 54倍。
- 已从美政府/软银/英伟达筹~$200亿（$20.47-23.28/股全部浮盈）；卖资产是昂贵的钱（3月已$142亿买回Apollo Fab34 49%）。
- 急需钱：Terafab+N3短缺溢出；14A产能从10万WSPM扩到100万；项目最高$1,190亿；资本缺口$200-350亿。
