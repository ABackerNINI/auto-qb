# 1233 → 1375 (+142) —— HR 在线核实 M1: 核心管道

> 摘要: 新包 hr/ 全链路(bencode/parse/adapters/model/store/ratelimit/resolve/service/report/fetcher) + 配置接入全链路; 11 条首跑真红后全绿; 时分不可考; 当日序位第 1 (09-24)
> 基线时间: 2026-09-24 00:00
> 档案: 26-09-22-backend-partial-hr-verify

- ↑ 收集数 **1233 → 1375**(+142; 2026-09-24 **HR 在线核实 M1: 核心管道**):
  用户令「实施该计划」(部分种子 HR 的在线核实), 并指定页面样本 `D:/Projects/站点页面/BTSchool`
  与前期实验脚本 `scripts/hr_fetch_experiment.py` 为输入。本轮落地计划的 **M1(离线可做)**:
  新包 `src/auto_qb/hr/` —— `bencode`(infohash 取 info 的**原始字节切片**, 定位跨度时只跳不建对象) /
  `parse`(栈式表格抽取 + 数值容错) / `adapters`(NexusPHP `myhr.php` 九列形态) /
  `model`(站点文件内的账号级状态) / `store`(**每站点一个 JSON + 一把 filelock**, 持锁期间完成
  「读→判有效期→必要时抓→写→释放」; revision 回退 / 心跳被覆盖 ⇒ 退化只读) /
  `ratelimit`(间隔 **只向上抖动** + 小时/天两级配额 + 失败退避熔断 + 时间窗) /
  `resolve`(**三态判定** = 受管束 / 已核实不受管束 / 未核实 + 不可变只读视图) /
  `service`(刷新管道; `dry_run` 零请求零写入、`hr.once` 抓取但不写盘) / `report`(`--hr-once` 走查) /
  `fetcher`(取数通道协议; 后端零 cookie、不直连站点)。
  配置接入全链路: `KNOWN_*_KEYS` + 校验器(**站点 mode != off 但没配 hr 段 ⇒ 配置期直接报错**,
  否则 `check_hr_condition` 恒 False、整站保护静默失效) + `config/schema/hr.py` + 新分组 +
  `HR_CHECK_FIELD_LEVELS`(热重载分级) + loaders; 设置页 Hub 补 `hr_check` 文案 / 未启用判定 / 读数。
  新增 8 个测试文件 + 共享夹具 `tests/hr_helpers.py` 与**脱敏页面 fixture**(取自真实样张结构:
  含 `<td class="embedded">` 包裹表、灰色不可点的「下一页」、免罪链接); 覆盖 bencode 钉死向量 /
  原始切片 vs 重编码(钉死计划 §5 的坑) / 畸形输入 / 表头缺失=改版 vs 表头在 0 行=合法空 /
  防重取三层 / 有效期复用零请求 / 翻页未到底 ⇒ 覆盖证明不成立 / **判定表逐行** /
  **新鲜度闸门不可被 `unknown_policy` 绕过** / 熔断 / 并发锁粒度 = 站点。
  红验方式: 11 条首跑真红(见提交说明), 逐条定位后全绿。
  全量 **1374 passed + 1 skipped** / TOTAL 91%(9278 语句 / 727 未覆盖 / 3128 分支 / 277 partial) /
  sidefx 台账 2212 / 越界 0。⚠ 余下 **M2(取数通道 + 取数线程) / M3(判定联动四消费点) / M4(多站点)**
  未落地 —— 本档案「子任务状态表」逐项记状态。
