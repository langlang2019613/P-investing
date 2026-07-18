---
title: MIT《Poker Theory and Analytics》全8讲详细总结
category: history
date: 2026-06-09
tags: 邮件存档
source: gmail-draft
---

我按 B 站 8P 顺序整理。公开对应 MIT OCW《Poker Theory and Analytics》，我用官方 transcript + 讲义核对，不只按 B 站字幕猜。核心先说：这门课不是“教赌”，而是把扑克拆成 EV、赔率、范围、对手模型、GTO、ICM、资金管理，这些思想也可以迁移到投资、交易、创业决策里。

第 1 讲：扑克理论导论

课程目标是建立“可分析的决策框架”，不是靠感觉打牌。老师把学习分成三层：C 基础概念，P 实战练习，A 高级技术。衡量胜负不能看单手输赢，而要看长期指标：现金局看 BB/100 hands 或 BB/hour，锦标赛看 ROI，课件给的参考是 MTT 约 30%、SnG 约 15%，也可以看小时收益。课程视角偏向线上 MTT grinder，重点是 ROI、现场锦标赛、偏保守低波动打法。

最重要的基础工具是有效筹码和 M Ratio。有效筹码等于你和仍在手牌中的最大对手之间较小的筹码量，也就是这一手最多能损失的筹码。M = 有效筹码 / (盲注 + ante 总和)，表示你还能活多少圈，也表示偷盲价值相对于你筹码的大小。还有 Q ratio = 你的筹码 / 平均筹码，以及 Effective M = M * 当前玩家数 / 10。玩家类型用 tight/loose 与 aggressive/passive 划分：TAG、LAG、tight-passive、calling machine、fish。整门课的底层思想是：先把“我有好牌吗”换成“我在什么筹码深度、什么位置、面对什么范围，哪个动作长期 EV 最高”。

第 2 讲：分析技术与方法论

本讲重点是用 PokerTracker 把牌局拆成 Decision Point，也就是每次你能 check、bet、call、raise、fold 的节点。真正有价值的分析不是盯盈亏曲线、抱怨运气、研究自己没机会行动的 walk，也不是用样本不足的统计。正确流程是：用 filter 找出具体决策点，建立对手心理模型，用统计和笔记修正模型，比较不同动作的 EV，然后循环复盘。

PokerTracker 的关键过滤维度包括：游戏类型、手牌细节、hole cards、牌面 texture、行动与机会，比如面对下注、面对加注、c-bet、fold to raise 等。统计本质都是：发生次数 / 机会次数 * 100。例如 VPIP 是 voluntarily put money in pot，RFI 是 raise first in。不要机械相信软件默认值，要先问“这个对手在这个节点的范围是什么”。

课程案例是 Fifty50 SnG 中，大盲拿 KQo 面对小筹码 open shove。默认 ICM 模型可能显示 call/push 有利，但加入对手信息后发现：Villain 73 手里只玩 11% 手牌，只 raise 过一次，样本虽小但明显偏紧。若把默认 33% 范围改成约 11%，结论从“推/跟”变成“弃牌”。关键阈值是：如果对手 shove 范围低于约 24%，KQo 就应 fold。结论：软件是计算器，不是大脑；真正的边来自你能否把对手范围估准。

第 3 讲：基础战略体系

本讲建立四个基础公式：位置、pot odds、implied odds、fold equity。位置上，越晚行动越好，因为信息更多，范围可以更宽；盲位虽然便宜看 flop，但后续每条街都先行动，处于劣势。低 M 时早位有时有主动优势，因为第一个全下的人可以最大化 fold equity。

EV 公式是：EV = Win% * WinAmt - Lose% * LoseAmt。Pot odds 规则是：Win% > CallAmt / (Pot + BetAmt + CallAmt)。例子：底池 380，对手全下 370，你有同花听牌。call 后总池是 1120，call 占 33%；9 个 outs 用 rule of 4 约 36%，精确约 34%，所以 call 是 +EV。最大可跟注额约 404。Rule of 2/4：每个 out 约等于每张后续牌 2% 胜率，如果 flop 后能看 turn+river，用 4%。

Implied odds 问的是：当前 pot odds 不够时，命中后还需要赢多少额外筹码。公式：额外所需筹码 = BetAmt / Win% - (Pot + Bet + Call)。例如 10% 胜率面对 100 下注，要让 call 合理，最终总池要到 1000，若当前 call 后池为 575，则还需要额外 425。注意 dirty outs：低同花、低顺、对子牌面上的顺/花都可能命中也输；也不要假设一次下注能免费看完 turn 和 river。

