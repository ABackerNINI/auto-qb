# 6505 —— WEBUI 首屏根治两期(P1 并发化 + P2 指纹长缓存)收尾全量基线

> 摘要: WEBUI 首屏根治两期(P1 并发化 + P2 指纹长缓存)收尾全量基线
> 基线时间: 2026-11-20 09:40
**Refs:** memory-bank/tasks/26-11-20-webui-boot-static-fingerprint.md

## 验收数字

TOTAL                                                28957     45  10328     63    99%
6505 passed, 6 skipped, 8 warnings in 137.62s (0:02:17)

`commands run test.full` 实测(2026-11-20 09:40, 覆盖率 99% 达标)。真机验收(P1-3 ≤3s / P2-4 ≤1.5s)按用户拍板剥离, 未跑, 待用户在有 qB/浏览器环境做。

## 本改动面

- 三笔本地提交(均 `ship.commit --no-push`, 分支 `feat/webui-boot-first-data-0727`): `204f69df` P1 分片 Promise.all + 脚本 preload 批量插入 / `072f2734` P2-a 静态树哈希 + HTML 令牌替换 / `c5cee5f0` P2-b withV + immutable 四态分流
- `src/auto_qb/webui/static/shared/boot.js`: Promise.all 分片并发 + index 归位; link preload 脚本预取 + 按序 async=false 批量插入; withV() 三处统一追加 ?v=
- `src/auto_qb/webui/server/static_version.py`(新): static 树内容哈希 V(白名单扩展名 + 长度前缀排序, sha256 前 16 位), 挂载时算一次缓存
- `src/auto_qb/webui/server/static_ui.py`: 响应层 HTML 令牌替换(HEAD 提前 return) + 缓存分流(仅 v 匹配 + 非 HTML + 2xx → immutable)
- 四套 `index.html`: head 静态资源加 `?v=__AQB_V__` + 注入 `window.AQB_V`
- 测试: `tests/test_web_api_core.py` 缓存拆分/四态/withV/升级演练+3xx/404/HEAD 边界; `tests/test_webui_static_dom_panel_misc.py` P1 并发守阵; 5 个测试基建文件容忍 ?v= 解析
- 收尾: 坑档 2 条(immutable 须判 status / HEAD 重建 Content-Length) + task 档案 + 架构/坑档事实回写 + 计划/两 issue 双向补链
