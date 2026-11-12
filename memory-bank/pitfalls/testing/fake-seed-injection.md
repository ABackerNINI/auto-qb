# 批量注入假种子的三个坑(skip_checking / 配方漂移 / 首同步风暴丢归组)

> 摘要: 大批量注入 qB 假种子(压测/测量库形)三坑合档 —— ①qB 默认入库逐种子校验 ~1s/种, 3000 种 = 45 分钟, 必须 skip_checking; ②手搓注入变体「配方漂移」三处全坏(漏 payload 数据文件 = 全组 missingFiles + 漏 announce = 永不归组 + leech 等不到 seeder)而脚本不报错(rc 只看成员数); ③首同步风暴丢归组的根因是「成员缺 announce 永不自愈」, 风暴只是放大器 —— 全员自带 announce 后风暴不丢归组。
> 触发: 批量注入, 假种子, 测量库形, skip_checking, missingFiles, 永不归组, 首同步风暴, 归组, tracker 匹配, 注入配方, inject.py, 压测库, 真机轨, stalledUP
**Refs:** memory-bank/tasks/26-11-11-webui-group-hash-ref.md (R1 节, 2026-11-11)

### qB 默认入库逐种子校验吞吐 ~1s/种

- **触发**: 批量 add 种子后等「全部做种态」—— qB 默认对每个新种子排队做完整性校验, ~1s/种(checking_memory_use 调 1024 无效), 3000 种 ≈45 分钟。
- **判别**: 入库进度按校验队列爬, 种子长时间停在 checking。
- **处置**: 注入一律走 qB 原生 `skip_checking`(信任「文件已就位」), 前提是注入脚本先写好 payload 数据文件再入库; 实测 3000 种入库 40s(@5000 34s)。

### 手搓注入变体「配方漂移」三处全坏且脚本不报错

- **触发**: 相对已验证配方(inject.py `add_group`: 先写数据文件 + 全员 announce)手搓新的 build 循环变体(如 inject_monster.py)。
- **判别**: 三处漂移**全坏但脚本 rc 只在成员数不达标时才失败** —— ①没写 payload 数据文件 → skip_checking 信任落空, 全组 missingFiles; ②除 0 号外成员没给 announce → 产品归组管线要求 tracker 配置匹配, 无 announce 永不归组(prod.log 连刷「未匹配 tracker 配置」行); ③leech 等一个永远不存在的 seeder(stalledDL)。判别看 qB 侧种子态(missingFiles/stalledDL)与产品 prod.log 未匹配行, **不是脚本退出码**。
- **处置**: 新注入变体必须**复用 add_group**(写文件 + announce 面单点), 不手搓 build 循环; 已注入的坏种全删重注入(WebAPI delete 400/批; 删除字段名是 `deleteFiles` 不是 `delete_files`; 同 infohash 重注入, 副实例 leech 无需重加)。可归组的假种子配方单点: 单文件种子 + 同 savepath/同文件名/确定性内容 + **piece_len 逐成员不同**(16384/32768/65536/…)→ infohash 互异、全部可校验做种、落同一辅种组(组键 = `(path_normalize(save_path), (文件名,))`, grouping_mod.group_key_of); **多文件 + info.name 变体配方不可行**(qB 5.2.3 files API 的 name 含 info 根目录, file_map 不同组)。

### 首同步风暴丢归组: 根因是成员缺 announce 永不自愈

- **触发**: 产品启动一次性发现大批新种子(首同步风暴)后清点归组数对不上。
- **判别**: 落单者 = **每组首个成员**(tracker 匹配失败那个, 实测 ~24%), 落 single 且**永不自愈** —— post 相位只重归组已归组者, 不回头收落单者。
- **处置**: 删净落单者 → 等两轮 sync → 逐个低速重加(20/s; 删加同轮内完成产品看不到变化, 必须跨轮)。产品配置面: 归组要求 tracker 域名匹配(产品配置加 `trackers.<名>.domains: [127.0.0.1, …]` 后归组成立)。**根治 = 成员入库自带可匹配 announce: 全员自带 announce 的库重启归组 5s 一次到位零落单(@5000 复核)** —— 丢归组的根因面是「成员缺 announce」而非风暴本身, 风暴只是放大器。
