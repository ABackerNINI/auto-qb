# 基线切片 26-10-05-2015 — open-path 下载中未落盘回退修复

> 摘要: 用户报「详情面板打开保存路径提示 目标文件不存在或不可访问, 路径实际存在, 已完成的
> 同路径种子可正常打开」。根因 = `fs.py` `api_open_path` 旧解析链「content_path 不是目录 ⇒
> 当单文件种子选中该文件 ⇒ 不存在即 404」, 无回退; qB 的 content_path 是逻辑完成名, 下载中
> 未落盘(或 .!qB 后缀)时 isdir=False 必走错分支。详情面板四个路径按钮全共用该端点, 故全失败。
> 修法 = 三段分流(文件→选中 / 目录→打开 / 都否→回退 save_path)。
> 基线时间: 2026-10-05 20:15

**Refs:** memory-bank/pitfalls/backend/qb-content-path-semantics.md

- 分支: develop @ 80f48bc7 + 工作区改动(未提交, 等提交指令)
- 命令: `commands run test.full`(Windows)
- **实测 (Windows)**: **2621 passed + 4 skipped, 29.41s, 覆盖率 TOTAL 98%**
  (15815 语句 / 169 未覆盖 / 5400 分支 / 140 partial; 门槛 98% 达标)
- 相对上一基线 [26-10-05-1814](26-10-05-1814-qb-traffic-v3-decimal-interval.md) 真值
  (2619 passed / 15813 语句 / 167 未覆盖 / 5398 分支 / 140 partial): passed **+2** / 语句 +2 /
  分支 +2, 全部来自 sync 合流的其它会话提交(c2ba6054→80f48bc7: 流量窗口快捷键 + 采样 1.5s 档
  修复在 tests/ 新增用例); 本轮 `test_api_open_path_endpoint` 只在**既有函数内**扩断言
  (3b 未落盘回退 + HE 双缺 404), 用例计数不变。
- 核心守阵: `test_api_open_path_endpoint` 的 HD(hash: content_path 指向未落盘文件 + save_path
  存在 ⇒ 200 + opened=save_path + select=False)与 HE(content/save 都不存在 ⇒ 404 终检兜底,
  不调用系统打开); 既有 1-6 场景(目录 / 文件选中 / content 缺失回退 / 组键 / 传 path 被忽略 /
  404·400·401)原样通过 —— R10-10 选中语义与安全红线无回归。
