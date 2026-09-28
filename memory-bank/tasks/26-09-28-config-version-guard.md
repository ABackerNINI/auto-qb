# 26-09-28-config-version-guard — 配置版本升级守卫: 键面基线冻结快照

**Status:** Done
**Added:** 2026-09-28
**Updated:** 2026-09-28
**Summary:** 按计划 [26-09-28-1834-plan-config-version-guard](../plans/26-09-28-1834-plan-config-version-guard.html) 落地: 键面基线守卫测试三条(键面比对按消失/新增/版本已抬三现场分流报错 + 迁移链完整性静态断言 + 参考文档出处钩) + 冻结基线 170 键(`tests/fixtures/config_key_surface.txt`) + 再生命令 `test.keys-update` 收录; keys.md 补 `fs` 行(守卫暴露的既有漂移)与 `hr` 键反引号化。test.full 1823 passed / 3 skipped / TOTAL 91%(基线切片 26-09-28-1855), 改动未提交待用户指令。
**Topics:** config-version-guard
**Refs:** memory-bank/plans/26-09-28-1834-plan-config-version-guard.html

## 原始请求

用户 2026-09-28:「上一次agent修改了config中的字段而没走现有的版本升级流程, 添加配置版本升级守卫, 先给一个思路」→ 思路确认后:「计划入档, 按推荐实施」(推荐范围 = 核心层键面基线 + keys.md 同步钩; commit 闸门按推荐不做)。

## 思考过程与决策

- **缺口定性**: 现有四道防线(版本链框架 / 写回版本闸门 / 启动物化 / schema↔validation 互检)全部以「流程被正确走」为前提; schema 与 validation 一起改时互检恒绿, 没有任何一环在开发期拦「改键不抬版本」。运行时补不了这道岗(没有登记的版本差就没有迁移可做), 必须在开发期立冻结参照物。
- **第三份冻结副本**: 基线独立于 schema 与 validation 两边, 是它能在两边一起改时报警的全部理由; 基线是生成物禁止手改, 「更新基线」因此是显式动作。
- **键面口径**: 顶层键来自 `KNOWN_CONFIG_KEYS`(剔除版本章 `schema_version`); 具名子树走 schema Field 树递归; 动态段归一通配(站点/规则集/规则名/档案 id/path_map 条目); `fs.path_map` 条目键有 `KNOWN_PATH_MAP_ENTRY_KEYS` 常量可派生; 曲线段内部键是校验器内联字面量, v1 不入面(边界写进计划 §4)。
- **不自动裁决破坏/非破坏**: 机器判不了语义, 用报错文案分流路由(消失键 → 抬版本+迁移注册+回归测试参照 test_hr_config.py; 纯新增 → 重生成基线), 文案指路 versioning.py 口径段 / 计划 26-09-26-0506 / pitfalls/backend/schema-stamp-writeback.md。
- **commit 闸门不做**: staged 检查误报面大(b68e9a0 加 tone 属性即合法不抬号), 键面级判定只有跑 Python 才准而 test.full 必跑守卫, commit 层只剩软提醒价值。
- **生成器单点放测试模块**: 再生脚本 import 测试模块取生成器, 不复制第二份展开逻辑。

## 实现计划

1. `tests/test_config_key_surface.py`: 生成器(单点) + 三条用例(键面比对分流 / 迁移链完整性静态断言 / keys.md 叶键出处) + 测试计划 docstring。
2. `tests/fixtures/config_key_surface.txt`: 基线(生成物; version 行 + 排序键路径)。
3. `scripts/update_config_key_surface.py`: 再生脚本(加载测试模块生成器重写基线 + 增删摘要)。
4. `.commands/test/config.toml` 追加 `test.keys-update`(收录协议: 难拼 + 会重复)。
5. keys.md 仅当同步钩暴露缺口时补; 收尾 DoD(test.full 基线切片 / activeContext / kb.index)。

## 子任务状态表

