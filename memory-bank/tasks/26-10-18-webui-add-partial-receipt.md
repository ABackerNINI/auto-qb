# 26-10-18-webui-add-partial-receipt — WEBUI 部分种子添加失败(已存在)时添加窗口不消失 —— 三态回执修复

**Status:** Done
**Added:** 2026-10-18
**Updated:** 2026-10-18
**Summary:** WEBUI 部分种子添加失败(已存在)时添加窗口不消失 —— 三态回执修复
**Topics:** webui-add-partial-receipt
**Refs:** memory-bank/pitfalls/web-ui/add-partial-receipt.md, memory-bank/testing/baselines/26-10-18-2220-add-partial-receipt.md

## 原始请求

1. 「修复：WEBUI部分种子添加失败(已存在)时添加窗口不消失」(2026-10-18, 用户原话)

## 思考过程与决策

- **根因(两层)**: ① qB 的 `/torrents/add` 对重复种子**不是整批 409**, 而是 HTTP 200 +
  `failure_count>0`(其余成功) —— 部分成功是常态路径; ② 旧 `_add_outcome` 只回布尔
  (无被拒才算受理), `_cmd_add_torrents` 把"部分受理"与"全拒"一起写成 `error` 回执;
  前端 `submitAddTorrent` 只认 `r.ok` 关窗 ⇒ 种子加进去几个, 窗口赖着不动还报"添加失败"。
- **关键取舍**: 修法不是"部分失败也关窗"这个单点行为, 而是**回执三态化** —— "成功没有"与
  "有被拒的没有"是两个独立问题, 压进同一个布尔, 消费端只能二选一, 对部分成功必然错一头。
  三态词汇表**复用既有 reannounce 的 ok/error/warn**(不造第四态): 全受理 `ok` /
  部分受理 `warn`(文案带"成功 N / 失败 M / 待定 K"计数) / 全拒 `error`。
- **前端行为口径(两个方向都钉)**: warn(部分受理)= 已受理但有保留 ⇒ **关窗** + warn toast
  (想补提再开窗); error(全拒)= 那一份文件/链接原样没进 qB ⇒ **留窗**等用户改完重提。
  反向的过度修复(把 error 也关窗)同样错, e2e 成对钉住。
- **`_add_outcome` 中间态坑(本轮实测抓到)**: 第一版只在 handler 聚合层做三态, 单调用元数据
  形态(success=1/failure=1)的 partial 仍被布尔判据压成 False ⇒ 与全拒不可分。必须把
  **单次调用判定**也扩成三值(`ok`/`partial`/`fail`), 聚合层再跨文件/链接两次调用收敛。
  守阵因此补了"元数据单调用 partial"用例(longtail 形态一), 旧文本混合两调用为形态二。
- **e2e 注入手法**: `page.route` 拦 `POST /api/torrents/add`(命令不入真队列, 回约定
  cmd_id)+ 拦 `GET /api/cmd/{id}` 供出注定的回执 —— SSE 侧无该 cmd_id 事件, 轮询路径
  确定性拿到, 不与事件路径赛跑。后端三态语义由单测钉, e2e 只钉前端反应。
- 未做(范围守恒): bulk 命令的"部分 hash 缺失也报 error"口径不动(与本案同形但属另一消费面,
  删除链的留窗/拦截语义不同, 不借修 bug 之机放宽); reannounce 的 warn 语义不动。

## 实现计划

1. 后端 `_add_outcome` 布尔 → 三值受理态; `_cmd_add_torrents` 聚合出三态回执(ok/warn/error)。
2. 前端 `submitAddTorrent` 按 `r.status` 分流: warn 关窗 + warn toast; error 留窗。
3. 更新既有单测断言(部分失败 error → warn)+ 补两种 partial 形态用例。
4. 静态守阵(接线)+ e2e(行为, 双皮肤 × 两方向), 均做红验。
5. 全量闸门 + 基线切片 + 坑档 + 本档案。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 后端三态回执(commands.py: `_add_outcome` 三值 + `_cmd_add_torrents` 聚合) | Done (2026-10-18) |
| 2 | 前端 submitAddTorrent 按 r.status 分流(warn 关窗 / error 留窗) | Done (2026-10-18) |
| 3 | 单测更新与补形(test_web_admin 断言改 warn + test_web_longtail 两种 partial 形态) | Done (2026-10-18) |
| 4 | 静态守阵 + e2e 双方向(均红验: 回退修复即红) | Done (2026-10-18) |
| 5 | test.full 全量 + 基线切片 + 坑档 + 立档 + kb.wrap | Done (2026-10-18) |

## 进度日志

### R0 · 立档 (2026-10-18)

- 用户报障「部分种子添加失败(已存在)时添加窗口不消失」→ 定位两层根因(qB 部分受理常态 +
  回执二态化) → 三态回执修复落地: 生产 2 文件(`webui/commands.py`、`static/shared/add_torrent.js`),
  测试 3 文件(既有断言改向 + 新增静态守阵), 新增 `e2e/add-partial-receipt.spec.mjs`。
- 验证: `commands run test.full` 全量过(数字见基线切片 `26-10-18-2220-add-partial-receipt`);
  `npm run test:e2e:fast` 65 例过; 静态守阵与 e2e 均对"修复前形态"红验通过。
- 知识产物: 坑档 `pitfalls/web-ui/add-partial-receipt.md`(新)+ `pitfalls/backend/qb-api.md`
  (`_add_outcome` 三值口径回写)。

- 2026-10-18 22:27 三态回执修复落地并全量验证: 后端 _add_outcome 三值受理态 + _cmd_add_torrents 聚合(ok/warn/error), 前端 submitAddTorrent 按 r.status 分流(warn 关窗+toast / error 留窗), 单测/静态守阵/e2e 双方向均红验; test.full 与 e2e fast 全过(数字见基线切片)
