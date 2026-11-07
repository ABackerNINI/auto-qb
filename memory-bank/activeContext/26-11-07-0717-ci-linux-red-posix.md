# ci-linux-red-posix

> 摘要: 修复 GitHub Linux CI 三条红: alias_kind_of 真目录误判硬链接(POSIX nlink>=2) -> S_ISDIR 先返回 None; 硬链接 stat 桩改到建夹具之后; 两条 relocate 预检用例的 B′ 不可判定改桩判定层(不用 os.stat 桩, 否则 posixpath.exists 连带把源侧三态判成缺失抢拦) + 守阵 1 例, 两条坑档复发/新增
> 最后活动: 2026-11-07 07:17

**R0(2026-11-07 07:17):** 修复 GitHub Linux CI 三条红: alias_kind_of 真目录误判硬链接(POSIX nlink>=2) -> S_ISDIR 先返回 None; 硬链接 stat 桩改到建夹具之后; 两条 relocate 预检用例的 B′ 不可判定改桩判定层(不用 os.stat 桩, 否则 posixpath.exists 连带把源侧三态判成缺失抢拦) + 守阵 1 例, 两条坑档复发/新增
