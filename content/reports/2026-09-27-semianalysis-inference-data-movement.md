---
title: SemiAnalysis：MoE推理的计算、数据搬运与系统映射
category: reports
date: 2026-09-27
tickers: NVDA, AMD, GOOGL
tags: SemiAnalysis, MoE, AI推理, KV Cache, 网络, 存储
source: codex
---

# MoE推理系统：真正的瓶颈是状态流动与调度

**报告日期：** 2026-09-21  
**原文：** https://newsletter.semianalysis.com/p/computation-and-data-movement-for

## 一句话结论

总参数量或峰值FLOPs已不足以描述代理推理。现代MoE服务应被拆成prefill、midfill、decode attention和decode experts四种工作状态，再分别匹配计算、HBM、网络、共享DRAM/SSD和调度。最优系统不是永远解耦或永远一体化，而是让高频张量协作留在最强scale-up域、把可摊销的KV状态移到较弱网络和分层存储，并以持续小批次保持交互速度。

## 四种负载不是同一件事

1. **Prefill：** 一次处理大量新Token，权重可被充分复用，算术强度高，通常计算受限。
2. **Midfill：** 在很长的既有KV前缀上追加数百至数千Token；既有较高矩阵复用，又要搬运数十GB上下文，是计算与内存混合约束。
3. **Decode attention：** 每次只生成一个或少数Token，却要扫描每个请求私有的长KV；跨用户几乎无法共享，主要受内存带宽约束。
4. **Decode experts：** Token只携带压缩后的激活，不再需要完整历史；不同请求若路由到同一专家可共享权重读取，但小batch下命中重合少，并伴随困难的all-to-all网络。

把四类负载装进一个统一benchmark会掩盖结构优势。Prefill/midfill适合把路由结果排序成专家批次；decode为了高交互更接近batch 1—5，而不是为了总吞吐强行扩大batch。

## KV Cache应是可移动对象

报告把上下文描述为不可变blob：系统提示、项目上下文、历史轮次、工具输出和生成Token分别存储，新操作读取需要的blob并追加新blob，而不是原地改写。耐久源应是快速并行存储；刚闲置的上下文先进入共享DRAM，冷数据再下沉SSD，真正活跃的前缀才在执行前进入HBM。

这改变了“会话绑定某台GPU”的设计。RDMA可把数据直接放入加速器内存，CPU DRAM仍承担元数据、组装、复本与输出暂存。常用系统提示可缓存在机架DRAM。完成一轮对话后，数GB KV可在低于下一轮会话间隔的时间内并行搬走，使昂贵HBM立即服务下一批请求。

## MoE如何映射到机架

报告建议按自然维度并行：

- 按层组做pipeline parallel，降低每stage权重与KV占用。
- 对不可切的宽矩阵做tensor parallel。
- 把独立专家广泛分布，并让同一层的专家all-to-all留在最强本地fabric。
- 当模型和目标上下文已留出安全容量后停止增加pipeline深度；继续切分只会增加交接延迟。

一个模型可能包含约15,000个“层—专家”。72 GPU紧密同步的价值在于每GPU每层只负责少数专家，同时汇聚大量Token共享权重读取。若专家都放SRAM，单次访问能耗可能比HBM低近两个数量级，但会把瓶颈推给连接数百节点、每秒数百万Token的all-to-all网络，网络的成本与功耗可能超过计算本身。

## 小批次、高利用率可以共存

Decode小batch不等于机器闲置。云规模调度池可同时配置长/短prefill、长/短context decode等worker，利用共享存储移动状态，让每个请求独立进出连续batch。Prefill/midfill时长较可预测，decode输出长度随机；在两者间设置ready buffer，可以避免一个长回答阻塞上游。

系统需要分离时间尺度：微秒级kernel和路由、毫秒级Token流、秒级缓冲、分钟级worker重配置、小时级需求预测不能都追随同一个噪声信号。否则延迟反馈会让系统在“全满—全空”之间振荡。

## 解耦并非教条

复杂解耦会产生状态搬运、调度空隙、更多服务器设计和运维成本。如果能构建同时拥有强计算与强内存带宽的全能worker，一轮turn从midfill到decode都留在同一处，可能避免KV跨网和重新排队。代价是不同阶段总有一部分计算或内存能力闲置。

所以真正决策不是“解耦/不解耦”，而是比较：专用worker节省的硬件投资，能否超过额外网络、状态迁移、排队和运维复杂度。系统越大、请求形状越多，统计池化越有价值；小规模、固定负载可能更适合聚合。

## Kimi K3模拟结果

报告对B200、B300、GB200、16—64 GPU配置作投影而非实测。8k/32k decode在低延迟端多采用pipeline+tensor parallel，高吞吐端常退回每GPU独立attention实例并保留宽expert parallel；127k缓存+1k追加的midfill由GB200在低TTFT端领先；prefill因Blackwell计算架构相近，三者前沿更接近。

多数Pareto配置即使加上KV传输缓冲，每GPU峰值HBM驻留仍低于约80GB。模型因此支持“带宽、网络位置和调度比最大化单GPU容量更重要”，但这是基于Kimi K3和模拟器的结论，不能直接外推全部闭源模型。

## 投资含义、风险与监测

- **受益层：** scale-up网络、DPU/NIC、CPU DRAM、并行文件系统、KV管理、调度软件与可观测性。
- **GPU比较：** 必须在固定prefill/midfill/decode状态、上下文、TTFT和TPOT下比较，峰值FLOPs意义有限。
- **风险：** 模拟配置未实测；模型架构会改变KV形状；分层存储省下的HBM可能被网络和软件成本吞噬。
- **监测：** KV命中/迁移量、每层专家all-to-all、P90 TTFT/TPOT、worker切换时间、HBM有效驻留、整站tok/s/MW。

| 结论项 | 判断 |
|---|---|
| 核心论点 | 推理是状态流动与调度问题，不只是矩阵计算问题 |
| 最强证据 | 四负载算术强度差异、可移动KV、Kimi K3前沿配置明显分化 |
| 估值含义 | 网络、DRAM、存储和编排在AI服务器价值量中继续上升 |
| 催化剂 | 共享KV存储、上下文卸载、PD/attention-FFN解耦进入生产 |
| 主要风险 | 模拟而非实测、系统复杂度与网络成本被低估 |
| 行动条件 | 用端到端SLO与全栈TCO验证，不为单一微基准付溢价 |
| 信心 | 中高（架构方向），中等（具体配置） |

> 本文为研究材料复核，不构成投资建议。
