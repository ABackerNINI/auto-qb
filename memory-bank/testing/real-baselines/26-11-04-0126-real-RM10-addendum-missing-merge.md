# RM10 附加轮(导出面): 缺失站点导出合并 4/4 全绿 —— CLI --export-yaml 共现合并/--split-trackers/幂等首验, 零产品缺陷

> 摘要: RM10 附加轮(计划 plans/26-11-04-0115-plan-real-rm10-addendum-missing-merge.html), 被测面 = 缺失站点导出/导入 tracker 合并功能(功能计划 plans/26-11-03-2337 M1/M2, 7 提交 948e11a1..086044b9 已入库)。**重立基线轮**(旧 5b795217 clone5 lineage 解析不到)。新建 4 条(RM10-11~14, 落 tests-real/rm10_notify/test_rm10_export_merge.py, 与既有 RM10 片共享 conftest 串行锁): ① only_missing 合并正向(共现 union-find 3 元素组 + 代表=最短域名派生键 + dry-run 零写)② 追加模式合并(既有条目原样保留)③ --split-trackers 配合校验红验 + split/合并键面对照(**新建即 L3**)④ 双跑幂等(两模式逐字节一致)。三态 **4/0/0**; **零产品缺陷入池**。造法关键: announce 用互异 127.x IP 字面量+死端口(`_hosts_of` 取 `urlparse().hostname` **不含端口**, 同 IP 异端口会塌缩成一个域——同 IP 异端口方案不可行, 实测前已避开); 导出配置指**副实例空凭据**(bypass_local_auth), token 零落盘。
> 基线时间: 2026-11-04 01:26-01:27(官方合跑 = 4 条一次串行, 29.78s; 另 4 条单跑预验证 01:23-01:24 各 6.7-8.9s 全绿)
> 基线 commit: `b01609ca`(官方合跑时刻 HEAD; 旧基线 5b795217 为 clone5 旧 lineage 现分支解析不到, 按「写不出 commit 从首轮重来」口径重立; 非收尾提交 hash)

## 01 验收数字

`uv run pytest tests-real/rm10_notify/test_rm10_export_merge.py -q --no-cov -p no:cacheprovider -n 0`(2026-11-04 01:26, 环境2, 与 real.run 同款命令形态; 4 条单跑预验证逐条 PASS 后官方合跑):

```text
4 passed in 29.78s
```

- 产品缺陷 0 个; FAIL 0; BLOCKED 0。
- 档位分布 **L0/L1/L2/L3 = 0/0/3/1**(L2×3: 11/12/14, L3×1: 13 新建即档)。
- 升档核验(计划 §04.2): 本轮 4 条纯新增(功能新面), 其中 RM10-13 新建即 L3 —— 红验真跑: ①缺 --export-yaml → rc!=0 + stderr 逐字文案「--split-trackers 需配合 --export-yaml 使用」; ②split 产物出现 ≥2 设计域条目即红(拆分语义失守门)+ 故意错位期望(bogus 域)红验自证真红。满足「每轮至少 1 条升一档」硬要求。

逐条结果(档位按计划 §04):

| 用例 | 内容 | 档位 | 结果 |
|---|---|---|---|
| RM10-11 | only_missing 合并正向 + dry-run 零写: 3 枚 paused 假种子(A=[127.0.0.7,127.0.0.12] / B=[127.0.0.12,127.0.0.13] / C=[127.0.0.14])→ 合并条目 domains==[127.0.0.12, 127.0.0.13, 127.0.0.7] (跨种子传递闭包)、键==`127_0_0_7`(代表=最短 9<10)、tags==[""](IP 形态空标签, 已知正确行为)+ hr 示例段逐字; 单元素条目 `127_0_0_14`; 设计域各恰一条目; 骨架只含 trackers+schema_version、无已配域; dry-run 轮「已导出」日志在而输出文件不存在 | L2 | PASS |
| RM10-12 | 追加模式: rm10em_invalid 条目原样保留(domains/tags 逐字)+ data_dir 等原始段回显 + 合并/单元素条目追加 + 定界断言 | L2 | PASS |
| RM10-13 | ①配合校验红验(rc!=0 + parser.error 逐字文案)②split 键面==恰 4 个逐域名派生名、每域恰一条目、零 ≥2 元素条目 ③对照: 合并面含 3 元素组且 127.0.0.12 无专属条目 / split 面有; bogus 期望红验自证 | **L3**(新建即档) | PASS |
| RM10-14 | 双跑幂等: only_missing 与追加两模式各连跑两次, 输出逐字节一致 | L2 | PASS |

