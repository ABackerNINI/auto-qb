# 计划 S6 真机验收·探测面(G5 前半): BLOCKED(多 clone 实例冲突)—— 冲突前干净态 hit 裁决与编辑器/证据区渲染已取证 —— 【已复测闭环: 判据①②③④ 全 PASS, 见 26-11-12-0229-real-relocate-bt-backup-retest.md】

> 摘要: 计划 `plans/26-11-11-0259-plan-relocate-bt-backup-scalar-probe.html` §04 S6 的真机
> 探测面验收(环境1 D盘机, commit f09830e6)。走完开工四步(guard/起实例/造种子/webui)后,
> 干净态直探端点拿到 **verdict=hit(hash 自证消歧唯一命中测试便携候选, 压过生产默认
> profile 与另两合格候选)**; 浏览器面取证编辑器挂载/placeholder/证据区渲染与 ambiguous
> 拒回填(D5)。**08:05 起 clone3 的 `s0` 大库轮(`tests-real/.work/s0/inject.py`, 3000 枚
> real-fake)压上同一实例**: 我方种子被对方轮次清除、探测 hash 集被 3000 枚污染(hit 恒不可
> 达, 实测变 ambiguous 双 hash 命中), 且后续 real.down / seed.clean 均会破坏对方现场 ——
> 按「测试实例全机一套, 别的 clone 在测 → 停手报告」纪律 **BLOCKED 停手**。产品缺陷零
> (hit 裁决与 D5 拒猜两形态的真机行为均与 §3.2 表一致); 未完成面 = hit 的 UI 回填→保存
> 落盘(PUT)链、offline 组、收尾清理。产品源码与 memory-bank 其它面零改动。
> 基线时间: 2026-11-11 08:01-08:11
> 基线 commit: f09830e6(分支 relocate-bt-backup-scalar-probe, 本地无远端; 实测全程 HEAD 未动)
**Refs:** memory-bank/plans/26-11-11-0259-plan-relocate-bt-backup-scalar-probe.html · memory-bank/testing/real-machine.md

## 01 三态结论

| 项 | 三态 | 说明 |
|---|---|---|
| 探测面(hit 全链: 按钮→命中→消歧→回填→保存落盘) | **BLOCKED** | 后端裁决(hit/消歧)与前端渲染面已取证(§03/§04); hit 的**回填草稿→actbar 脏态→PUT 落盘**链未走完 —— 08:05 起 clone3 s0 轮压上共享实例, hash 集被污染, 且走完该链需重造种子(踏对方现场)。原因与时间线见 §04 |
| offline 组(real.down 后 200 未自证) | 未执行 | real.down 会关掉对方正在用的实例, 冲突期禁止 |
| 产品缺陷 | **0** | 已取证两形态(hit 裁决 / ambiguous 拒回填)行为与计划 §3.2 表逐字一致 |

## 02 环境指纹

| 项 | 值 |
|---|---|
| commit | f09830e6(`relocate-bt-backup-scalar-probe`, 工作树净) |
| 环境 | 环境1(D盘机), `QBT_REAL_ENV` 未设(按 EXE 探测) |
| 实例 | 主 36595 = `D:\Programs\qBittorrent-testing\qbittorrent.exe` / 副 36596 = `D:\Programs\qBittorrent-testing2\qbittorrent.exe`, 均 qB v5.2.3 |
| 实例状态 | 08:01 guard 全绿(36595 pid=26824 / 36596 pid=38320, 均 firewalled, 真实种子 0); `real.up` → `[skip] 36595 已在监听`; `connection_status=firewalled`(非 disconnected, §2.4 核过) |
| 便携 BT_backup 实测路径 | 主 = `D:\Programs\qBittorrent-testing\profile\qBittorrent\data\BT_backup`(与计划 §2.2 便携口径 `<exeDir>/profile/qBittorrent/data/BT_backup` 一致; 副 = `D:\Programs\qBittorrent-testing2\profile\qBittorrent\data\BT_backup`) |
| 产品 webui | `commands run dev.webui -- --qb-port 36595 --no-open`(08:02 起), WEB 实绑 `http://localhost:6261`(OS 取号); 派生配置 = `H:/Temp/auto-qb-dev-webui/config.yml`(dev_webui 最小配置: interval=86400S 任务线全关 / 规则零段 / grouping 只读归组 missing_tag 空 / web skip_local_verify: true), **qbittorrent.port = "36595"(白名单内, 非生产)**; 启动物化迁移 v1→v8 落盘(派生配置自留 `config.yml.v1.bak`, 仓库根 config.yml 与 auto-qb-data/ 零触碰) |
| 同步确认 | 产品日志「检测到新增种子 1 个」= 我方 L0 假种子可见, webui 后端连的确实是 36595 |
| 收尾足迹 | webui 已停(6261 释放); 派生配置无 `relocate.bt_backup` 键(PUT 一次都未发生); 36595/36596 保持 firewalled 原样留给对方轮次 |