| 子任务 | 状态 | 说明 |
|---|---|---|
| 计划档 + 任务档案 | Completed | plans/26-09-28-1834-plan-config-version-guard.html + 本档案(已转 Done) |
| 守卫测试 + 基线 + 再生脚本 | Completed | 三条用例 + 基线 170 键 + 突变自检(删键→红→还原)通过 |
| test.keys-update 收录 | Completed | test 包 add --write, 幂等试跑通过 |
| keys.md 补缺口 | Completed | fs 行 + hr 键反引号化 + 规则段插件指针; 插件 spec 内部键豁免(docstring 记录口径) |
| 收尾 DoD | Completed | test.full 1823 passed/3 skipped/91%(切片 26-09-28-1855) + progress 条目 + kb.index; activeContext 切片建立后又移除 —— 切片池 57 超 56 上限且 0 个超期可蒸馏, 本专题已完成且细节全在 tasks/progress/基线切片, 按「已完成条目迁出后切片消解」处置 |

## 进度日志

- **2026-09-28 18:34**: 开工 sync 已同步 b68e9a0e; 计划档落盘(拍板后冻结), 本档案建立。
- **2026-09-28 18:52**: 守卫测试 + 基线 + 再生脚本落地, 三条用例绿; 突变自检通过(临时删基线一行键, 守卫报红且分流文案正确, 还原后全绿)。
- **2026-09-28 18:58**: 实施发现两处计划外现场, 均按最小处置: ①**keys.md `fs` 行整行缺失**(d50fa12 引入的既有文档漂移, 守卫出处钩当场暴露) —— 补最短行 + `hr` 行输出键反引号化; ②**keys.md 距 12,000 cap 仅 ~200 字符余量**, 插件清单外迁其委托正主 `rule-system/conditions-and-actions.md`(实施验证合并语料零缺口), 守卫语料跟随委托关系; **插件 spec 内部键**(插件名之下层级)整个参考文档体系无逐键覆盖, 暂豁免出处检查并在 docstring 记录 —— 是否逐键展开待用户拍板(可入池 issue)。
- **2026-09-28 19:00**: `test.keys-update` 收录 test 包并试跑(幂等, 键面无变化行)。test.full 三跑: 首跑 8 失败全是 kb 索引生成物未重建(重跑 kb.index 解决), 二跑剩 `test_run_loop_throttles_without_stop_event` 一次计时抖动(单跑即绿, 与本批无接触面), 末跑全绿 **1823 passed / 3 skipped / TOTAL 91%**。改动未提交 —— 待用户显式说「提交」。
- **2026-09-28 19:08**: activeContext 切片建立后触发 `test_kb_active_context_slices_are_valid`(池 57 > 56, 且 kb.active 报 0 个超 14 天可蒸馏对象) —— 本专题已完成且执行数字已沉淀(tasks/progress/基线切片), 移除切片后全量复绿。
- **2026-09-28 19:20**: 收到「提交」后 sync 遇分叉+脏树 —— stash → sync 快进 74c733cf(远端三笔: HR 排除功能/测试去重/throttle 计时余量) → stash pop 仅 keys.md 真冲突(远端 hr 行加排除表键 vs 本地反引号化, 合并两者) → **守卫首战告捷**: 拦住远端并入的 4 个新键(`hr.exclude_tags`/`hr.exclude_categories` 及 trackers 级), 正确分流「纯新增=非破坏」→ `test.keys-update` 重生成基线 170→174。keys.md 合并后 12,111 超 cap 111 字符 —— 处置: 删冗余插件指针句 + 压缩 fs 行 + hr_check 行尾「站点接入」去重(事实在 trackers 段旧键行与 hr_check.sites 专节均有载), 回到 12,000 内。合并基线 test.full **1831 passed / 3 skipped / TOTAL 91%**(12576 语句 / 920 未覆盖 / 4246 分支 / 392 partial, 21.2s)。
