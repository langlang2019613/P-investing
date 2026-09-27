---
title: SemiAnalysis：4-hi HBM的推理经济性与存储产业链影响
category: reports
date: 2026-09-27
tickers: NVDA, MU, 000660.KS, 005930.KS
tags: SemiAnalysis, HBM, DRAM, AI推理, 半导体, 存储
source: codex
---

# 4-hi HBM：从容量竞赛转向单位晶圆Token产出

**报告日期：** 2026-09-13  
**原文：** https://newsletter.semianalysis.com/p/long-live-the-short-king-why-4-hi

## 一句话结论

报告提出一个明显逆于过去数年的判断：面向高交互推理，HBM不应继续机械追求更高堆叠与更大单卡容量；当机架级总容量已越过“模型权重+有效KV Cache”的安全阈值后，4-hi HBM可用更少DRAM die提供相同接口带宽，使成本/带宽、Token/HBM晶圆和封装良率同时改善。该结论对推理ASIC较强，对预训练与未来超大模型并不普遍成立。

## 需求为什么从容量转向带宽

传统训练要在HBM中保存权重、梯度与激活，容量约束很强；decode每生成一个Token，都要读取活动权重和用户KV Cache，更容易受带宽约束。随着算力从一次性预训练转向后训练、强化学习与在线推理，边际计算更偏向带宽敏感。

同时，尺度单位已经由单卡变成机架。H100 HGX总HBM约640GB，Llama 3.1 405B权重曾占其中约63%；GB300 NVL72把scale-up域扩大9倍、单GPU HBM约翻倍，机架总容量接近21TB，而MXFP4量化的2.8T Kimi K3副本约1,561GB，不到该机架HBM的8%。Rubin Ultra NVL576再把域扩大8倍。因此，单GPU容量下降不必然意味着系统容量不足。

## 4-hi为何能保留带宽

HBM4/HBM4E每个cube有2,048条数据I/O，单个核心DRAM die最多承载512条，因此4-hi已经能用满全部I/O。降低到4-hi会减少位容量，却不减少每个cube的接口宽度。报告的HBM4E示例假设13Gbps针脚速率：每个stack约3,328GB/s；4/8/12-hi分别提供16/32/48GB容量。成本主要随GB数上升，而推理解码的价值往往来自GB/s，这使4-hi的美元/带宽更优。

报告以Rubin Ultra NVL576运行Kimi K3作roofline推演：4/8/12-hi对应每GPU 128/256/384GB；在105 tok/s/用户时，12-hi相对8-hi不再增加吞吐；在213 tok/s/用户时，超过4-hi的容量不再产生收益。8-hi和12-hi相对4-hi的最大总吞吐增益只有约8%和10%，但报告模型中的整机成本溢价分别为12.1%和26.3%，因此单位Token成本反而更高。

## 实测与反例

SemiAnalysis还在16张GB300、8卡prefill+8卡decode的Kimi K3配置上压缩可用HBM。每GPU KV预算从53GB降至34GB，或在解耦配对中从44GB降至24GB；大多数前沿点吞吐接近不变，直到并发超过70、KV占用触顶后，受抢占、重复装载与排队影响，吞吐才骤降近30%。受限配置从DRAM读取KV的次数超过正常配置10倍，说明DDR卸载能缓冲容量不足，但不能消灭极高并发下的容量拐点。

最重要的反例是未来模型变大。若未来模型与单用户KV都达到Kimi K3的3倍，12-hi和8-hi相对4-hi可多提供47%和36%吞吐；考虑成本后，8-hi在低于约180 tok/s/用户时可能更划算。报告因此真正支持的是“按工作负载选择堆叠高度”，而非所有场景统一转向4-hi。

## 产业链与利润分配

- **Nvidia/ASIC设计者：** 低堆叠可缓解HBM短缺、降低BOM并增加可出货系统数，但瓶颈会转移到逻辑晶圆、base die、CoWoS、基板、PCB、整机集成和电力。
- **Micron：** 报告称Micron正在为至少两家客户测试4-hi，而三星与SK海力士仍抵触低堆叠。若Micron先行，可能获得新SKU的份额与溢价。
- **三星/SK海力士：** 低堆叠减少每个stack的bit含量，不利于延续HBM对DRAM晶圆的高消耗；但报告估算4-hi可按GB收取约10%溢价，加上更高封装良率，单位利润率可能反而更好。
- **普通DRAM：** 若4-hi释放DRAM晶圆，可缓解服务器DDR等产品被HBM挤占的供给压力，但需求转移的实际幅度取决于加速器、base die和封装能否同步扩产。

## 独立核验与争议

[Nvidia公开资料](https://nvidianews.nvidia.com/news/nvidia-vera-rubin-platform)确认Rubin平台已把GPU、CPU、NVLink、网卡、DPU和上下文存储作为一个系统协同设计，但并未公开背书报告关于Rubin Ultra HBM容量、4-hi客户选择或供应商态度的全部细节。因此，192GB、客户测试与供应商抵触属于报告渠道信息，不能当作公司指引。

最大的模型风险有三项：roofline使用峰值带宽而非持续带宽；Kimi K3不能代表未来五年全部模型；TCO以硬件成本为主，未完整计入因容量不足带来的调度、网络、DDR/SSD和工程复杂度。4-hi应被视为专门面向高交互推理的SKU，而不是训练通用替代品。

## 投资监测清单

1. HBM4/HBM4E量产SKU是否出现4-hi及其认证客户。
2. Rubin Ultra最终每GPU容量、机架域大小和实际可售时间。
3. 同模型、同SLO下4/8/12-hi的tok/s、并发和美元/Token。
4. KV卸载后的DDR带宽、网卡与SSD开支是否吃掉HBM节省。
5. Micron、SK海力士、三星的HBM产品组合、ASP/GB和封装良率。

| 结论项 | 判断 |
|---|---|
| 核心论点 | 推理时代应优化Token/HBM晶圆，而非单卡GB |
| 最强证据 | 机架总容量扩张、4-hi不损失接口带宽、成本增幅高于模拟吞吐增幅 |
| 估值含义 | 有利于推理系统TCO与Micron先发机会；不等于HBM总需求见顶 |
| 催化剂 | HBM4客户认证、Rubin Ultra定规、4-hi正式SKU |
| 主要风险 | 模型/KV增长超预期、卸载成本、报告渠道信息未获公司确认 |
| 行动条件 | 观察真实SKU和同口径benchmark后再调整存储供应商盈利假设 |
| 信心 | 中等 |

> 本文为研究材料复核，不构成投资建议。
