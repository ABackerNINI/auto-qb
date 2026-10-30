# impact-map:本项目(auto-qb)依赖影响面与联合分析 runbook

> deps-upgrade skill 的项目专属事实层。通用流程在 `../SKILL.md`,检测配置在 `deps.toml`,本文件只放**本项目具体事实**(端点、facade、task id、报告路径)。
> 迁移到其它项目 = 连同 `deps.toml` 一起整目录替换。
> 行号会漂移:引用前以 grep 复核为准(方法局限见报告 §03)。

## 1. 依赖盘点

### 1.1 三特殊依赖(联动链)

```
qbittorrent-api (pin, uv.lock)  --门控 WebAPI 版本-->  qBittorrent (watch)  --内嵌-->  libtorrent (watch)
```

- **qbittorrent-api**:唯一进 uv.lock 的特殊依赖(`pyproject.toml` 钉死 `==2026.8.1`)。按探测到的 WebAPI 版本逐端点门控(`version_introduced`/`version_removed`),对未知新版本天然前向兼容;`RAISE_ERROR_FOR_UNSUPPORTED_QBITTORRENT_VERSIONS` **不要开**(见报告 §8.4 注意事项)。
- **qBittorrent**:外部目标程序,生产对端 v5.2.3(WebAPI 2.15.1)。升级语义不是 patch/minor/major,而是「兼容性承诺有无」。
- **libtorrent**:随 qB 内嵌(2.0.x),从不直接 bump;行为变化经 qB 升级间接带入。
- **联动规则**:三者**任何一者**有更新 → 三者联合分析(库的参数双发/门控决定 qB 升级面;qB 的 WebAPI 版本决定库的门控行为;libtorrent 世代决定 qB 行为层变化)。runbook 见 §3。

### 1.2 普通 pin 依赖(pyproject 直接依赖,全部 `==` 钉死)

pyyaml / filelock / pystray / pillow / customtkinter / fastapi / uvicorn / ruamel.yaml / httpx(+ dev 组:pytest / pytest-cov / pytest-xdist / yapf)。传递闭包由 uv.lock 锁定。无特殊联动;按 SKILL.md 分档走 bump 流程即可。

### 1.3 支持矩阵口径

- **最终目的:支持 qB v5.2.3 及之后所有版本** → **特性检测优先于抬版本下界**:新能力=加探测项(字段存在性探测/响应双形态识别),不是抬 qB 版本要求。
- alpha/beta **只跟踪不承诺**;rc + stable 才入 `deps.toml` 的 support 矩阵。
- 现有锚点:qB 5.2.3(生产)/ 5.3.0;libtorrent 2.0.x / 2.1.0;qbittorrent-api 2026.8.1(钉)/ 2026.10.1(已分析)。锚点与报告路径记在 `deps.toml` `[[support]]`。

## 2. 影响面清单指要

**不整抄**——细目在两处成品里,升级分析时按需取用:

- **报告 §07**:`memory-bank/reports/26-10-31-0548-report-qb-5-3-upgrade-impact.html` —— 82 行影响矩阵(A38 端点级 + B18 行为语义 + C26 libtorrent)+ 端点/字段消费清单。
- **外部素材快照**:`D:\Projects\Else\qb-update-analysis-notes\p4-impact.md`(影响矩阵工作版)、`p5b-qbittorrentapi-support.md`(库支持度与三情形对照)。

结构性事实(比对新上游版本时的固定入口):

| 事实 | 位置 |
|---|---|
| **唯一 API 出口** = `QbApi` Facade,业务代码不碰 raw client | `src/auto_qb/core/qbapi.py` |
| 客户端构造(本地地址关 trust_env / api_key Bearer 分支) | `src/auto_qb/core/qbclient.py` |
| 启动期字段契约(21 必需 + 6 重加;缺失 fail-fast) | `src/auto_qb/torrents/compat.py`(`REQUIRED_TORRENT_FIELDS` / `RE_ADD_FIELDS`) |
| 版本差异全靠**字段探测**、无版本号解析:`next_announce` epoch / `torrents/add` 双形态响应 | `src/auto_qb/webui/commands.py`(坑档 `memory-bank/pitfalls/backend/qb-api.md`) |
| 快照对 qB 新字段前向兼容(自动落 `_raw`) | `src/auto_qb/torrents/record.py` |
| sync 增量逐键 diff、缺失=未变 | `src/auto_qb/torrents/store.py` |
| 跳检全流程(导出→删除→重加) | `src/auto_qb/core/modules/ops_mod.py` |