**三态: PASS 4 / FAIL 0 / BLOCKED 0。**

**零外连红线**: 全程成立。announce 全部 `http://127.0.0.x:1/announce`(IP 字面量零 DNS + 死端口); 种子全程 paused(stopped*)不 announce; 实例内真实种子 0 枚; real-fake 收尾删净; guard 复跑绿。

## 02 环境指纹

| 项 | 值 |
|---|---|
| 环境 | 环境2(C盘机), `QBT_REAL_ENV=2` 显式指定; token 经环境变量注入(QBT_TEST_56589/56590), 全程零落盘(用例/配置/切片零 token 字面值, grep 实测) |
| 实例版本 | qBittorrent v5.2.3(两实例同 build) |
| 56589(主) | pid 8228(开工=收尾一致, 零重启), firewalled, 真实种子 **0 个**; 本轮零触碰(出口实测 0) |
| 56590(副) | pid 7596(开工=收尾一致, 零重启), firewalled; 导出配置指向它(空凭据直连); 收尾 real-fake 残留 0、种子 0 |
| bypass_local_auth | True(环境2 标准配置, 56590, 本轮未触碰) |
| 产品解释器 | `.venv` → CPython 3.13.15(uv 管理); CLI 短命进程(run_cli) |
| 产品配置 | 每条用例派生独立配置落 `.work/rm10/<case>/config.yml`; schema_version: 5; 指 56590 空凭据(**不写 api_key**, D2 拍板); trackers 段配 `rm10em_invalid: domains ["rm10em.invalid"]`(与 announce 域零命中) |
| 落点 | 假种子数据只落 `tests-real/.work/rm10/rm10_1x/seeds/`(KB 级 3 枚/场 ×4 场); real-fake 标签收尾删净; `.work` 全清(real.seed.clean 实测「已清空」) |
| 收尾进程口径 | CLI 短命进程自退; `.work` 全清; 进程比对恰开工两枚(8228/7596) |

## 03 本轮实测确认的代码事实(回写素材)

1. **`extract_tracker_hostnames` 的域名不含端口**(`_hosts_of` → `urlparse(url).hostname`, src/auto_qb/infra/utils.py:113): 同一 IP 不同端口的多个 announce 会**塌缩成一个域名** —— 「IP+异端口造互异域」不可行, 互异域必须用互异 host。IP 字面量(127.0.0.x)形态: `gen_default_tag` 返回空串(parts[-2] isdigit 分支, exporter.py:72)、`gen_tracker_name` 把点换下划线(`127.0.0.7` → `127_0_0_7`)—— 两者实测与单测口径一致。
2. **qB 5.2.3 `/torrents/addTrackers` 参数名是 `hash`(单数)**: 传 `hashes` 得 400「缺少必需参数：hash」(实测); urls 换行分隔可用, 对 stopped 种子照常生效 —— 造多 tracker 假种子不必动 lib/qb.py, 用例侧 `_call` 直调即可。
3. **合并/拆分/幂等三面在真机首验成立**(官方合跑一轮即绿): 共现 union-find 跨种子传递闭包(A∩B 经 127.0.0.12 传递)真机可观测; 代表=组内最短(9<10)派生键; split 恢复逐域名; 双跑逐字节稳定。exporter.py 真机面零缺陷。
4. **--split-trackers 配合校验报错文案逐字**: 「--split-trackers 需配合 --export-yaml 使用」(cli.py parser.error), 缺 --export-yaml 时 rc!=0 —— 与 --only-missing 同款配合校验形态。

