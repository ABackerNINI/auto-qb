# 种子转移功能真机验收: 后端管线 12 项 + UI 面 9 项, 1 产品缺陷(409 已存在误判失败) + 2 改进入池候选; 组支 BLOCKED(无分组环境)

> 摘要: 计划 26-10-31-0306(种子转移到其它下载器)W4 真机验收: 双测试实例(36595 主 qB(api_key 鉴权) → 36596 目标(本机免鉴权)), API 面驱动 `/api/transfer/test`·`/api/transfer/run` 全参数矩阵 + 浏览器 GUI 黑盒走 UI 全流程(设置卡编辑器/四段式确认弹窗/右键四支/三态结算反馈/空目标态)。
> 基线时间: 2026-11-01 02:10–02:45(手工驱动, 非 real.suite —— 本验收是功能 W4 验收而非 RM 切片, 用例为一次性驱动脚本, 落 .work/transfer-accept/(已随 real.seed.clean 清除), 断言口径与复现步骤全部誊入本切片)
> 基线 commit: b439bb32(实测时刻 HEAD)
> 环境: 36595 v5.2.3 connected(8 真实种子全程 paused 零触碰) / 36596 v5.2.3 firewalled(空库) / 产品进程 tests-real/.work/transfer-accept/config.yml 派生(grouping 关/无规则/notify 关, web :39000 skip_local_verify); instances.local.json 新建(36595 token, 已 gitignore)

## 01 验收数字

**API 面 12 项(驱动脚本逐项断言, 全部走真双实例):**

| 用例 | 内容 | 结果 |
|---|---|---|
| TR-01a | `/api/transfer/test` 好→`status=ok, info="qBittorrent v5.2.3"`; 坏凭据目标→error「登录失败(检查用户名/密码)」; tr stub→error「暂未实现: Transmission 目标暂不支持转移」 | PASS×3 |
| TR-02 | 单选转移+字段落位: category/tags/up_limit(131072)/dl_limit(262144, 5.2 字段名 dl_limit)/ratio_limit(2.5)/seeding_time_limit(3600)/save_path 原样, 目标 state=stoppedUP progress=1; **源任务删除+数据文件原在**(deleteFiles=false 不变量) | PASS |
| TR-03 | 多选批量 2 颗同批全成功, 逐项回执 | PASS |
| TR-04 | keep_source=true → 成功且源保留 | PASS |
| TR-06 | 认证失败注入(目标 36595+错密码) → 该项「失败」不中断批次, 源保留 | PASS |
| TR-05 | 已存在注入(目标预置同 infohash) → 期望「跳过」**实测「失败」**—— **产品缺陷**(见 §03-1), 源保留不变量未破 | **FAIL** |
| TR-07 | 下载管线态(stalledDL) → 「跳过」, 源保留 | PASS |
| TR-08 | 未完成(stoppedDL, progress 0)+目标跳检开 → 自动降级校验添加, 注明「未完成, 已自动改为校验添加」, 目标落 0% 非跳检; 源删除 | PASS |
| TR-09 | 路径映射(反斜杠精确匹配+junction 别名落点) → 目标 save_path==别名且数据可达; 正斜杠 `from` **静默不命中**(见 §03-2) | PASS* |
| TR-11 | 负向: 空 hashes→400「未提供任何 hash」; 未知 target→400「转移目标不存在」 | PASS×2 |
| TR-热重载 | PUT /api/config 改 web.transfer.path_map → applied/changes=["web"]/无 restart_required, 下一跑兑现 | PASS |

**UI 面 9 项(浏览器 GUI 黑盒; 证据=当轮 DOM 快照/页面内文原文, 按口径不留截图, 文字已誊入各行):**

| 用例 | 内容 | 结果 |
|---|---|---|
| UI-01 | 种子列表渲染(4 假种子+8 真实种子 paused, dark 主题无异常) | PASS |
| UI-02 | 设置卡「种子转移」: 4 目标列出; 测试连接三态(成功绿「qBittorrent v5.2.3」/坏凭据红「登录失败(检查用户名/密码)」/tr stub「暂未实现」); 编辑器字段全落位(密码掩码「已设置, 留空 = 不修改」/保存路径锁死必开 disabled/超级做种默认关/转移后状态单选/映射规则表) | PASS |
| UI-03 | 单种子支右键→「转移到」submenu(4 目标)→四段式确认弹窗(语义说明/目标/数量/转移字段/路径映射预览「未配置映射, 原样转移」/跳检警示/「仅本次保留源种子」默认不勾)→执行→**成功 toast「成功 1, 跳过 0, 失败 0(源任务已删除, 数据文件未动)」**+行消失; 后端回读目标 36596 落位 | PASS |
| UI-04 | 失败注入(tr-dup 已存在): toast「失败 1; 目标添加请求失败(Conflict); 源已保留」+行内 error 图标+源保留 | PASS |
| UI-05 | 预检拦截(tr-nodata stalledDL): 弹窗不开, toast「没有可转移的种子: 1 个全部被预检排除(下载管线态 (stalledDL), 不可转移)」—— 前端预检与后端状态门同口径 | PASS |
| UI-06a | 多选支(ctrl 点选 2 颗)右键菜单含「转移到」 | PASS |
| UI-06b | 整集整剧支(追剧视图剧集行, 2 集合)菜单含「转移到」(只验存在未执行, 真实种子不转移) | PASS |
| UI-06c | 单组支: **BLOCKED** —— grouping.enabled=false 无组可右键; 解锁条件: 开分组+trackers 域名配置造组(RM04 口径)后补验「选中集优先/否则整组成员」两分支 | BLOCKED |
| UI-07 | 空目标态: 全目标禁用热重载后 submenu 灰项「未配置目标, 去设置」 | PASS |