## 03 实测证据(3.1/3.2 = 冲突前干净态 08:01-08:04; 3.3 = 冲突后污染态 08:06-08:07)

### 3.1 种子与 BT_backup 形态(`real.seed` L0 256K)

- `commands run real.seed -- --yes --port 36595 --name real-probe-l0.bin` →
  `[ok] infohash=ae370f1438eed1d5b19d3be5d6584be5c13ac650, state=stalledUP progress=1`(标签 real-fake)。
- 主实例 BT_backup 实测(08:02):
  `ae370f1438eed1d5b19d3be5d6584be5c13ac650.fastresume`(1456 B) + 同名 `.torrent` + `queue`(内容 = 该 40hex 一行) ——
  资格判定两要素(`^40hex\.fastresume$` / `queue`)真机形态与计划 §2.2 取证一致。
- 副实例 BT_backup 当时 = `d6aa292e….fastresume.bak` + `queue`(0 个现行 fastresume, `queue` 单独构成资格)。

### 3.2 探测端点直探(POST /api/relocate/bt_backup_probe, 干净态)—— **hit + hash 消歧唯一命中便携候选**

```json
{
  "verdict": "hit",
  "reason": "4 个候选合格, hash 自证消歧命中唯一: D:\\Programs\\qBittorrent-testing\\profile\\qBittorrent\\data\\BT_backup",
  "online": true, "manual_set": false, "storage_type": "Legacy",
  "candidates": [
    { "hash_matched": false, "fastresume_count": 242, "origin": "default-profile", "path": "C:\\Users\\11059\\AppData\\Local\\qBittorrent\\BT_backup" },
    { "hash_matched": false, "fastresume_count": 290, "origin": "portable",          "path": "D:\\Programs\\qBittorrent-2\\profile\\qBittorrent\\data\\BT_backup" },
    { "hash_matched": true,  "fastresume_count": 1,   "origin": "portable",          "path": "D:\\Programs\\qBittorrent-testing\\profile\\qBittorrent\\data\\BT_backup" },
    { "hash_matched": false, "fastresume_count": 0,   "origin": "portable",          "path": "D:\\Programs\\qBittorrent-testing2\\profile\\qBittorrent\\data\\BT_backup" }
  ]
}
```

> **`storage_type` 线值/渲染括注**: 上摘录是**线值原样** —— `"Legacy"` 为 qB 5.2.3 WebAPI 实发字符串(收尾复核: 绕产品直 GET `36595/api/v2/app/preferences`, `resume_data_storage_type` raw = `'Legacy'`(str), 产品端点原样透传零映射)。probe 侧按 `str().strip().lower()` 容错接受(`_LEGACY_TOKENS` 含 "0"/"legacy"/""), 代码文档口径「整数 0 = Legacy / 1 = SQLite」在 5.2.3 实为字符串 —— 字符串容错分支真机实际走到。编辑器存储行「qB 恢复数据存储: Legacy」(§3.3)是前端 `bbStorageText()` 渲染映射("0"/"legacy" → "Legacy"), 与线值同形、非同层。

