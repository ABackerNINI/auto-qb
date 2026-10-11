# 26-10-11-2315-doc-links-strict-check — 坏链判据收紧 + 容器代理透传

> 摘要: 用户贴 CI 单条红(`test_doc_links_are_not_broken`: `pitfalls/kb/index-archive-view.md:45 → ...`)求助修复, 并追问「提交前为什么没拦下来」。**根因不是链接层级写错, 是省略号占位被当真链接 + 判据被 Windows 路径归一化骗过**: `(dir/rel).exists()` 在本机对 `kb/...` 返回 True(Win32 剥掉结尾的点 ⇒ 路径塌成父目录 `kb/`), 同族还有大小写不敏感 ⇒ **本机三道防线(doc.links 闸门 / test.quick 闸门 / 手工 test.full)必然同源放行**, 只有 ubuntu job 会红。处置: ①坏链处照抄原文并裹行内代码(不再用省略号占位); ②`check_doc_links.link_exists` 改**组件级 `listdir` 精确比对**(区分大小写 + 拒绝结尾点/空格), 新增守阵并在旧判据下红验通过; ③`test.linux` 的网络死结一并解开 —— `linux_ci.py` 加**代理自动透传**(回环主机改写 `host.docker.internal` + 补 `--add-host` + `no_proxy` 恒并入回环), 守阵 `test_linux_ci.py`。坑与两轮容器假红取证写进 `pitfalls/testing/patching.md`(⑥ 新节 + 判别法四类升五类 + 容器网络两坑)。档案: [26-10-11-doc-links-strict-check](../tasks/26-10-11-doc-links-strict-check.md)。
> 触发: 坏链, doc.links, 相对链接, 省略号占位, Windows 路径归一化, 结尾点, 大小写不敏感, exists, 平台差异, CI 红, test.linux, 容器代理, no_proxy, host.docker.internal
> 最后活动: 2026-10-11 23:15

**Refs:** memory-bank/tasks/26-10-11-doc-links-strict-check.md

## 状态

- **已完成并可结题**: 坏链已修; 判据收紧 + 守阵(红验已做); 代理透传 + 守阵(红验拆两处即红); 文档回写三处; 三侧实测(Windows 全量 / 包内脚本 / 容器 Linux)见基线切片 `26-10-11-2315-doc-links-strict-check`; 随本次提交入库。
- **本轮副产物(下次直接用)**: `commands run test.linux` 现在自带代理透传 —— 宿主代理写在回环上也照跑, 不必再手拼容器命令; 判据侧"路径存在性"一律按 Linux 口径判, 本机绿不再等于 CI 绿。
- **未动(范围守恒)**: `linux_ci.py` 不加"关透传"开关(默认正确解, 无开关必要); `--all` 档新增的 3 处 `SOUL.md`/`TOOLS.md` 坏链(未入库的身份模板件、`--all` 未接任何闸门或测试)只报告不修; `memory-bank/modules/webui-static-contract.md` 的存量 cap 债务(21,166 > 20,000 字符)与本次无关, 留待专门的清理会话。
