# AGENTS.md

> 所有AI编码代理的统一入口。完整知识库在`memory-bank/`(Memory Bank模式)—本文件只放**路由与硬约束**;不要凭印象回答项目问题,按路由深入后再动代码。
> ⚠本文件有**8000字符硬上限**——超出部分IDE注入时被静默截断,尾部内容模型看不到。改完用`commands run doc.caps`自查。

## 知识库路由(两层:本文件粗路由→`memory-bank/README.md`细路由)

「按任务读哪份文档」的单点在`memory-bank/README.md`的细路由表——本文件不复述,免得两处各自演化。三条动作级提示:

- **改代码前**:读`memory-bank/pitfalls/_index.md`——7类(git·web-ui·backend·testing·ops·kb·docs),按动作选类再进类索引。
- **跑git命令前**:必读`memory-bank/pitfalls/git/_index.md`——ref静默丢弃等本机硬约束单点在里面(同步/推送核验已内联进ship脚本;旧rebase/merge/stash毁库禁令已随拦截层修复解除)。
- **检索纪律**:先索引、后grep、**禁止整读**任一目录;不确定关键词时`grep -rn "<词>" memory-bank/`兜底。

## 会话协议

完整规程(会话开始/收尾DoD 5步/立档阈值4条/任务档案模板)见memory-bank skill(`.agents/skills/memory-bank/SKILL.md`);机械守卫`tests/test_memory_bank.py`。本节只留入口。