Fold equity 公式：纯 bluff 时，EV = Pot * Fold% - Bet * (1 - Fold%)，最低成功率是 Bet / (Pot + Bet)。150 bluff 进 350 pot，只需 30% fold。Semi-bluff 还有摊牌胜率，课程给的快捷规则是：所需 Fold% 约等于纯 bluff 阈值减去 1.5 * Win%。因此有真实 draw 的下注价值远高于空气 bluff。实战警告：bluff 太小不像价值牌，太大风险失控；不要 bluff calling station；不要因为怕被抓 bluff 而放弃 +EV 下注。

第 4 讲：翻前局势深度解析

翻前在锦标赛里极其重要，因为短码时大部分价值来自 push/fold。核心假设：M < 10 时基本只考虑 all-in 或 fold。翻前变量少，容易预先求解：你的牌、位置、筹码、对手 call range。范围写法要熟：QQ+ 表示 QQ/KK/AA，A2s+ 表示同花 A2 以上，ATC 表示 any two cards。简化记忆表：TT+, AQ+ 约 5%；55+, AT+ 约 10%；22+, A2+, KQ 约 20%；22+, A2+, Broadway 约 30%；对子和两张牌点数和 16 以上约 50%。

核心例子：盲注 125/250+25，大盲 1100，M=2.59；Hero 在 BTN/SB，3400，M=8，拿 96o。假设 BB call range 是 22+, A2+, JT+，约 27.6%；96o 对该范围胜率 34.26%。EV push = 72.4% * 425 + 27.6% * (34.26%*1250 - 65.74%*950) ≈ +253.5 chips。弃牌相当于放弃约 175 chips EV，所以即使 96o 也应该推。这就是短码 push/fold 反直觉的地方。

实战规则：小盲先手 heads-up，如果对手 tight，很多时候 any two cards 都可推；一般情况下，1M 推 100%，5M 推约 75%，10M 推约 50%，最大错误是 M<10 时推得太窄。大盲面对小盲 shove 的 call 规则：M=1 时 call range 可约等于对方 push range 的 10 倍；M=2 是 2 倍；M=4 是 1 倍；M=6 是 2/3；M=9 是 1/2。多人位置更保守：MP call 约 5% * 对手推牌范围，LP 约 10%，CO 约 30%，SB 约 50%。推牌方面：AT+,55+ 在 M<10 从任意位置都可推；Broadway 在 1M 任意位置、6M 晚位、10M cutoff 可推；ATC 在 1M 晚位、4M button、10M 小盲可推。

第 5 讲：决策机制与制定

这一讲是 Matt Hawrilenko 的“人类可用博弈论”。他反对只问“对手有没有 bluff”，而是要求你先问：“我整个范围在这里长什么样？”开场例子是深筹码 AA：翻牌 K-J-8，turn 5，river K，对手在 720k pot 中 overbet 约 1.08M。直觉会纠结“他是不是 bluff”，但正确方法是看自己的 river distribution：哪些手是 value，哪些是 bluff catcher，哪些必须 fold。

玩具模型一是 clairvoyance game：双方 ante，你知道自己是否赢，对手不知道，你可以 bet，对手 call/fold。若下注额为 pot 的 S 倍，防守方最低 call 频率是 1/(1+S)，进攻方 bluff-to-value ratio 是 S/(1+S)。所以对手下注 1.5 倍 pot 时，你要用能打赢 bluff 的手中约 40% 继续。这个公式解释了为什么大注需要你更少防守，但对手的 bluff/value 比例也可以更高。

玩具模型二是 A-K-Q game，用来映射真实牌局中的 value、bluff catcher、bluff。关键概念是 read your own hand：不是读你手上这两张牌，而是读你走到当前节点的整个组合分布。每条街都要用两件事更新范围：card removal 和自己的行动。对子有 6 个组合，offsuit 有 16 个组合，suited 有 4 个组合。你如果用不同下注尺度切割不同手牌，就会 needless bifurcate distribution，让自己容易被反向利用。

