# open-path 下载中种子打开失败修复

> 摘要: 用户报「种子详情面板点开保存路径提示『打开目标文件夹失败: 目标文件不存在或不可访问』,路径 R:\Download\PTing 实际存在,同路径已完成种子可正常打开」。根因 = `fs.py` `/api/open-path` 旧解析链「content_path 不是目录 ⇒ 当单文件种子定位选中 ⇒ 文件不存在即 404」无回退;qB 的 content_path 是逻辑完成名,下载中未落盘(或 .!qB 后缀)时必走错分支,而详情面板四个路径按钮全共用该端点。
> 最后活动: 2026-10-05 20:15

## 已完成

- [x] 根因定位: `src/auto_qb/webui/server/routes/fs.py` `api_open_path` torrent 分支 —— `isdir(content)=False` 一律 `select=True`,未落盘即 404;前端 `drawer.js` 四按钮 + `menu.js` 全部只传 kind+hash 走同一链。
- [x] 修复: 三段分流 —— isfile→选中(R10-10 不变)/ isdir→打开内容目录 / 都否→回退 save_path;仅回退目标也不可访问才 404。安全边界不变。
- [x] 守阵: `test_api_open_path_endpoint` 加 HD(未落盘回退)/ HE(双缺 404 终检);全量 **2621 passed + 4 skipped / 98% / 29.41s**,基线 [26-10-05-2015](../testing/baselines/26-10-05-2015-webui-open-path-fallback.md)。
- [x] 回写: 坑档 [qb-content-path-semantics](../pitfalls/backend/qb-content-path-semantics.md) + `modules/webui-static-contract.md` open-path 口径更新 + kb.index。

## 正在进行

(无 —— 待提交)