**这就是 hash 消歧正确性的真机证据**(任务核心判据): 4 候选全部合格(生产默认 profile 242 枚 / 自定义 profile 实例 290 枚 / 副测试实例仅 queue), 与测试实例(36595)hash 集恰 1 枚(`ae370f14…`)求交**只命中测试便携候选**, verdict=hit 且 reason 指名该路径 —— 生产路径零误中。

### 3.3 浏览器面(Playwright/Chromium 真开设置页, 08:06)

- 导航: `nav.tabs-right button` → 设置 hub → `.hb-card`(卡头「自动化」) → `.hb-blk`(块头「整组迁移」)内 `.bt-bk` 编辑器可见(挂载点 settings-detail.html `b.key === 'config.relocate'` 块尾, 与 e2e/settings-bt-backup.spec.mjs 同款选择器)。
- **空态目检**: 输入框值空, `placeholder = "留空 = 未启用, 可点自动探测"`(计划 S4 文案逐字); 说明文案含「探测只回填草稿, 保存才落盘」; 「自动探测」按钮可见可用。
- **点按钮后证据区渲染**(verdict 行/原因行/存储行齐全):
  `verdict_cls = "bt-bk-verdict warn"`, `verdict_text = "多个候选合格且无法消歧 —— 未做任何填写, 请核对下方候选后手动填入"`,
  `reason = "4 个候选合格且其中 2 个 hash 命中, 无法消歧; 拒不猜测(D5), 手动键兜底"`,
  存储行 `qB 恢复数据存储: Legacy`。输入框保持空、配置零改动 —— **D5 拒不猜测的前端行为真机成立**(计划外加分项: 本轮意外以真机形态覆盖了 ambiguous 分支的 UI 面)。
- 截图: `attachments/26-11-11-0804-real-relocate-bt-backup-probe-01-home.png`(首页) / `…-03-editor-empty.png`(设置页编辑器空态含 placeholder)。证据区截图(04)因脚本 bug 未及拍摄, 见 §05-4。
- 注意: 浏览器跑此轮时 36595 已被 clone3 污染(08:05 的 3000 枚), 故按钮实测拿到的是 ambiguous 非 hit —— **非产品行为偏差**, 是环境态变了(时间线见 §04)。

## 04 BLOCKED 原因与时间线(多 clone 实例冲突)

| 时刻 | 事件 |
|---|---|
| 08:01 | `real.guard` 全绿(两实例 firewalled, 真实种子 0) —— 开工时无占用迹象 |
| 08:02 | 我方 L0 假种子入库(1 枚) + dev.webui 起(读侧最小配置) |
| 08:03 | 端点直探 = **hit**(§3.2, 干净态, hash 集 = 我方 1 枚) |
| 08:05 | **clone3**(`D:\Projects\zcode\auto-qb-zcode-clone3`)起 `python -I tests-real/.work/s0/inject.py`(进程 08:05:22, PowerShell 实查): 向 36595 注入 **3000 枚 real-fake**(`g####.bin`, save_path `R:\qbt-fake\s0\lib\…`, 08:05 实测 2837 checkingDL/163 stalledUP), 向 36596 加 `jit.bin`(802ebce9…); **我方种子 `ae370f14…` 被对方轮次清除**(36595 torrents/info 与 BT_backup 均已无痕) |
| 08:06-08:07 | 浏览器探测 = ambiguous(4 合格候选中 2 hash 命中: 36595 自身 3000 枚 + 36596 经 jit.bin 同 hash 命中) —— hit 恒不可达 |
| 08:08 | 按纪律定案停手: 后续步骤全部需要重造种子或关停实例 = 踏 clone3 现场 |
| 08:11 | 足迹清理: webui 停(6261 释放); **real.down / real.seed.clean / real.guard 复跑刻意不执行**(分别会关停对方在用实例 / 删 `R:\qbt-fake\s0` 对方数据 / pause-all 打断对方 checking), 双实例 firewalled 原样留给对方 |

