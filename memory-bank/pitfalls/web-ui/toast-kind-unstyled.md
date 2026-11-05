# toast 新 kind 不登记样式 = 与 info 同貌

> 摘要: toast 新 kind 不登记样式 = 与 info 同貌
> 触发: toast, kind, 提示条, warn 档, 消息弹窗, 样式没生效, 与 info 一样, toast 颜色, 语义档, msg-tone, msg-line
**Refs:** memory-bank/conventions/webui.md

### 新增 toast kind 只改了调用点、没在皮肤 CSS 登记语义档 —— 提示条静默落成中性档, 与 info 完全同貌

- **触发**: 给 `this.toast(文案, "warn")` 这类新 kind 加调用点(或从别处抄一个 kind 名进来), 只验「提示出来了没有」, 没验「提示长什么样」。四套皮肤里 `warn` 就是这样攒到 21 处调用点却**整档没有样式**(只 `.toast.ok/.error/.busy/.timeout` 四档有规则) —— 于是"部分受理/已受理但推迟"这类真需要用户留意的回执, 渲染出来与"已导出 .torrent"这种纯告知一模一样: 中性描边 + accent 图标。
- **判别**: ① 症状侧 —— 两种不同严重度的提示并排看不出来(用户报「消息弹窗样式没统一」的一半来源); ② 代码侧 —— `grep -n "\.toast\.\w*" <皮肤>/css/components.css` 的 kind 集 ≠ `grep -rho 'toast([^;]\{0,80\}"\(ok\|warn\|error\|info\|busy\|timeout\)"' shared/*.js` 的 kind 集; ③ 浏览器侧 —— `getComputedStyle($0).borderColor` 对 warn 与 info 取到同一个值。
- **处置**: kind → 语义档是一张**声明表**(flux 现状: `.toast.ok/.warn/.timeout/.error/.busy` 各自声明 `--msg-tone` + `--msg-line` 两个变量, 消费点只读变量); 加 kind 就在表里加一行, 没有第二条路。`info` 是**中性基线本身**, 故意不列规则 —— 列了反而与"无等级"的语义自相矛盾。别用"在 `.toast` 上堆一串 `:not(.ok):not(.busy)…`"兜底: 那只会在下一档新增时再静默一次。
- **守阵**: `tests/test_webui_static_skins_skin.py::test_frontend_static_bundle_health` 第 20 项 `_scan_message_surface_parity` —— 扫「模板图标映射(overlays.html 的 `{[t.kind]: '#i-…'}`)+ JS 调用点」两侧求 kind 全集, 任一侧出现而未登记即红(文案带"新 kind 必须登记语义档"); 同项还钉 `--msg-surface` 恰一处声明、`.toast`/`.modal` 都消费 `var(--msg-surface`/`var(--msg-line)`、以及各档取色期望表。
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)
