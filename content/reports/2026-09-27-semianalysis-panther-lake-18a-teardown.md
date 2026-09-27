---
title: SemiAnalysis：Panther Lake拆解与Intel 18A制造竞争力
category: reports
date: 2026-09-27
tickers: INTC, TSM, 005930.KS, AMAT, LRCX
tags: SemiAnalysis, Intel 18A, Panther Lake, PowerVia, RibbonFET, 先进制程
source: codex
---

# Panther Lake拆解：18A从路线图走到量产硅片

**报告日期：** 2026-09-26  
**原文：** https://newsletter.semianalysis.com/p/intel-panther-lake-teardown

## 一句话结论

Panther Lake证明Intel已经把RibbonFET、PowerVia和Foveros-S同时带到商业芯片，这是制造恢复的重要里程碑；但拆解不支持“18A已重夺全面制程领先”。其计算逻辑代表单元密度约与TSMC N3E GPU逻辑相当，仍未超过N3P、N2或Samsung SF2的峰值密度，高端GPU继续使用TSMC N3E，服务器路线与外部代工客户仍待验证。

## 芯粒与工艺分配

Panther Lake由计算、GPU和I/O tile通过Foveros-S放在被动硅base tile上：两种计算tile使用Intel 18A；4核Xe3 GT1用Intel 3，12核GT2用TSMC N3E；两种I/O tile均用TSMC N6。这个分配揭示真实战略：18A先承担CPU/核心数字逻辑，成熟外部节点继续承载高端GPU与模拟/I/O，降低新工艺爬坡风险。

[Intel官方资料](https://newsroom.intel.com/client-computing/intel-unveils-panther-lake-architecture-first-ai-pc-platform-built-on-18a)确认Panther Lake是首款18A AI PC平台，并强调RibbonFET、PowerVia与Foveros；但公司“相对Intel 3性能/瓦提升15%、密度提升30%”是内部节点比较，不能替代报告跨代工厂的实测几何比较。

## PowerVia：收益与代价

传统芯片把电源和信号都放在晶体管正面的金属层。PowerVia把主电源网移到背面，经nano-TSV连到源/漏接触：正面M0—M14用于信号，背面BM0—BM5供电。短而宽的背面电源线降低压降、缓解正面布线拥塞，也允许18A在紧凑cell height下保留较宽M0。

拆解看到nano-TSV从接触层到BM0约150nm，并采用Mo-lined W；正面低层使用Co/Ru、随后Co、较高层引入Nb barrier，以在电阻、填充、可靠性与工艺复杂度间折中。双AlOx etch-stop扩大刻蚀窗口，但增加沉积、清洗、界面和寄生电容。

PowerVia并非免费面积。其横向landing仍占standard cell空间，面积回收少于direct backside contact。更重要的是传统硅背面散热路径被载体、互连与绝缘介质替代，热阻上升；报告在bond stack观察到约200nm SiN、180nm SiOx、500nm SiON及约100nm界面氧化层，预计后续版本必须继续优化热路径。

## RibbonFET与密度

18A是Intel首次量产GAA：四层水平ribbon被栅极全包围；Samsung SF2对照样本为三层MBCFET。更多sheet不自动等于更高密度或性能，sheet宽度、接触、应变、阈值金属、cell height、gate pitch和布线可达性共同决定结果。

报告测得Panther Lake高性能库M0 pitch为36nm，虽然18A PDK支持32nm；18A逻辑接近五轨库，Intel 3与TSMC N3E样本约七轨。Bohr代表cell模型中，18A计算逻辑与N3E GPU逻辑密度相近，18A比Intel 3 GPU样本高约18.6%；差异主要来自cell height，三者gate pitch接近。18A M0截面积约为N3E样本2.63倍，按pitch归一后仍约1.84倍，有利于降低线阻/电流密度，但会增加电容。

## 架构与面积变化

- P-core面积与Lunar Lake几乎不变，却把私有L2从2.5MiB增至3MiB；共享P-core L3缩小14.8%。
- 四核低功耗E-core cluster缩小5%，主要来自L2区域优化。
- NPU面积缩小36.9%，在保持总INT8 MAC数下把NCE从6个减为3个，并把scratchpad与SHAVE DSP从12个减为6个；省面积但本地存储更紧。原生FP8部分缓解数据量。
- GT1的单Xe core比Lunar Lake大约69%、比N3E GT2大约55%，显示Intel 3在该实现中面积效率较弱。
- GT2的L2 SRAM宏密度约23.7Mbit/mm²，GT1约18.3；计入bank外围后约16.9对10.4Mbit/mm²。

这些结果说明Panther Lake并非纯粹的“18A全芯片胜利”。产品性能来自架构整合、缓存布局、外部N3E GPU、成熟N6 I/O和先进封装的共同作用。

## Foveros-S的经济性

Intel标称Foveros-S约36µm pitch，报告局部测得相邻microbump约25.24µm、特征宽约12.33µm。分拆tile可让高价18A只用于最需要的计算逻辑，小die随机缺陷概率更低，并可在封装前筛选；同时产生被动base、D2D、bonding、测试、封装良率和额外功耗成本。

正确指标不是单die良率，而是跨产品组合的“每个可售成品成本”。Wildcat Lake使用更高整合度、移除被动base并以UCIe连接平台控制器，说明Intel会按产品带宽与价格选择不同封装，而不是所有产品都堆Foveros。

## 投资含义

**Intel。** 最大利好是18A已从PPT变成可拆解的量产产品，执行风险下降；但foundry thesis还需外部客户、良率、成本、交期和18A-P验证。高端GPU外包N3E也说明内部工艺尚未覆盖全部最佳模块。

**TSMC/Samsung。** TSMC继续提供高端GPU与I/O节点，Panther Lake不是对其替代；Samsung SF2在峰值密度仍有竞争，但没有背面供电。节点竞争进入晶体管、供电、互连、热与封装的多维组合。

**设备材料。** 背面工艺、双面互连、Mo/W、Co/Ru、Nb、ALD/PVD与混合封装增加步骤和材料复杂度，利好刻蚀、沉积、检测与先进封装价值量，但也提高Intel资本强度和良率风险。

## 证伪与监测

1. 18A实际良率、晶圆成本、出货量和外部客户tape-out。
2. Panther Lake整机性能/瓦是否在同功耗产品上兑现。
3. PowerVia热阻是否导致频率、封装或散热成本问题。
4. Clearwater Forest服务器量产与18A-P后续节点。
5. Foveros-S装配良率、D2D功耗和不同tile复用收益。

| 结论项 | 判断 |
|---|---|
| 核心论点 | 18A量产是可信复苏里程碑，但不是全面制程领先证明 |
| 最强证据 | 实体截面确认RibbonFET/PowerVia；代表密度约等于N3E而非领先N2/SF2 |
| 估值含义 | 降低Intel制造路线失效尾部风险，尚不足以上调Foundry长期回报 |
| 催化剂 | 良率披露、外部客户、Clearwater Forest、18A-P |
| 主要风险 | 热阻、复杂工艺良率、GPU继续外包、服务器竞争力不足 |
| 行动条件 | 用产品成本、良率与客户收入验证，不以单一pitch判断节点胜负 |
| 信心 | 中高（结构观察），中等（商业回报） |

> 本文为研究材料复核，不构成投资建议。