实战原则：如果你的范围强到必须 fold AA，甚至 fold trips，那不一定是 river 错了，可能是前面街的范围构造太窄。规则是：如果某类牌你想 value bet，最好构造一个不需要在后面被迫 fold 它的分布。剥削打法也不是“我读到他 bluff，所以我 hero call”，而是 在边际上移动：对手 bluff 太多，扩大 marginal calls；value bet 不足，收缩 marginal calls；fold 太多，扩大 marginal bluffs、减少薄 value；call 太多，扩大薄 value、减少 bluff。读牌信心通常会被高估，所以不要从边际直接跳到极端。

第 6 讲：扑克经济学原理

Aaron Brown 这一讲不是普通打法，而是讲扑克、信用、期货市场、量化金融之间的共通机制。他的核心论点是：扑克不是单纯游戏，而是一种训练人理解信用创造、清算、mark-to-market、风险承担、信息网络的经济制度。早期扑克不是用现金，而是用个人发行的 poker checks，即带有个人信用的筹码/欠条。赢家拿到别人的 checks，本质上获得对别人的债权；输家则进入一个需要履约、工作、交易、偿还的网络。没有中央清算方，靠个人信用和 ring clearing 运转。

他把早期扑克和 wildcat bank、soft money bank 类比：都不是先有完整现金储备，而是先创造信用，再通过关系、声誉、清算机制维持价值。这个视角解释了为什么扑克特别适合边疆经济、地下经济、创业型经济：现金稀缺，但人可以用信用、能力和关系创造交易。扑克桌同时是信息市场、信用市场和人际网络。

他进一步把期货交易所与扑克类比：芝加哥期货市场不是简单为了农民 hedge，而是为加工商、贸易商、运输商创造信用和定价服务。期货市场的 mark-to-market、清算、价差交易，和扑克每轮下注后筹码对齐、结束后清算很像。比如磨坊主买入现货小麦、卖出远期小麦，本质是“借入小麦”，而不是单纯对冲价格。期货市场还给运输、仓储、等级、时间价差等服务定价。

最后他讲到量化金融文化：赌场、体育博彩、扑克训练出的人，后来进入华尔街。赌场型人才擅长机械优势和隐蔽执行，体育博彩人才擅长预测人群下注行为，扑克人才介于两者之间，既懂数学又懂人和网络。关键思想是：现实世界不像骰子那样随机；如果系统足够精密，就有可预测结构，如果系统粗糙，就有非均匀模式。量化投资的真正边来自：小优势、重复下注、风险控制、冷冰冰用现金验证判断，而不是专家的自信叙事。

第 7 讲：博弈论及其应用

Bill Chen 讲 Cepheus 和计算机扑克。Cepheus 是 University of Alberta 对 heads-up limit hold’em 的近似 GTO 解，花了约 900 CPU-years，把 exploitability 降到小于 1/1000 big blind，几乎不可区分于完美策略。这是第一个被“解决”的真实扑克游戏，但不等于所有扑克都被解决，尤其 no-limit、多玩家、锦标赛仍复杂得多。

Nash equilibrium/GTO 的含义：一组策略中，任何玩家单方面改变都无法提高收益。在两人零和游戏里，GTO 也是 min-max 策略，保证你不被对手利用。它不一定是打弱玩家最赚钱的方式，例如石头剪刀布对手如果只出石头和剪刀，你应 100% 出石头，而不是均衡的 1/3；但 GTO 给你不可剥削的基准。

算法核心是 regret minimization。Regret 是“如果我一直选另一个策略，本可以多赚多少”。每轮根据正 regret 分配策略权重，长期平均 regret 会趋近 0。两方互相做 regret matching，就会逼近 GTO。CFR，即 counterfactual regret minimization，把这个思想放到每个信息集节点上，用“假设我能走到这个节点”的概率来更新 regret，因此可以处理不完全信息游戏。CFR+ 又把负 regret floor 到 0，并用更高效的树搜索和权重调整。

规模非常大：limit hold’em 只看 river 节点，就有约 1755 类 flop、9^3 种前几街行动、2352 种 turn/river，约 30 亿行动序列；再乘 2126 种 river hand type，得到约 6.5e12 个 hand-river 类型，每个节点还要访问约 1000 次。Omaha 8 因为四张底牌，大约是 hold’em 的 82.5 倍；Razz 约 374 倍；no-limit 的难点是下注尺度连续，离散化以后相邻尺度 EV 接近，regret 收敛更慢；多人游戏没有保证收敛到唯一 Nash，卫星赛/多支付结构还会出现多个均衡甚至类似合谋均衡。

