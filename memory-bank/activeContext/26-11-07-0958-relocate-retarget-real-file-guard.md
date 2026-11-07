# relocate-retarget-real-file-guard

> 摘要: 认领并修复 issue 26-11-07-0748: retarget_alias 链接位被真文件占据时静默 os.unlink 删真数据(真目录有保护真文件没有); 修法与建议①改道收窄 —— 硬删路径下游存在 hardlink 孪生残名(qB 跨卷搬移删另一名字后 nlink 收敛 1)的有意删除, 一律拒绝会永停 supersede, 故仅 plan 声明 hardlink 且与新目标同尺寸才放行, 其余(意外真文件/云占位符/尺寸不符)一律 RuntimeError 交 D20; 重解析标签豁免收窄为 MOUNT_POINT/SYMLINK(评审 minor 1 条当场修, review.check 过检 1/1); 红验两条+放行族钉两分支, test_alias_fs 68 绿, test.full 5626 passed(见 kb.baseline); issue 翻 Done
> 最后活动: 2026-11-07 09:58

**R0(2026-11-07 09:58):** 认领并修复 issue 26-11-07-0748: retarget_alias 链接位被真文件占据时静默 os.unlink 删真数据(真目录有保护真文件没有); 修法与建议①改道收窄 —— 硬删路径下游存在 hardlink 孪生残名(qB 跨卷搬移删另一名字后 nlink 收敛 1)的有意删除, 一律拒绝会永停 supersede, 故仅 plan 声明 hardlink 且与新目标同尺寸才放行, 其余(意外真文件/云占位符/尺寸不符)一律 RuntimeError 交 D20; 重解析标签豁免收窄为 MOUNT_POINT/SYMLINK(评审 minor 1 条当场修, review.check 过检 1/1); 红验两条+放行族钉两分支, test_alias_fs 68 绿, test.full 5626 passed(见 kb.baseline); issue 翻 Done
