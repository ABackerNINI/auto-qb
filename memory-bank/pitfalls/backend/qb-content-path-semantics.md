# qB content_path 是逻辑完成名, 下载中磁盘上可能不存在

> 摘要: qB Web API 的 `content_path` 报的是**逻辑完成形态**的路径 —— 单文件种子在文件尚未落盘、或启用了「未完成文件加 .!qB 扩展名」时, 该路径在磁盘上**不存在**, qB 不会报空也不会报后缀名。对它做存在性分流时若写「非目录即文件」(`isdir=False` ⇒ 当单文件种子选中该文件), 下载中的种子必走错分支: 文件不存在 → 404「目标文件不存在或不可访问」。用户视角是「路径明明存在(父目录在)却打不开」, 与真实根因(目标尚未落盘)相距甚远。
> 等级: L0
> 触发: content_path, root_path, open-path, open_path, 单文件种子, 下载中, 未落盘, .!qB, 未完成扩展名, 目标文件不存在, 打开目标文件夹失败, 定位选中, select, 解析顺序, 辅种组, 组按单个处理

**Refs:** memory-bank/tasks/26-10-11-webui-open-path-resolve.md

## 条目

- **触发**: 对 `content_path` 做存在性分流(打开文件夹/校验/回退); 症状是已完成种子能打开、下载中的不能, 报错文案落在「文件」层。
- **判别**: ①同 save_path 的已完成种子可开、下载中的 404 ⇒ content 目标未落盘; ②报错文案是「目标**文件**不存在」而非「目录」⇒ 走了 select(单文件选中)分支, 即 `isdir=False` 被当成「是文件」; ③qB 侧 `.!qB` 后缀开关开启时, 完成前后文件名不同是常态。
- **处置**: 存在性判定按**实际形态**三段分流, 不做布尔化对偶推导 —— `isfile=True` → 选中; `isdir=True` → 打开目录; 都否 → 回退 `save_path`(至少把目录打开), 只有回退目标也不可访问才 404。单点 `fs.py` 的 `api_open_path`(2026-10-05 修复), 守阵 `test_api_open_path_endpoint`(HD 未落盘回退 / HE 双缺 404)。2026-10-11 起口径细化为「文件 > root_path/content_path > save_path」, 见下条。

- **触发**: 决定"打开哪一个路径 / 选中还是进入 / 组要不要按单个种子处理"。
- **判别**: 用户诉求 —— 「尝试顺序 = 文件(单文件种子) > root_path/content_path > save_path; 打开后**选中条目**(多条目不选中); 组内**只含一个种子**、或组内**路径一致**(辅种组都指向同一份文件)时按单个处理」。
- **处置**: 解析收成单点 `fs.py::api_open_path._probe(rec) -> (target, select)` —— ① `content_path`/`root_path` 中**已存在文件** → 返回该文件 + `select=True`(单文件种子唯一的"选中"层级); ② `root_path` 优先、`content_path` 次之取**已存在目录** → 返回该目录 + `select=False`(打开层据此**进入**该目录, 不是高亮); ③ 都不可用 → 回落 `save_path`(下载中 content_path 是逻辑完成名, 见上条)。组分支(kind=group): 组 key = (规范化 save_path, 文件列表) 已保证这两维一致, 只补内容路径维 —— `_paths_consistent(recs)`(`content_path`/`root_path` **任一**归一后同一取值即视为同一份内容, 空值不参与) **或** 组内 `len(recs)==1` ⇒ 用代表成员走 `_probe`; 否则(确有多份不同内容)退回组 key 首元(save_path)。`root_path` = qB 5.0+ "torrent 文件树**首个公共子目录**"(始终是目录, 空串 = 无根目录), 作目录时优先于 content_path(更贴近内容位置)。守阵 `test_api_open_path_endpoint`(HA–HL + k_a 单成员 / k_b content 一致 / k_d root 一致 / k_c 不一致 四组)。
