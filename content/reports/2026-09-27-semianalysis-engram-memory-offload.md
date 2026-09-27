---
title: SemiAnalysis：Engram条件记忆与DRAM/SSD卸载经济性
category: reports
date: 2026-09-27
tickers: NVDA, AMD, MU, 000660.KS, 005930.KS
tags: SemiAnalysis, Engram, DRAM, SSD, HBM, AI推理
source: codex
---

# Engram条件记忆：把稀疏知识从HBM移到DRAM

**报告日期：** 2026-09-18  
**原文：** https://newsletter.semianalysis.com/p/engrams-embedding-entendre-codesign

## 一句话结论

Engram不是给模型外挂一个普通字典，而是把高频多Token模式编码成可学习的稀疏查找表，与MoE专家路由共同训练。因为每个Token只访问极少数行且地址由Token ID预先决定，这部分参数天然适合从HBM卸载到主机DRAM并与前层计算重叠；报告实测DRAM卸载几乎不损失整体性能，反而可减少Tensor Parallel规模并改善TCO。SSD在当前未优化路径下则全面落后于DRAM。

## 机制与模型质量

Engram用二元、三元或四元Token后缀做哈希，从多张embedding表取回向量，经投影、门控和短因果卷积后写回残差流。地址只由Token ID决定，而非隐藏状态，因此runtime能在更早层计算时预取数据；这与必须整块读取的稠密权重不同。

[DeepSeek原始论文](https://arxiv.org/abs/2601.07372)把inactive parameter预算在MoE专家和Engram表之间分配，loss呈U形，意味着把全部容量只给专家或只给记忆都不是最优。SemiAnalysis按论文设置、约6E18 FLOPs/次训练复现实验，也观察到相同趋势。

探针显示Engram高门控内容包括人名、代码片段、关系短语、许可证与网页模板。这说明它优化的是训练目标中的可预测模式，不是“人类认为重要的事实”。数据清洗因此会影响条件记忆的边际价值。

删除Engram会改变后续特征和专家选择，并非简单丢掉一张表。CRUXEval teacher-forced实验中，答案loss由0.2848升至0.3093 bits/token；若强迫无Engram模型沿用原专家路径，进一步恶化到0.3375，说明重新路由可部分补偿记忆缺失。保留prefill Engram通常比只在decode保留更有用，因为更丰富的语义已被写入随后传递的KV Cache。

## DeepSeek V4.1 Flash的内存量

报告估算DeepSeek V4.1 Flash在第1和14层配置约196.6B Engram参数，卸载表约188.8GiB。每个Token位置在两层合计取24行、总流量约12.4KiB；若4卡切分，每GPU约3.1KiB。表很大、单次访问极稀疏，正是外部内存友好的形状。

Qwen3.8-Flash-Next使用8个bigram和8个trigram哈希，表约51.2B参数；每Token只取16个、每行160维的向量，BF16下约5KiB。LongCat也独立发展n-gram embedding，并建议等专家数越过甜点后再加入、占总参数不超过50%。这表明条件记忆可能成为模型架构趋势，而非单一DeepSeek技巧。

## DRAM卸载为何可能更快

HBM与DRAM方案使用相同GPU kernel选择并反量化行：HBM直接读显存；DRAM通过UVA直接读锁页主机内存。把整张表搬进HBM只加速很小的稀疏lookup，却占用本可容纳KV Cache的昂贵显存，对decoder计算与通信没有帮助。

在B300周零软件栈上，把Engram从DRAM搬回HBM的结果落在运行波动内。更关键的是，DRAM卸载使B300副本能从TP4降到TP2，减少通信，Pareto前沿最多改善约1.6倍。这里的收益不是“DRAM比HBM快”，而是释放HBM后允许更优的并行布局。

## SSD为何暂时失败

报告用B200、memory-mapped本地SSD和未优化vLLM fork测试。SSD路径需要把row ID送CPU、去重、收集到锁页缓冲区、再拷回GPU并反量化，且未启用GDS。即使页面已在文件系统缓存中、没有物理SSD读取，协调与CPU往返仍存在。

在约125 tok/s/用户时，DRAM方案约121百万Token/美元，SSD约52百万；观测到的所有SSD点都被某个DRAM点同时在P90交互速度和Token/美元上支配。便宜介质不自动带来低成本服务：如果SSD没有减少GPU数量、主机配置或创造新可售容量，四张昂贵GPU仍然存在，经济收益为零。

## 对硬件与软件生态的含义

- **HBM：** Engram降低同质量模型的容量需求，却不等于HBM需求下降；释放的容量可用于更大KV和更多并发，且decode依然依赖HBM带宽。
- **服务器DRAM：** 从“CPU附属内存”升级为推理工作集的二级活跃层，内存通道、UVA/RDMA、锁页容量和能耗变重要。
- **NVMe：** 当前路径不经济；若未来GDS、GPU直取、预测预取和冷热行缓存成熟，才可能成为低频Engram与KV的三级层。
- **Nvidia/AMD：** DeepSeek V4.1 Flash发布首日，Nvidia六个SKU的vLLM直接可用；AMD镜像延迟且初期性能/美元显著落后。报告七日快照中MI355X仍约比B200差2—4倍，表明“Day-0软件”本身就是商业护城河。

## 风险与验证边界

SSD实现明确未优化且没开GDS，不能据此否定长期NVMe价值；DRAM结果来自特定模型、服务器与UVA路径；条件记忆依赖训练数据和哈希碰撞，规模扩张可能记住大量低价值模板。DeepSeek原论文的消融是训练—推理不匹配，不能等同于“有无Engram从头训练”的纯收益。

## 监测清单

1. vLLM/SGLang是否把DRAM Engram offload上游化并保持decode graph。
2. DRAM卸载能否在不同CPU、NUMA、PCIe/CXL拓扑复现。
3. 启用GDS与GPU直取后的SSD Pareto前沿。
4. 新模型的Engram参数占比、命中分布和质量增益。
5. HBM释放是否真正减少GPU副本规模，而非只增加闲置容量。

| 结论项 | 判断 |
|---|---|
| 核心论点 | 稀疏条件记忆天然适合DRAM卸载，并可改善并行布局 |
| 最强证据 | B300 DRAM与HBM总体性能相近，TP4降TP2最多改善约1.6倍 |
| 估值含义 | 提升服务器DRAM与内存软件价值；当前不支持SSD推理需求大幅上修 |
| 催化剂 | 上游实现、GDS/直取、更多模型采用Engram |
| 主要风险 | 单模型单平台、SSD实现不成熟、记忆内容质量不可控 |
| 行动条件 | 必须证明卸载减少全栈成本或增加可售吞吐，而非只减少HBM占用 |
| 信心 | 中高（DRAM方向），低至中（SSD前景） |

> 本文为研究材料复核，不构成投资建议。