**未完成面**(复测轮待做): ① hit 的 UI 回填(草稿=测试便携路径)→ actbar 脏态 → 「保存并应用」→ PUT /api/config → 派生配置 `relocate.bt_backup` 落盘片段; ② offline 组(real.down 后点按钮, 200 + online=false 未自证标注); ③ 收尾 real.seed.clean + real.down + guard 复跑。复测前置: 确认 clone3 s0 轮已收尾(其实例状态恢复 + 无并发驱动进程)后重走 §03 干净态。
**复测闭环(26-11-12)**: 上列①②③连同判据③(整组迁移, 经用户拍板同盘近似拓扑替代)与清场已全部走通 —— 逐字证据与三态见 `26-11-12-0229-real-relocate-bt-backup-retest.md`。

## 05 计划外发现(只记录不修)

1. **多 clone 共享实例的并发冲突, 开工 guard 探不到**: guard 的静态白名单+在线核验+快照只能看「端口在不在/种子净不净」, 探不到「另一 clone 的驱动进程将在 N 分钟后压上」。本轮 guard 全绿 4 分钟后 clone3 的 3000 枚注入落地。缓解靠人(排期错峰), 机械面(如 guard 增加对非本 clone 驱动进程的启发检测)不在本轮范围。
2. **real-fake 标签跨 clone 无主**: 我方的种子被对方轮次的清场一并删净(real.seed.rm --all 按 real-fake 标签全扫实例条目; real.seed.clean 按 R:/qbt-fake 与 tests-real/.work 两路径全删磁盘残留 —— 两者均不分创建者)——共享单实例语义下这是既有设计, 但意味着**两 clone 同期跑 real.* 时互相清场**, 与「停手报告」纪律互为因果, 排期错峰是唯一解。
3. **`D:\Programs\qBittorrent-2` 实例(生产侧, `--profile=D:\Programs\qBittorrent-2\profile`)被探测推导为 portable 候选**: 该实例 profile 目录恰与 `<exeDir>/profile/` 重合, 探测器不解析命令行(按计划 §2.3 口径, exe 旁有 profile/ 即推导), origin 标「便携」。行为符合 spec(exe 目录事实推导 + hash 自证兜歧义), 非缺陷; 记录备查: 「--profile 不可静态探测」在 dir 恰为 `<exeDir>/profile` 时会以 portable 形态被命中, 消歧正确性由 hash 交集保证(本轮干净态实测正是它被正确压下的例证)。
4. **测试侧脚本 bug(自记)**: Playwright `locator.count()` 未 await(Promise 恒真值)导致对不存在元素走 `innerText()` 30s 超时, phase A 脚本崩在 offline 行检查, 04 证据区截图未及拍摄; 两形态文字证据已在 §3.3。非产品问题。
5. **dev_webui.py CONFIG_TMPL 缺 `schema_version`** → 启动物化迁移 v1→v8 并改写派生配置(留 .v1.bak): RM08 切片 26-10-31-1914 §03-7 已记过同款(当时 v5), v8 下仍然; 派生配置自愈无害, 仅提示后续若给该脚本补键可顺带消除每次启动的迁移 WARNING 行。

## 06 收尾状态

- 我方足迹: 种子已被对方轮次删除(非我方 rm); webui 已停; 派生配置零改动; 驱动脚本与截图留 `tests-real/.work/probe-accept/`(gitignore)与 `attachments/`。
- 共享实例: 36595/36596 firewalled 原样(clone3 s0 轮现场未动); **未跑** real.down / real.seed.clean / real.guard 复跑(理由 §04)。
- 本切片即本轮全部产出; 不立 task 档案、不改 memory-bank 其它面(S7 收尾归主会话)。