已知基线:5.2.3→5.3.0 分析结论 = 1 硬破坏(`torrents/setShareLimits` 必带 `shareLimitsMode`,修法是 facade 传参、与库版本解耦)+ 8 行为变化 + 6 新机会(报告 §07/§09)。

## 3. 联合分析 runbook(四工位拆解法)

触发:检测报告出现「Joint analysis triggers」,或三特殊依赖任一有上游更新。

| 工位 | 做什么 | 手段 | 产出 |
|---|---|---|---|
| **P1 上游提交提炼** | 目标版本区间的提交逐条归类(如 qB `git log release-5.2.3..v5.3.0`),官方 Changelog / WebAPI_Changelog 交叉印证 | clone 上游仓库逐提交 `git show`;重点挑「自动化工具可感知」的条目 | 分类清单 + 重点变更汇总 |
| **P2 API 深挖** | 端点级变更代码级核对:`git diff -- src/webui/api/` 逐提交核对,鉴权/路由层一并看 | 官方 changelog **未记载**的代码级事实是主要风险源,逐条与代码对账 | 端点级变更总表(含破坏性细节) |
| **P3 联动依赖** | 若 qB 大版本:libtorrent 世代差(ChangeLog 段 + qB 适配提交反推);若 qB 新 WebAPI:qbittorrent-api 是否已发支持版(README 声明 / `_version_support.py` 映射表 / src diff 零删除核验) | 库侧结论必须到**代码级**:参数双发?None 键丢弃语义?可实测(requests prepare 请求体验证) | 联动依赖支持度结论 |
| **P4 本项目影响比对** | 上游变更 × 本项目调用面(§2 的清单)逐条比对,定档 🔴破坏/🟡行为变化/🟢无影响/🔵新机会 | **源码 grep 核对,非文档推断**;用 .venv 里实际安装的库版本核对真实请求行为 | 影响矩阵 + 按优先级的动作清单 |

经验(从 5.3 分析实证):

1. **拆子任务串行**:四工位做成独立子任务(独立 agent/轮次)依次传递,P4 只吃前三工位产出,单轮上下文装不下全链。
2. **以代码为准修正上游笔记**:changelog 会漏记、外部笔记会误判(实例:P2 判 skip_checking「静默失效」被 P4 用库双发实测推翻);每条结论标「代码级/实测级/笔记级」。
3. **行号是快照**:P4 的 文件:行号 以其分析时点 HEAD 为准,引用前 grep 复核。
4. **升级目标未钉死时**:HEAD 与发布 tag 之间的增量在真正升级前复核(尤其 WebAPI 版本号)。
5. **每步独立可回滚**:facade 修复先行(可在旧版本上合入)→ 升库 pin → 再升 qB,顺序见报告 §8.5。

## 4. 本仓库测试与命令(task id)

命令一律走 task id(引擎见 commands skill),不拼裸命令:

| 场景 | task id |
|---|---|
| 全量测试(green 档硬前提) | `commands run test.full` |
| 快速迭代 | `commands run test.quick` |
| 真机跑主程序(一律先 `--dry-run`) | `commands run dev.run -- config.yml --dry-run` |
| 格式化改动的 .py | `commands run dev.fmt -- <file>` |
| 依赖同步(bump 后必跑) | `commands run env.sync` |
| 会话开工同步 | `commands run my-commit-flow.sync` |
| 提交+推送(等用户显式指令) | `commands run ship.commit` / `ship.push` |

依赖 bump 操作面:改 `pyproject.toml` 的 `==` pin → `commands run env.sync`(锁文件粘性,只动目标包)。单包定点升级/纯新鲜度检查属 uv 语义,不在包内单列 task——展开命令与深读指针用 `commands show env.sync` 看,或直接读 uv 官方文档,文档里不要手抄(命令漂移守阵会判红)。

## 5. 报告 / issue 落盘口径

- **watch 型轻量产出**(常规巡检):不建新件,`commands run kb.wrap` 切片 R 行记结论。
- **watch 型正式产出**(跨大版本首次适配):正式报告 → `commands run kb.new report`,落 `memory-bank/reports/`;体例与四工位决策树见 `memory-bank/conventions/doc-forms.md`(单文件 HTML,dark 主题)。
- **🟡 涉码改动**:入池 issue → create-issue skill(`.agents/skills/create-issue/SKILL.md`),文件名/8 类类型/档位规则以该 skill 为准,不在此复制。
- **🔵 新能力便签**:可入便签 issue(type=feat 或 question,便签档),或先记在巡检结果里由用户定。
- 测试基线数字只写 `memory-bank/testing/baselines/` 新切片,其余文档引用不手抄(AGENTS.md 产出口径)。
