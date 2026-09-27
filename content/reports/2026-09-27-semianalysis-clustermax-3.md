---
title: SemiAnalysis：ClusterMAX 3.0 GPU云评级与供应商分化
category: reports
date: 2026-09-27
tickers: CRWV, NBIS, GOOGL, ORCL, MSFT, AMZN, NVDA, AMD
tags: SemiAnalysis, Neocloud, GPU云, ClusterMAX, 云计算, AI基础设施
source: codex
---

# ClusterMAX 3.0：GPU云的价值从“有卡”转向“有效作业”

**报告日期：** 2026-09-23  
**原文：** https://newsletter.semianalysis.com/p/clustermax-30-the-industry-standard

## 一句话结论

在GPU重新短缺的市场里，采购者最容易犯的错是只比较美元/GPU小时。ClusterMAX 3.0覆盖323家供应商、详细评估77家，并把托管集群拆成计算、网络、存储、编排、监控、支持、安全与可靠性；最终只有19家取得奖牌级评级。CoreWeave仍是技术标杆，Nebius升至Platinum；Google与Oracle为Gold。评级说明大规模训练/推理的真实成本取决于goodput与故障恢复，而不是名义卡数。

## 评级对象与方法边界

ClusterMAX评的是“客户拿来即可运行的托管集群”，不是powered shell、裸金属租赁、按Token API、RLaaS或模型质量。理想用户有大量算力预算，却不希望自己处理Slurm、Kubernetes、NAT、坏卡、存储挂载与网络调优。

测试分为三阶段：

1. **配置与卫生：** GPU/CPU/内存规格、驱动、固件、ACS、GPUDirect RDMA、IMEX、镜像与安全补丁。
2. **性能：** 计算、NCCL/网络、存储微基准和真实负载，设定通过阈值。
3. **可靠性：** 主动/被动健康检查、XID与PCIe故障、节点重启、自动cordon/drain/替换、监控和SLA。

可靠性是最重要维度。软故障未必写XID，却会让整个job等待慢rank；如果平台没有straggler检测、自动修复和备用容量，便宜GPU会转化为更贵的有效训练小时。

## 主要评级

| 等级 | 供应商 | 核心判断 |
|---|---|---|
| Platinum | CoreWeave、Nebius | CoreWeave技术与可观测性领先；Nebius在产品、供给与商业定价上成为默认高端Neocloud |
| Gold | Google Cloud、Oracle | GCP托管Slurm/GKE成熟；Oracle凭大单交付与AMD支持保持高位 |
| Silver | Lambda、Microsoft Azure、Firmus、TensorWave、GMI | 基础能力较强，但支持、可靠性、产品化或硬件路线仍有明显短板 |
| Bronze | AWS、Gcore、GMO、Verda、Moonlite、Together、Crusoe、Prime Intellect、DigitalOcean、Hyperstack等 | 可用但需客户投入更多工程；部分厂商存在可靠性或卫生问题 |
| Participation Ribbon | Vultr、Vessl、RunPod、Bitdeer、Shadeform等 | 做到基本供给，尚未形成可信托管集群体验 |

报告新增Participation Ribbon，避免把“勉强可运行”和真正underperforming混为一谈。Fluidstack变为Unavailable，Crusoe降至Bronze，Azure降至Silver，GMI从Bronze升Silver。

## 头部供应商拆解

**CoreWeave。** 继续设定技术标杆。其GPU straggler detection读取NCCL telemetry识别没有明显错误码的慢卡，并直接给出修复建议；价值在于减少客户二分排查和大作业浪费。风险不在本次技术评级，而在商业层：长期合同可能使其无法完全享受近期租价上涨。

**Nebius。** 从上次第二名但Gold升为Platinum。技术细节仍可能落后CoreWeave，但供给、产品、支持和商业决策让其能对Neolab收取溢价；这证明技术评级与股票估值并非一回事，定价权和合同结构同样重要。

**Google Cloud。** GKE与托管Slurm终于达到Gold；缺点是控制台和访问流程笨重，GB200 GKE曾出现默认StorageClass无法挂载的配置问题。它的优势是深厚的系统人才和TPU/GPU双栈，风险是大组织产品化速度。

**Oracle。** 零适用CVE的自动化卫生表现突出；测试中AMD驱动问题没有被健康检查捕获，但Oracle能快速协调AMD定位并打补丁。其增长依赖OpenAI、Meta、Nvidia等大型合同，集中度高，但对AMD路线的支持是差异点。

**Lambda/TensorWave/GMI。** Lambda的合成XID可在15分钟内自动修复，但真实XID 79在Kubernetes层缺乏可见性、约2小时后才恢复。TensorWave是领先的AMD专属云，能否借MI455X/Helios进入Gold取决于软件和大规模交付。GMI计算与InfiniBand扎实、存储改善，但Kueue与DRA resource claim冲突暴露产品细节不足。

## 降级信号与采购风险

AWS的产品菜单和组织复杂度使托管集群不是核心优先级；Together因可靠性问题降至Bronze；Crusoe测试中出现异常密集XID、旧CVE与工程人才流失信号。许多中尾部供应商的问题并不高级：没有SOC 2/ISO 27001、ACS未关、GPUDirect RDMA未开、集群创建或硬件故障期间仍计费、RBAC/SSO/审计日志缺失。

报告还测试了编码代理辅助运维。代理在目标清晰、上下文完整时显著放大工程效率；但也会用循环压垮Slurm controller、绕开NVLink误用InfiniBand、在NVMe而非NFS上跑存储测试，甚至把CPU节点当GPU节点。它放大专家能力差距，而不是自动抹平差距。

## 商业含义与估值框架

评级不是企业质量或股价排序。采购方应把合同价格换算为：

`有效GPU小时成本 = 合同总成本 ÷（可用GPU数 × 运行时间 × goodput × 可接受作业成功率）`

供应商若能用健康检查、自动修复和支持减少停机，即使标价更高也可能更便宜。投资者还要叠加合同期限、客户集中度、融资成本、机房电力、硬件代际和转租结构。技术Platinum不保证股权回报，技术Bronze也不必然意味着裸金属或土地业务无价值。

## 证据边界与监测

评级来自SemiAnalysis自有测试，分配规模和测试时长不足以覆盖所有真实故障；供应商修复速度快，结果有时间点效应；部分未复测厂商沿用旧信息。应关注完整dashboard、合同SLA、客户reference和持续复测，而不是只引用奖牌。

| 结论项 | 判断 |
|---|---|
| 核心论点 | GPU云应按goodput、可靠性与支持定价，而非名义GPU小时 |
| 最强证据 | 77家深度评估仅19家奖牌级，头部自动修复与尾部基础配置差异巨大 |
| 估值含义 | CoreWeave/Nebius具技术或商业溢价；合同结构可覆盖或抵消技术质量 |
| 催化剂 | Rubin/Helios交付、复测升级、SLA标准化、EndpointX等新评级 |
| 主要风险 | 自有方法不完全透明、样本期有限、供应商快速修复、评级非财务评级 |
| 行动条件 | 将评级与租价、利用率、债务、客户集中和代际迁移联合评估 |
| 信心 | 中高（技术相对排序），中等（投资映射） |

> 本文为研究材料复核，不构成投资建议。
