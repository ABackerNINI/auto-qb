# real-machine §2.7 分片陷阱速查(原文归档)

> 外迁自 memory-bank/testing/real-machine.md · 26-11-08 cap 清零 —— §2.7 分片陷阱速查(RM02-RM09 + 跨卷小容量前置)逐字外迁, **原样保留**。
> 主档案: [../real-machine.md](../real-machine.md)

### 2.7 分片陷阱速查(造法细节看用例 docstring 与切片计划)

- **RM02**: 托管模式首条 ERROR 要 20-40s(等待窗放宽); 断连退避**按簇计数**(probe 数 ≠ 重连尝试数); 直跑 pytest 会互抢端口, 用 `real.suite`(`-n 0`)。
- **RM03**: 断言咬规则**全名** `@规则集.规则名`(裸名不进日志); 规则 `interval` **留空**才是每轮; dry-run 照常分派规则、动作跳写 = 零副作用观测窗; 去重断言走 `exec_history` 落盘账。
- **RM04**: 无 announce 假种子**跳过整条 torrents_added 管线**(归组/维护/限速全不发生)⇒ 必须带 announce(`http://<本机IP>:1/announce` 死端口零外连); 重复 infohash 回 **409 ⇒ 删旧重加, 绝不收养**; **删 junction 绝不递归**(purge 用 os.walk 遇 reparse 点 `os.rmdir` 剪枝); 多标签「, 」连接必 strip(pitfalls/testing/qb-tags-multi-split-strip)。
- **RM05**: 标签**定义**独立于种子存活, 清场必须显式删定义层; 多匹配「第一个」= 配置书写序(`write_cfg` 必须 `sort_keys=False`)。
- **RM06**: 产品从不后端直连(唯一路径 ChannelFetcher→本地端点, 零外连有结构保障), 用例以 HTTP 桩扮演扩展; 三态分档咬专属日志文案。
- **RM07**: 全局限速权威面=transfer 端点(`app/preferences` 旧键静默失效); gtm 状态端点按实况双分支断言, **写端点对就绪工具一律不发**(跨 clone 红线)。
- **RM09**: 命令回执 POST 200 只代表入队, 轮询 `GET /api/cmd/{cmd_id}` 到 status≠pending; reannounce 确认=消解等待模型(`updating` 恒非成功证据, 两态用 `FakeTracker` 承载)。
- **跨卷小容量前置**(L490): 唯一方式=管理员挂 ImDisk: `imdisk -a -s 96M -t vm -o fix -m Y: -p "/fs:ntfs /q /y"` + 设 `QBT_REAL_SMALL_TARGET=Y:\small_target`; **绝不碰 Recovery/System/EFI 卷**; 前置缺失=断言失败给指引不静默 skip(`lib/small_target.py`); 用完卸载(`imdisk -d -m Y:`, 用户主导)。
