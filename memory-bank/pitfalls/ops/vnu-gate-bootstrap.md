# check_html --vnu 首跑自举: GitHub 直连被墙且本机无 java

> 摘要: check_html --vnu 首跑自举: GitHub 直连被墙且本机无 java
> 触发: vnu, check_html, vnu.jar, java 不可用, SSL CERTIFICATE_VERIFY_FAILED, release-assets 超时, HTML 规范级检查
**Refs:** memory-bank/tasks/26-11-01-memory-bank-html-syntax-guard.md

### check_html --vnu 首跑自举: 本机无 java + GitHub 直连被墙 → 闸门红在环境不在 HTML

- **触发**: 任何 clone 首次提交含任意 `**/*.html` 改动的件(2026-11-01 闸门扩面后不限 memory-bank) —— 上游新加的 vnu 闸门
  (`check_html.py --vnu --strict`) 首跑要在 `<root>/.tools/vnu.jar`(gitignored, 逐 clone 自举)
  下载 v.Nu(32MB, GitHub releases), 并需要 PATH 上的 `java`; 2026-11-01 在 clone4 实测两处都断。
- **判别**: 失败行闸门 note = 「HTML 规范级增量检查(v.Nu)…」; 输出尾部是
  `urllib.error.URLError: [SSL: CERTIFICATE_VERIFY_FAILED]`(下载被断, 非 HTML 真错)或
  `[红] check_html --vnu: java 不可用 ('java' 未找到)`。注意脚本只支持 GitHub 单一下载源,
  且 `run_vnu(..., "java")` 硬编码 PATH 直呼 —— 不认 JAVA_HOME。
- **处置**(2026-11-01 已在本机落地): ① java 走清华 TUNA 的 Adoptium 镜像(国内直连,
  `https://mirrors.tuna.tsinghua.edu.cn/Adoptium/21/jre/x64/windows/`), 装到 `C:\Java\jre-21`,
  已写用户级 `JAVA_HOME` 与 PATH(Program Files 需管理员, 未提权路径放弃); ② vnu.jar 用
  本机可用通道取(GitHub 直连不通 → 代理端口或浏览器手动下), 放 `<root>/.tools/vnu.jar`
  (PK 头校验 50-4B); ③ 本地先预跑 `check_html.py --vnu --strict <文件>` 再 ship.commit;
  ④ 校验结果可与 W3C 在线校验器(`validator.w3.org/nu/?out=json`, 国内可达)互验。
  ⚠ 新开的终端才拿得到用户级 PATH; agent 会话继承宿主旧环境, 跑闸门仍需 inline 前置
  `C:\Java\jre-21\bin`。
- **守阵**: 无专门机检 —— 环境自举类坑, 症状在闸门失败行(见判别)。
- **复发**: 2 (2026-11-01, 首次含 HTML 改动的提交: 上游 26b66d0a 新加该闸门, 本 clone 环境两断; 用户给代理未起、后手动提供 jar 解决)
  +1 (2026-11-01, **环境2/C盘机**首次含 HTML 改动的提交: 该坑的自举是**逐机器**的, 环境1 机器 2026-11-01 落地过不代表环境2 有 —— java 与 vnu.jar 两处重新断。本次 GitHub 直连可用(`release-assets` 可达), jar 直接下载成功无需代理; java 仍走 TUNA 镜像装 `C:\Java\jre-21`。为什么没命中: 路由没到 —— 会话开工只按硬约束读了 `pitfalls/git/_index.md`, 本坑在 ops 类, 收到闸门失败行后才进来; 后续换机/新 clone 自举时把本条当 checklist)
