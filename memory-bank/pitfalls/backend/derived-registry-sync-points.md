# 派生登记的重算挂点必须数清全部写入路径 —— 只挂漏斗, 绕开漏斗的落账单点会滞后一拍

> 摘要: 给 store 加新的派生登记(relocating/resuming 这类纯内存并集)时, 重算挂点若只选在「job 变更的重算漏斗」(_set_job → _sync_relocating), 而账面存在**刻意不走漏斗**的落账单点(_note_resume_state/_note_tag_state 同款: 终态 job 的账面变更不该触发标签镜像重入/反复后移 updated_at), 挂账瞬间登记不更新 ⇒ 消费方(fuse 让路/拦截)窗口错位一拍; 重算必须双挂点: 漏斗末尾兜底 + 绕道落账点直呼, 两点共享同一个全量重算实现。
> 触发: 新增 store 登记, 派生登记, 重算挂点, 漏斗, _set_job, _sync_relocating, _note_resume_state, _note_tag_state, 不走 _set_job, 登记滞后, 让路窗口, resume_pending, resuming_hashes, relocating_hashes
**Refs:** memory-bank/tasks/26-11-15-backend-relocate-resume-confirm.md

### 「重算挂进漏斗一处就全覆盖」在存在绕道写入路径时不成立

- **触发**: 给 RelocateModule(或同构模块)新增派生登记(issue 26-11-15-0441: fuse 让路从 relocating 收窄为 resuming 账窗口, 新登记 `store.resuming_hashes`)。自然写法是把重算挂进 `_sync_relocating` 末尾——它是 job 变更的重算漏斗(`_set_job`/`_load_jobs`/新建 job 都经此), 看似全覆盖; 但 resume 账的落账单点 `_note_resume_state` **刻意不走 `_set_job`**(终态 job 的挂账/清账不该触发标签镜像重入, 也不该反复后移 updated_at), 于是「开账 → 消费方下一拍读登记」之间登记还是空的: fuse 让路窗口错位一拍, 恢复初期回声拉流被计连击; 反向(账闭合不撤登记)同理滞后。
- **判别**: ① 列出登记所依据的账面字段的**全部写入路径**(grep 谁写: `resume_pending` 运行期落账只有 `_note_resume_state` 写; `from_dict` 启动恢复也写该字段, 但经 `_load_jobs` 走漏斗); ② 对每条路径问一句「这条走漏斗吗?」—— 不走的必须直呼重算; ③ 测试判据写成「账面变更**当拍**登记即变」(不 sleep、不等下一轮/下一次 job 变更), 滞后一拍的实现立刻转红。
- **处置**: 双挂点, 共享同一实现: ① 漏斗末尾兜底(`_sync_relocating` → `_sync_resuming()`, 覆盖 job 变更/启动加载/热启用, 终态挂账 job 也进登记——登记口径若按账扫全部 job 就**不要**沿用漏斗里 active_jobs 的过滤); ② 绕道落账单点直呼(`_note_resume_state` 落账后即 `_sync_resuming()`, 开账/闭合/穷尽收敛三个账面变化即时落地)。重算写成无参全量重建(clear + 按账面并集重填), 双挂点零增量逻辑, 不给两套实现漂移的机会; 老 store 替身缺字段时自建一份, 不打扰既有测试形状。
- **守阵**: `tests/test_relocate_resume_confirm.py`(账面变更当拍断言: 即时重算不滞后/终态+穷尽保留/启动重建) · `tests/test_fuse_mod.py`(全链 restreak/即时重算)。
- **复发**: 0

### 现状: 触发面(两张登记集的重算挂点)已随 relocate S5-1 结构性退役 —— 登记改派生查询, 无挂点可漏

- **触发**: 给 relocate 这类「登记集 + 重算挂点」排查登记滞后/让路窗口错位一类问题前, 先看本条现状 —— 本坑的原始触发面(store.relocating_hashes / store.resuming_hashes 两张登记集的全部重算挂点)已随 relocate 重构 S5-1(a652290f, 计划 26-11-15-2340 第二批)**整体退役**: 登记不再由挂点维护, 改为 `RelocateModule` 公开派生查询 `relocating_hashes()` / `resuming_hashes()` / `alias_roots()`(按账面现算, **派生即最新, 无挂点可漏**); 跨模块消费面迁 ctx 句柄(qbapi 经构造注入)。
- **判别**: 旧形态是否残留由守阵机械承考 —— `tests/test_relocate_interface_guard.py` P3 判据钉「三登记名直读」(出现即红), grep 无跨层私有引用由同守卫四判据承考(真仓 198 文件)。
- **处置**: 上文触发/判别/处置为历史记录, 保留不改写; 同构「派生视图 + 挂点同步」写法在别处仍会复发本坑 —— 新增派生账优先做**现算查询**(零挂点), 确需缓存登记才回到本文判别法。
