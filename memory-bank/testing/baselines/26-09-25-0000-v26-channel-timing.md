# 1562 → 1573 (+11) —— v2.6 通道时序与饿死残留修复

> 摘要: 扩展轮询 5min vs 后端 request_timeout 180s 时序错配是主因(每条约四成概率超时); POLL_MINUTES 5→1 等 7 项; 时分不可考; 当日序位第 8
> 基线时间: 2026-09-25 00:00

- ↑ 收集数 **1562 → 1573**(**+11**; 2026-09-25 **v2.6 通道时序与饿死残留修复**):
  「种子下载不触发」审查实报 —— 主因是**扩展轮询 5 分钟 vs 后端 request_timeout 180s** 的时序错配
  (每条任务约四成概率超时: 烧配额 + 计失败 ⇒ 3 次页面失败 = 12h 熔断)。① 扩展 `POLL_MINUTES` 5 → 1、
  `DEFAULT_POLL_HINT` 300 → 60; ② 不完备刷新有效期 60s → `max(120s, 2×poll)`(旧窗口与 poll 相同 ⇒
  复用轮「只补下载」从不发生 —— 下一轮永远晚一个 ε); ③ 页面取数失败后仍补一次下载
  (`_backfill_on_page_failure`, 待回填来自已持久化索引); ④ 下载阶段让位/人工事件(叫停/扩展硬上限/登录页)
  原样上抛不再计成 tid 失败(旧实现被 `except HrFetchError` 吞掉 ⇒ 关停三次 = 12h 冷却);
  ⑤ 扩展 fetchBinary 登录页检测(`kind=login-page` ⇒ `HrLoginExpired`, SameSite 剥 cookie 实测风险);
  ⑥ Retry-After 以 cooldown 封顶; ⑦ 配额展示按窗口键折算(修「本小时 7/12 · 还能取 12 次」自相矛盾)。
  新增: `test_hr_service.py` 7(窗口 3 + 页面失败补下载 1 + 下载阶段让位 3)· `test_hr_fetcher_channel.py` 1 ·
  `test_hr_ratelimit.py` 1 · `test_hr_report.py` 1 · `test_extension_proxy.py` 1(真跑 node)。
  ★红验 7 条(临时还原旧实现全红, 还原后全绿)。TOTAL 91%(10872/788/3574/325; HR 包 93%)。

耗时: 并行 19.3 / 20.0 / 21.7s(v2.6/v2.7 合并采样)。