**三态合计: PASS 20 / FAIL 1(TR-05, 产品缺陷) / BLOCKED 1(UI-06c 环境性)。**

## 02 不变量核验(计划 §01 设计底线逐条)

| 底线 | 实测 |
|---|---|
| 数据文件永不移动/删除 | TR-02/03/04/08/09 转移成功后源数据文件逐一核在; 成功 toast 文案明示「数据文件未动」 |
| 不成功路径不碰源 | TR-05/06/07 源任务全部保留(回执+qB 侧双核) |
| 未完成种子绝不跳检添加 | TR-08 降级注明; UI-05 预检拦截; 目标侧 progress 0 非 skip 添加 |
| 同机硬约束 | 目标=同机 36596, save_path 原样/映射别名均数据可达 |
| 凭据只从服务端出网 | 目标凭据只在产品配置; 前端编辑器密码掩码(UI-02) |
| 删源只删任务 | TR-02d 显式断言数据文件在 |

## 03 发现(2026-11-01 用户确认已入池)

1. **[bug] 已存在被误判「失败」而非「跳过」** → `memory-bank/issues/26-11-01-0334-bug-torrent-transfer-duplicate-409.html`: qB 5.2 `/torrents/add` 对重复 infohash 回 **409 Conflict 且 body 无已存在文案**(仅 "Conflict"), `adapters/qb.py::_result_from_exception` 只在 409 文案命中 `_DUPLICATE_NEEDLES` 时判 duplicate; 探针查重兜底(`_hash_exists`)只覆盖 Mapping 形态分支, **异常分支没有**。回执「失败: 目标添加请求失败(Conflict); 源已保留」; UI toast/行内图标同口径误报失败。源保留不变量未破, 但与计划 §03 失败分类「已存在→跳过」不符且用户反馈误导。复现: 目标预置同 infohash 种子 → 对其发起转移。**修复锚点**: `_result_from_exception` 的 409 分支加 probe_hash 查重兜底(与 Mapping 分支同款)。
2. **[enhancement] 路径映射无分隔符归一化** → `memory-bank/issues/26-11-01-0334-feat-torrent-transfer-pathmap-sep.html`: `orchestrator.map_save_path` 与前端 `trMapSavePath` 逐位同语义(裸 `startswith`), 配置写正斜杠 `from` 而种子 save_path 是反斜杠(Windows qB 回读形态)→ **静默不命中**, 转移按原样路径落。前端预览与后端一致所以弹窗预览诚实(用户可见未改写), 无数据风险(最坏=目标侧路径不符预期, 数据仍可达)。建议: `from`/save_path 归一化分隔符后再比对(或映射编辑器给「当前无规则命中」实时提示)。复现: path_map from 写 `D:/...` → 转移 → 目标 save_path 未改写。
3. **[enhancement] transfer 目标不支持 api_key 鉴权** → `memory-bank/issues/26-11-01-0335-feat-torrent-transfer-target-apikey.html`: 主 qB 配置有 `api_key`(qB 5.x API Key, Bearer 直连), `_build_client` 只传 username/password —— **纯 token 目标实例(如 36595)无法作为转移目标**(空密码登录 401)。实测顺带确认: 错密码对 36595 稳定落 auth_failed 分类(失败注入通路真实验证)。建议: TransferTargetConfig 加 api_key 字段 + `_build_client` 透传。

## 04 环境与收尾核净

- 守卫: 开工 `real.guard` 全绿(36595 8 真实种子 paused / 36596 0); 收尾复跑全绿, 进程 pid 与开工一致(41868/39300)。
- 造件清理: 假种子 10 颗(36595×6 源 + 36596 转移落位 9 + 预置 1)全部删除; junction×3 先 `os.rmdir` 剪枝再清数据(无穿透); `real.seed.clean` 清 .work 与 R:/qbt-fake; 收尾两实例种子数 8/0 与快照一致。
- 产品配置: tests-real/.work/transfer-accept/config.yml(非仓库根 config.yml, 红线未触); 进程已停; instances.local.json 保留(gitignore, 后续轮复用)。
- 外发: 零(伪种子无 announce 零 tracker; 目标探测全部本机)。
- 证据口径: 截图 12 张当轮已删(用户指令: 截图不入 git 不留证, 证据只使用文字)—— 各 UI 用例关键反馈文案已逐字誊入 §01 对应行(成功 toast「转移结算(目标 test-qb-96): 成功 1, 跳过 0, 失败 0(源任务已删除, 数据文件未动)」/失败 toast「…失败 1; 目标添加请求失败(Conflict); 源已保留」+行内 error 图标/预检 toast「没有可转移的种子: 1 个全部被预检排除(下载管线态 (stalledDL), 不可转移)」/空态灰项「未配置目标, 去设置」/测试连接三态回显原文)。
