# 26-11-01-0516-real-torrent-transfer-r3.md —— 明细(自 26-11-01-0516-real-torrent-transfer-r3.md 外迁, 逐字保留)

> 主件: [../26-11-01-0516-real-torrent-transfer-r3.md](../26-11-01-0516-real-torrent-transfer-r3.md)
> 口径: 见 [../../baseline.md](../../baseline.md)

## 03 修复定点复核(上轮入池三处, 本轮逐一复验不复现)

1. **已存在误判「失败」→跳过形态(26-11-01-0334 bug, 修复 commit f556b11f 409探针兜底)**: API TR-05 回执「跳过: 目标已存在(添加被拒且目标查得同 hash); 源已保留」summary skipped=1; UI-04a toast 同口径计入跳过, 行内图标 `sx-warn` 非 `sx-error`。上轮「失败: 目标添加请求失败(Conflict)」误判形态不复现。
2. **path_map 分隔符归一化(26-11-01-0334 enhancement, 修复 commit f731de07)**: TR-09 正斜杠 from(`R:/qbt-fake/tr/fsrc`)→状态=成功 目标 save_path=R:\qbt-fake\tr\fdst 前缀命中=True 数据可达=True 源删除=True; 反斜杠 from 回归(bdst)同过; UI-03 弹窗映射预览同显含正斜杠条目的 3 条规则。上轮「正斜杠 from 静默不命中、按原样路径落」不复现。
3. **transfer 目标 api_key 通路(26-11-01-0335 enhancement, 修复 commit 26cdbe48 后端 + 88a6aceb 前端编辑器)**: TR-新 36596(免鉴权源)→36595(api_key 纯 token 目标)转移成功落位 newsrc, 第 2 颗带预置字段全字段落位; TR-01 test-qb-95-key 探测 status=ok; UI-02 补充: 编辑器「API Key」输入框存在(type=password, 占位符「已设置, 留空 = 不修改」, 值空不回显真值), 测试连接绿「连接成功: qBittorrent v5.2.3」。上轮「纯 token 目标无法作为转移目标(空密码 401)」不复现。

## 04 环境与收尾核净

- 守卫: 开工 `real.guard` 全绿(36595 pid=41868 8 真实种子 paused / 36596 pid=39300 空库起步, 与上轮同 pid); 收尾复跑全绿 —— [ok] 36595 pid=41868 connected 真实种子 8 个已全部暂停 / [ok] 36596 pid=39300 firewalled 真实种子 0 个, pid 与开工一致; 全机 qB 进程 4 个(本轮双实例 41868/39300 + 既有其它实例 16204/11676), 本轮只 tree-kill 了产品 python(33752→22568), qB 进程零触碰无增减。
- 造件清理: 假种子 23 颗(36595×5: tr04/tr05/tr06b/tr07/trnew2 + 36596×18: tr02/tr03a/tr03b/tr04/tr05/tr06a/tr08/trmix/tr09bs/tr09fs/trnew/trrl/ui6c×3/ui6c2×2/ui6c3)经 `real.seed.rm --all --yes` 全删(连数据文件, 只认 real-fake 标签碰不到真实种子); junction×3(R:\qbt-fake\tr\{bdst,fdst,rldst})先 `os.rmdir` 剪枝再清数据(无递归穿透); `real.seed.clean --yes` 清 tests-real/.work 37 个文件(.torrent×18 / config95.yml·config96.yml / 两份 results 工作笔记 —— 逐字证据已全部誊入本切片)与 R:\qbt-fake 残留; 收尾两实例种子数 8/0 与快照一致。
- 产品配置/进程: config95.yml 本轮改动(grouping.enabled=true + 新增 trackers 段 uifake: domains=["192.168.1.122"] 解锁 UI-06c; path_map 第 3 条规则 rld→rldst 承热重载用例落盘), 非仓库根 config.yml 红线未触; 相位1 产品进程(python 33752→22568, web :39000)`taskkill /T` 已停, 相位2 上轮已停, 无产品进程残留; instances.local.json 在 tests-real/config/(clean 范围外)保留后续轮复用。
- 外发: 零(伪种子无 announce 零 tracker; UI-06c 解锁用 uifake announce=本机死端口连接即 RST 零外连; 目标探测全部本机)。
- 证据口径: 不留截图(用户既定口径), 证据=当轮 DOM 快照/页面文案/回执 JSON 逐字誊录 —— 各 UI 用例关键反馈文案已誊入 §01/§03 对应行(成功 toast/跳过 toast/失败 toast/预检 toast/空态灰项/测试连接四态回显)。
