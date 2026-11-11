# dev.webui 每次启动无条件重生成派生配置: 已 PUT 落盘的键被冲掉 + WEB 端口漂移

> 摘要: `commands run dev.webui` 每次启动都从 CONFIG_TMPL 无条件重生成派生配置(不 diff 不保留), 上一阶段经 PUT /api/config 落盘到派生配置的键(如 relocate.bt_backup)被静默冲掉, WEB 端口也重新 OS 分配 —— 跨阶段真机轮(P1 存的键 P2 找不到、脚本还连着旧端口)的现场漂移源。
> 触发: dev.webui, dev_webui, CONFIG_TMPL, 重生成配置, PUT 落盘被冲, 端口漂移, 端口重分配, WEB 端口, 多阶段真机, 派生配置

## 本篇只回答

多阶段真机轮里用 dev.webui 当产品面时, 上一阶段落盘的配置键消失、WEB 端口变了, 怎么判别与处置。

### 重启 dev.webui 后派生配置回到最小模板 —— 键被冲 + 端口漂移

- **触发**: 同一真机轮跨阶段重启 dev.webui(产品进程死亡重拉 / 端口换号重起), 而前阶段曾对运行中的产品 PUT 过配置键 —— 启动时 CONFIG_TMPL 覆写派生配置, PUT 落盘的键(例: relocate.bt_backup、trackers 条目)静默丢失; WEB 端口每次 OS 分配(P1 51407 → P2 59048)。附带面: 派生配置未设 data_dir 键 ⇒ 产品 data_dir 默认仓库根 auto-qb-data/, journal/spec/daemon 账会落到 prod 数据目录下(用后须删净)。
- **判别**: ①派生配置(Temp/auto-qb-dev-webui/config.yml)里前阶段落盘的键消失; ②dev.webui 启动日志的 WEB UI 地址端口与上阶段不同; ③产品行为「忘」了前阶段设置(relocate 已禁用/tracker 条目消失)但没有任何错误行。
- **处置**: 跨阶段复用 dev.webui 时, 每次重启后重新核对派生配置关键字段 + 从启动日志取新 WEB 端口再驱动浏览器/脚本; 前阶段落盘的键当「易失」对待, 需要持久时把值写进驱动脚本重建而非依赖派生配置留存; 用完清场时记得检查 data_dir 默认落点(auto-qb-data/relocate/ 等)是否有测试账残留。修面 = dev_webui.py 启动改为「已存在则不覆写」或 diff 后保留非模板键, 属产品侧脚本改动, 走入池不就地修。
- **守阵**: 无机检(开发脚本行为); 纪律靠本条。
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)

**Refs:** memory-bank/testing/real-baselines/26-11-12-0229-real-relocate-bt-backup-retest.md