## 04 排障与复跑记录

| 轮次 | 内容 | 结论 |
|---|---|---|
| 首跑 RM10-11 | addTrackers 400「缺少必需参数：hash」 | **测试侧造法缺陷**(qB 参数名单数), 修用例复跑绿, 产品零改动 |
| 次跑 RM10-11 | 开跑断言「有 real-fake 残留」红(上轮失败点在 build_scene 内, 测试体 finally 够不到) | **测试侧健壮性缺陷**, build_scene 改「先清场 + 失败自清」(各片自清幂等口径), 复跑绿 |
| 官方轮 01:26 | `4 passed in 29.78s` | 一轮即绿, 零 FAIL 零假红; 用例代码官方轮前定稿, 官方轮后零改动 |

## 05 遗留与解锁条件

- WEBUI 导入三钮自适应引导(M3/M4 端到端观感): L0 目视挂账(与 RM08 D3 横滚条同批, 归用户下次目视清单); 后端 groups 字段与前端接线已由单测(26-11-04-0035 切片)钉住。
- 跨站种子错焊场景(转载/合种携带多站 tracker): 产品有 --split-trackers 兜底(本轮 ③ 已验), 错焊形态的共现闭包真机面未单独立例(单测覆盖 group_missing_domains 传递闭包); 真实撞上按功能计划 §07 用 --split-trackers 兜底。
- RM10 既有 8 条(RM10-01~08): 本轮附加面不重跑(导出面新增, 既有面零漂移 —— 漂移体检 7 提交对 notify/tools/extensions glob 零命中); 下次 RM10 全片轮再作回归。

## 06 基线 commit

本轮为 RM10 **附加轮 + 重立基线轮**(旧基线 5b795217 为 clone5 旧 lineage, 现分支解析不到(bad revision), 按「写不出 commit 从首轮重来」口径重立)。**基线 commit = `b01609ca`**(官方合跑时刻的 HEAD; 收尾提交只含切片/锚件/用例, 不含产品代码)。下次漂移体检用它做
`git log b01609ca..HEAD -- src/auto_qb/core/modules/notify_mod.py src/auto_qb/infra/notify.py src/auto_qb/core/exporter.py "src/auto_qb/tools/**" "extensions/**"(除 hr-fetch-proxy)`(glob 以锚件 §03 RM10 行现值为准)。

## 07 记账与结论

- **glob 自检**(§05 规则 8): RM10 行 5 条 glob 全核 —— notify_mod/notify/exporter 各 1 命中、tools/** 2、extensions(除 hr-fetch-proxy)0(维持 26-10-31 记账); 片边界不糊, 不拆不并。**cli.py 覆盖核查**: `src/auto_qb/cli.py` 已被 RM01 行 glob 覆盖(锚件 §03 RM01 行第 1 条), 按 §05 规则 1 归属优先**无需提名并入 RM10**(本轮 cli.py +9/-1 的 flag/配合校验改动由 RM10-13① 真机红验覆盖, 片归属记账不变)。
- **漂移体检**(§07): 重立基线轮, 漂移面 = 功能 7 提交(948e11a1..086044b9)对 RM10 glob 唯一命中 `exporter.py`(+79/-10, **判据变** = 本轮被测面本身); cli.py(+9/-1 → RM01 glob)、sites.py(RM08 glob)、static/*.js(RM09 glob)各归其片。
- **测试侧改动清单**(产品 src/ 零改动): 新增 tests-real/rm10_notify/test_rm10_export_merge.py(4 条); pytest.ini testpaths 未动; RM10 既有用例零改动。
- **收尾核净**: 两实例种子 0 / real-fake 残留 0(real.seed.rm --all 命中 0 + clean 实测「已清空」); guard 复跑绿(双 firewalled); 进程比对恰开工两枚(56589=8228 / 56590=7596, 零重启); token 零落盘(repo 全仓 grep 两条 token 字面值零命中)。
