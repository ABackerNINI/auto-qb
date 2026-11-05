# qB fastresume 编辑纪律: 当场改必被覆盖/双键/坏文件静默丢种

> 摘要: 改 qB 的 BT_backup fastresume 有四条铁律 —— ①qB 在线时写入必被秒级覆盖(pause/start/标签等 ~20 类操作挂 `deferredRequestResumeData`, 实测 0.5s), 只能写 qB 下线窗口; ②save path 是双键(`save_path` lt 实际 + `qBt-savePath` qB 账面), 只改其一 = 半效编辑; ③坏 bencode = qB 静默丢种(仅 INFO 级日志, 非 missingFiles 链); ④指向旧路径的删链/删种各有门。机制单点 = 计划 26-11-05-0808 §2.2。
> 触发: fastresume, BT_backup, qBt-savePath, save_path, 改路径, relocate 收尾
**Refs:** memory-bank/tasks/26-11-05-backend-relocate-fastresume-finalize.md

### fastresume 路径改写(relocate 收尾类操作)

- **触发**: 任何「绕过 qB API 直接改 fastresume 文件」的代码或实验(relocate 整组迁移收尾、手修 save_path、实验脚本改键)。
- **判别**: ①改完几秒内文件 mtime 变、值回旧 = 被 qB 内存态重写; ②API save_path 与实际加载位置不一致 = 单键半效; ③重启后种子从 API 无痕消失 + 日志仅一行 INFO「无法解析恢复数据」= bencode 写坏(N6 实测形态)。
- **处置**: 只在 qB 下线窗口写(WebUI 失联探测); 双键同改且逐键在原串上做前缀替换(两键分隔符风味不同: lt 反斜杠 / qBt 正斜杠, 禁止重推导路径串); 写前 bdecode 往返自校验 + 原子落盘(tmp+replace) + `.bak` 备份; AutoTMM 成员无 qBt-savePath 键, 闸门排除; 删链门 = 「save_path 等于旧根 OR 位于旧根之下」双判据 + 组外依赖扫描清零; junction 存续期内拦截带文件删种(deleteFiles=true 会穿 junction 误删新位置数据)。完整设计 = 计划 26-11-05-0808 §3, 机制行号表 = 其 §2.2。
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)
