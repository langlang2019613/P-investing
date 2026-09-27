---
title: SemiAnalysis：Vera Rubin代理推理性能与每GW盈利模型
category: reports
date: 2026-09-27
tickers: NVDA, AMD
tags: SemiAnalysis, Vera Rubin, GPU, AgentX, AI推理, 数据中心
source: codex
---

# Vera Rubin NVL72：代理推理性能与每GW经济性

**报告日期：** 2026-09-14  
**原文：** https://newsletter.semianalysis.com/p/vera-rubin-nvl72-agentic-inference

## 一句话结论

Rubin在AgentX长上下文、多轮、缓存复用负载上的优势是真实且显著的，但“67倍”是特定170 tok/s、特定GB300 TensorRT-LLM曲线端点和拥有成本口径的对比，不能代表整条前沿。更稳健的结论是：在常见60—100 tok/s服务区间，Rubin相对当前最佳GB300配置约有1.4—3倍Token/TCO优势，并可在电力受限的数据中心创造更高每GW收入。

## 测试对象与口径

AgentX模拟真实代理流量：会话有大量轮次、长上下文、高前缀复用、工具调用和短期sub-agent突发。报告采用早期预发布TensorRT-LLM软件测试Vera Rubin NVL72，并同时比较GB300、B300、B200、H200和MI355X。TCO分为两类：

1. 大型云厂商自有成本：服务器与网络资本开支、折旧、机房、电力和资本成本。
2. 三年云租赁：基于市场询价的每GPU小时合同价。

Rubin机架是GPU、Vera CPU、NVLink 6、ConnectX-9、BlueField-4与Spectrum-6协同设计。[Nvidia官方资料](https://investor.nvidia.com/news/press-release-details/2026/NVIDIA-Kicks-Off-the-Next-Generation-of-AI-With-Rubin--Six-New-Chips-One-Incredible-AI-Supercomputer/)确认NVL72由72颗Rubin GPU和36颗Vera CPU组成，并把上下文存储作为agentic inference基础设施的一部分，支持报告关于“系统而非单卡”的方向；但第三方性能倍数仍来自SemiAnalysis当前测试。

## 读懂“67倍”与正常区间

在170 tok/s且采用自有成本时，Rubin相对GB300 Dynamo TensorRT-LLM测得约67倍总吞吐/TCO；问题是后者接近自身最高速度端点，吞吐已经很低。若同一速度改与GB300 SGLang比较，优势约5.56倍。报告自身也强调engine标签不可省略。

在更现实的60—100 tok/s区间，Rubin相对最新GB300方案约1.4—3倍。Rubin最高P90 interactivity约276.24 tok/s，GB300 TensorRT-LLM约171.53 tok/s，高约61%；但GB300使用开源SGLang时可接近Rubin的最高交互速度，说明软件栈选择会改变结论。

按三年租赁，报告采用Rubin每卡每小时高于8.5美元、Blackwell Ultra约5美元的2026年7月价格。即使Rubin租价更高，在80 tok/s时仍可用同样租赁TCO产出约62%更多Token；极高交互区间的优势可扩大，但对曲线端点敏感。

## 电力约束与每GW模型

100 tok/s时，Rubin约59.4百万tok/s/MW，GB300 SGLang约28.5百万、GB300 TensorRT-LLM约21.1百万；对更强GB300引擎的优势约2.09倍。150 tok/s时约7.2倍，200 tok/s时降到2.72倍，说明倍数随SLO并不单调。

报告在75 tok/s、60%利用率、无模型许可费的假设下推算：

| 平台 | 年收入/GW | 模拟年利润/GW |
|---|---:|---:|
| Vera Rubin | 1,595亿美元 | 1,499亿美元 |
| 最强GB300对照（SGLang） | 1,149亿美元 | 1,053亿美元 |

Rubin因此多约39%收入、42%利润，即每GW约增加446亿美元模拟利润；若线性缩放，10MW约4.46亿美元。该数字是Token售价、持续需求、60%利用率和线性扩展共同决定的情景输出，不是Nvidia或云厂商指引。

Rubin还支持动态功率调度。若真实推理负载长期低于峰值TDP，运营商可根据功率曲线提高同一园区的GPU密度。但收益必须以utility meter、PUE、网络和CPU功耗全口径衡量，而不能只按GPU TDP。

## 生命周期与部署时点

GB300先部署、先产生现金流；Rubin单位时间收入更高。报告情景中，10MW Rubin达到约430万美元/日，选定的GB300 TensorRT-LLM约253万美元/日；若Rubin按测试时点开始服务，累计收入约在2026年10月下旬超过GB300。这只是收入交叉，不是资本回收期：交付延迟、爬坡、价格下降、需求不足或软件成熟速度都会改变结果。

## 投资含义与风险

- **Nvidia：** 代际升级价值来自整机架和软件协同，支持高ASP和更快替换；但过大的宣传倍数容易掩盖基准选择。
- **Neocloud/模型服务商：** 电力稀缺时Rubin有更高Token/GW和定价空间；只有拿到硬件、保持利用率并获得低成本融资才能兑现。
- **AMD：** MI355X在该快照与模型上明显落后，但报告承认不同模型、软件成熟度和未来MI455X会改变比较。
- **风险：** 早期软件、单一模型、供应商协作测试、插值点、FP4/FP8差异、不同引擎与成本假设都可能放大倍数。

## 监测清单

1. Rubin量产软件在vLLM、SGLang和TensorRT-LLM三套栈的同日结果。
2. 60/80/100/150 tok/s固定SLO下的tok/s/MW与Token/TCO。
3. 真实租赁成交价、机架交付时间和可用率。
4. utility MW口径的整站功耗与动态功率调度收益。
5. GB300价格下降能否抵消Rubin性能差距。

| 结论项 | 判断 |
|---|---|
| 核心论点 | Rubin显著提高代理推理的Token/TCO与Token/GW |
| 最强证据 | 常见服务区间1.4—3倍优势及100 tok/s约2.09倍tok/s/MW |
| 估值含义 | 支持Nvidia系统级溢价，也提高高利用率算力运营商的每MW价值 |
| 催化剂 | 量产交付、开源引擎成熟、第三方复验 |
| 主要风险 | “67倍”端点效应、早期软件、成本和Token价格假设 |
| 行动条件 | 采用整条Pareto前沿与全站功耗，不用单点最高倍数决策 |
| 信心 | 中高（方向），中等（盈利绝对值） |

> 本文为研究材料复核，不构成投资建议。
