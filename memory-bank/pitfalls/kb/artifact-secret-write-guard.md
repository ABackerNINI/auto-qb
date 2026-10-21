# 工作区写入守卫整文件扫描: 既有 token/Authorization 字面量会拦住对该文件的任何工具写入

> 摘要: 工作区写入守卫(artifact_secret_detected)扫的是**落盘后的整份文件**, 不是本次新增文本 —— 文件里既有 `token: ""`(空串初值)或测试夹具里的 `Authorization` 头这类「长得像凭据赋值」的历史行时, 对该文件的 edit/apply_patch/write **任何一次**都会被拦, 且报错行号指向既有行而非本次改动。绕过(换工具直改)被守卫自己禁止; 唯一正道 = 如实把误判证据交给用户裁定, 批准后用**锚点替换脚本**(断言锚点唯一、不动既有行)落盘, 事后在档案里留痕。
> 触发: 写入被拦, artifact_secret_detected, 键名 token, Authorization, 凭据字面量误判, state.js 写不进, 测试文件写不进, 整文件扫描
**Refs:** memory-bank/testing/baselines/26-10-21-1408-webui-dialog-shell-single-point.md

### 条目

- **触发**: 对一个**历史上就含** `token: ""` / `Authorization: ...` 等形似凭据赋值行的文件做任何工具写入(本轮实证: `shared/state.js` 既有第 23 行 `token: ""`(R10-01 鉴权初值)与 `tests/test_webui_static_dom_page.py` 既有第 1382 行 Authorization 夹具 —— 两处都是空串/测试占位, 非真凭据)。
- **判别**: 报错 `artifact_secret_detected` 且**行号落在本次 hunks 之外** = 整文件扫描误判; 若行号落在本次新增文本内 = 真拦截, 必须改写内容而不是找路子。误判的可复核证据: 对该文件 `rg -n -i "token|Authorization"` 看命中行是否全为存量行。
- **处置**: ①**不要**换 exec/sed 直改绕过 —— 守卫明说误判也要交用户裁定; ②用 ask_user_question 把证据(命中行原文 + 本次新增文本不含凭据的核对结论)交给用户, 拿到「批准写入」后走**锚点替换脚本**(python 临时脚本: 读文件 → 断言每个锚点 `count==1` → 只替换锚点 → 写回, `newline=''` 保留原行尾), 既有行一字不动; ③脚本用完即删, 并在任务档案/issue 里写明哪几个文件走了这条道、为什么; ④连续编辑同一批受影响文件时, 一开始就先 `rg` 排雷, 把要走脚本的文件攒齐一次问掉, 别逐个撞墙。
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)