- **开始**:①**先同步**(问答/只读轮次跳过;**首个执行动作——改文件/跑测试/任何git写操作——之前必须完成**)——`commands run my-commit-flow.sync`:自动fetch+快进/分叉自动rebase(保线性),成功一行「已同步 <hash>」贴进回复;失败一行含原因与步骤(树脏/冲突已自动回滚),照做后重跑,**禁止在落后分支上改代码**。②看会话滚动状态:`commands run kb.active`列`memory-bank/activeContext/`切片;该读哪份文档走上面的路由。③**只动当前这一个clone**——跨仓库操作**绝对禁止**,须用户显式说「授权」(见「🔴 跨仓库操作」节)。
- **收尾**:按skill的5步DoD——更新activeContext切片(已完成条目**迁出**到progress)/达阈值则立档+`commands run kb.index`重建索引/代码事实变更回写`memory-bank/`与根README/跑`commands run test.full`并新建基线切片记实测数字(`testing/baselines/`,体例见`testing/baseline.md`口径段)/**新坑按动作写进`pitfalls/<类>/<主题>.md`(补三行头元数据)并重跑`commands run kb.index`**。若这轮踩到**已记的坑**,把该条`复发`+1,并在档案里写一句为什么没命中(路由没到/文件没读/读了没照做)。
- **冲突裁决**:代码 > `memory-bank/` > 根`README.md` > `想法.md`;漂移以代码为准并回写。

## 产出口径

- **计划文档**:用`delivery-artifact` skill,放`memory-bank/plans/`;**一律单文件HTML**(出现`.md`即违规)。
- **报告**:审计/故障取证/可行性分析→`memory-bank/reports/`;四工位决策树与`doc-*`协议单点见`memory-bank/conventions/doc-forms.md`。
- **HTML一律dark主题**:深色底+浅色字,样式里写`color-scheme:dark`;配色规格与文件命名见`memory-bank/conventions/webui.md`「HTML 文档一律 dark 主题」。

## 编码约束:非ASCII图形符号

- 代码/配置禁emoji与图形符号→ASCII替代;文档(.md/交付html)可用。见`memory-bank/conventions/code-style.md`

## 黄金法则(来自设计原则,违反即破坏设计)

1. **幂等性**:重复执行不得有副作用;"每天一次"等窗口语义靠state_file去重(`record_execution`),不依赖循环频率。
2. **保守默认**:高风险动作(跳检/强制汇报/删除种子/覆盖限速)默认关闭,只对显式配置范围生效。
3. **状态持久化**:跨轮次状态统一进state_file;优雅退出立即落盘+运行期按state_save_interval周期落盘(配置端下限30s,0=关),非优雅终止丢失窗口≤间隔。
4. **fail-fast**:配置在`config.validate_config`全量校验并聚合报错;之后的代码假定配置正确。**新配置键必须加进validate_config并同步`config/schema.py`**(守卫测试会查)。
5. **单一写线程**:只有主循环线程改任务队列结构与state_file;不引入绕开该假设的并发代码。
6. **范围守恒**:计划外的代码/文档缺陷**一行都不改**——入池`memory-bank/issues/`(命名/8类类型/档位/`_index.md`登记见create-issue skill `.agents/skills/create-issue/SKILL.md`);**入池不为填单做代码分析**。该不该现在修见scope-guard skill `.agents/skills/scope-guard/SKILL.md`。
7. **请求边界**:开工先判这一轮是**问答/只读**还是**执行任务**——只是问就**只在回复里作答**,不得入池issue/立档/出计划/改文件/commit push;想延伸排查先问。只有执行任务才适用上面的收尾DoD与立档阈值。
   - **"继续/continue/接着做/你看着办"不构成授权**——只表示"把你手上这一步做完"。四类动作必须**逐项**显式确认:①新建文件②入池issue③认领issue④commit/push。
   - 反面案例见`memory-bank/pitfalls/kb/request-boundary.md`。

## 红线(生产文件,禁止改动/提交)

- **`config.yml`**:用户真实生产配置(真实PT域名/tracker规则/qB凭据引用),不是示例!示例用`minimal.yml`/`test_yamls/`。
- **`auto-qb-data/`**:运行时数据(state.json/锁/日志/跳检备份),已gitignore;不要"顺手"格式化或重排。
- 明细见`memory-bank/pitfalls/ops/prod-files.md`。

## 命令

**想跑测试/格式化/提交/推送/包内脚本第一步是找task id,不是拼裸命令**——等价物裸跑(`uv run pytest`/`git push`…)会丢掉包里单点定义的环境陷阱。`commands run <task>`的`<task>`是包里的一条命令(映射表在`.commands/`各包的`config.toml`,引擎是commands skill `.agents/skills/commands/SKILL.md`)。**先直接试跑**,报command not found才装一次wrapper(幂等,生成物已gitignore):`uv run python .agents/skills/commands/scripts/install_wrapper.py`(落仓库根+PATH目录,PATH那份跨clone共享,多数会话免装);没装时也可展开`uv run python .agents/skills/commands/scripts/run.py run <task>`。`<task>`用`list`里的id(子包可写`ship.commit`,也可写全`包/子包.<task>`);不知道调哪个就`list`(一次平铺全部包与命令,无需下钻)。遇到**反复要跑/难拼/有陷阱写法**的命令,按SKILL.md的收录协议自己`add`进包——命令集靠这个长大,不是靠人维护。

```text
commands run test.full # 全量测试(最新基线:commands run kb.baseline列最近3条;排障 --all)
commands run test.quick # 快速迭代,跳过覆盖率报表
commands run dev.run -- config.yml --dry-run # 真机跑主程序(需真实qB;一律先 --dry-run)
commands run dev.fmt -- <改过的 .py> # 格式化(.style.yapf:facebook,列宽120)
commands run env.sync # 首次/依赖变更后同步依赖
```

- 依赖统一走`uv`(`pyproject.toml`+`uv.lock`)。
- ⚠`TMPDIR`已内置在`test.*`里,**别再手工加前缀**(会盖掉包里正确的值);判据见`memory-bank/pitfalls/testing/tmpdir.md`。
- 新增测试必须同步该文件头部docstring的"## 测试计划"清单。

## ⚠环境硬约束:Git操作(AI工具shell特有)

**工作区模式:多clone并行**:每个AI实例用**一份独立克隆**,跨clone同步一律走Gitee `develop`。细则见`memory-bank/conventions/collaboration.md`「协作约定」;完整判据与事故档案单点在`memory-bank/pitfalls/git/_index.md`。本节只留最容易致命的几条:

- **rebase/merge/stash禁令已解除**:历史上删除拦截层会在这几类操作写入`.git`时批量删对象(3次事故),已修复、恢复可用——高风险历史整合前仍建议先`cp -a .git <备份>`。落后/分叉一律`commands run my-commit-flow.sync`(自动快进/rebase保线性;树脏会给失败行,行内自带stash解锁配方)。
- **ref三处核对与推送核验已内联进ship脚本**:`HEAD`==`refs/heads/<branch>`==loose/packed、推完`ls-remote`现查远端真值,全部由`ship.commit`/`ship.push`/`my-commit-flow.sync`自动做——**不要手工核验**;不一致/「无法核实」会出现在失败行里,排障用`commands run my-commit-flow.verify-ref`。(本shell里`refs/remotes/*`写入被静默丢弃、`git push --dry-run`永远"成功",都不可信——详单点`memory-bank/pitfalls/git/refs.md`。)
- 机检与停手点一律走**task id**:`commands run ship.commit`/`ship.push`/`my-commit-flow.sync`/`my-commit-flow.verify-ref`(排障)(`list my-commit-flow/ship`看全流程,`show <task>`看展开的命令与深读指针)。**包内README与`references/`只在排障/迁移时读**——日常整读它,等于把"读整份文档找命令"的成本又搬回来。

## 🔴 跨仓库操作:绝对禁止(需显式强授权)

完整定义(含事故实证与止损纪律)见`memory-bank/conventions/collaboration.md`「🔴 跨仓库操作」节;本节只留红线。

- **除当前工作clone外,对其它clone的任何写操作一律绝对禁止**——改文件/`git apply`/复制覆盖/跑git命令。
- **授权指令只认`授权`**,须用户**显式**说出;**「提交」不算**——它只授权commit+push到远端。
- 未授权时**停下来问**:发现"改动在别的clone上不生效"应报告交由用户决定,**不能自己动手**。
- **跨工作区同步一律走Gitee `develop`**,没有第二种路径。

## 提交/PR

**步骤与机检一律走task id**(不是文档):收到"提交"→①收尾回写文档(DoD)→②消息写进`.git/COMMIT_MSG_AI.txt`(提交后脚本自动删除)后`commands run ship.commit`:闸门+暂存+提交+内部同步(**提交先行**——树净rebase恒可自动,stash舞蹈自提交路径退役)+核ref+推Gitee全自动;同步冲突/断网才需agent介入(失败行自带下一步),成功一行「提交成功 <hash>」,推送未完成不改退出码(补`ship.push`)。独立`my-commit-flow.sync`只剩会话开工用途。**本节只留口径**;原理与完整判据在包内`references/pipeline.md`(排障才读)。

- **协作主线**:日常在`develop`,以**Gitee的`develop`**为准;**交付与否只看Gitee**。GitHub只作镜像、**允许滞后**——别用GitHub状态判断进度。
- **用户说"提交"=commit+push**,一次走完;**触发词只认"提交/入库/推上去"这类显式指令**,"继续/接着做/ok/你看着办"一律不算。**本条是提交口径的单点定义**,优先于`memory-bank/`里的历史表述。
- **推送顺序固定**:先推Gitee(必须成功)→核远端ref==本地→再**尝试一次**GitHub镜像——**全程静默**(允许滞后,成败都不提;不重试/不换代理/不改走SSH/不回滚Gitee已完成的推送)。
- **提交信息=gitmoji+中文**:首行`<gitmoji> <中文一句话概述>`,空一行后写动机/取舍/影响面/实测数字;小改只写首行。**数字必须是提交那一刻实测的**。选哪个emoji走gitmoji skill `.agents/skills/gitmoji/SKILL.md`。
- **回写合流交脚本**:收尾回写直接写在本地基线上,与远端的合流由`ship.commit`提交后rebase完成——各`_index`撞车由生成物自动化解兜底(取一侧+重跑生成器+自证),手写件冲突才停下要人;回写文件仍**随主提交一并暂存**,不推完再补一笔(已推送的提交不能amend+强推)。
- **红线与闸门清单外置在`.commands/my-commit-flow/.my-commit-flow.toml`**(包脚本强制读取,缺了就停手引导生成)。