第 8 讲：锦标赛实战策略

锦标赛和现金局最大区别是：现金局 chips = money，锦标赛 chips 只是影响名次概率，cEV ≠ $EV。锦标赛有固定买入、盲注上升、不能随时离场、方差更大，但 ROI 可能更高，也更容易形成可见 track record。核心概念是 tempo，也就是你在不同阶段要用正确 aggression。

按 M 分区：M<2 是 dead zone，几乎没有 fold equity，目标是恢复 fold equity，绝不要主动跌破 M=1。2<M<8 是 steal period，只做 all-in 或 fold；偷一次盲注可能让筹码增加 10%-40%，价值大于很多摊牌边际。8<M<12 是 steal/re-steal period，你的 3BB steal 约等于 2M，被 6M shove 时不一定必须 call，所以有 fold option。12<M<30 是 value betting zone，可以看 flop，尽量 raise 入池、heads-up 后 c-bet；不要用 TPTK、低两对、明显危险牌面上的 set 轻易打光。M>30 是 set mining zone，便宜看口袋对子，等隐蔽强牌，但 50M 深度不要拿非 nuts 轻易打光。

中筹码 postflop：标准 preflop raise 是 3BB + 每个 limper 加 1BB；flop/turn/river 下注通常约 2/3 pot，用来让 draw 无法 +EV。开局范围：盲位/UTG/UTG+1 用 TT+, AQs+, AKo+；中位 88+, AJ+, KQ+；晚位/CO/BTN 可加入 77+, Axs, 高 suited connectors。面对 raise 时更紧：早/中位 TT+, AQs+, AKo+，晚位 88+, AJ+, KQ+。心理层级：L0 不读牌，L1 看自己牌，L2 看对手牌，L3 想自己代表什么。你最好只比对手高一层；对不会读你的新手玩 L3 bluff，常常是自杀。

Bubble 阶段通常在离钱圈约 10%-20% 人数时出现，ICM 开始主导。业余玩家往往太紧，后来有些环境又会变得过度激进，所以要快速判断桌上是 bad folds 多还是 bad calls 多。ICM 例子非常关键：4 人等筹码 2500，奖金 1000/600/400/0，每人 equity 是 500；一人赢下另一人变 5000 后，他 equity 不是 1000，而是约 766，另外两名幸存者从 500 升到约 616，因为被淘汰者的 equity 被幸存者分享。卫星赛更极端：10 人 9 张 $10k 门票，所有人等筹码时每人 equity $9000；Hero 拿 KK 面对 all-in，KK 对 ATC 胜率 82%，chip EV 是 +1600，但 dollar equity 是 82%*$10000 = $8200，比 fold 的 $9000 低，所以 call 是 -$800，甚至 AA 也可能应该弃。

资金管理：bankroll 不是账户里多少钱，而是“如果亏光，会迫使你停止扑克活动的钱”。规则只适用于正期望玩家；负期望无论 bankroll 多大都会长期破产。以约 2% risk of ruin 为基准，NL 现金局约 20 个 max buy-ins，limit 约 300 big bets，单桌锦标赛 30 个 entries，MTT 50-100 个 entries。Kelly Criterion 的例子：如果一比一下注有 60% 胜率，理论上下注 bankroll 的 20%。WSOP 主赛 6000+ 人、$10k buy-in，合理 bankroll 可能超过 $1M；即使高手有 +50% ROI，单场方差也巨大，所以常见 staking、卖份额、互换百分比，本质是把高方差投资切小、分散和转移风险。

总复盘

这 8 讲合起来是一套决策系统：第 1 讲定义长期胜利和 M；第 2 讲教你用数据复盘具体决策点；第 3 讲给 EV、pot odds、implied odds、fold equity；第 4 讲把短码翻前变成范围和 Nash/push-fold 表；第 5 讲把单手思维升级成分布思维；第 6 讲把扑克映射到信用、市场和量化金融；第 7 讲解释 GTO/CFR/计算机求解；第 8 讲把所有东西放进锦标赛、ICM 和资金管理。真正的精髓是：不要问“我这手牌强不强”，要问“在这个结构下，我的范围、赔率、对手范围、未来风险和资金约束合起来，哪个动作长期期望最高”。

来源：
B 站：
MIT OCW 官方课程资料与 transcript：https://ocw.mit.edu/courses/15-s50-poker-theory-and-analytics-january-iap-2015/resources/lecture-videos/
