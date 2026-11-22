# 6790 —— 6790 passed, 6 skipped —— 行菜单重开 flyout 残留修复(issue 26-11-20-0321)

> 摘要: 6790 passed, 6 skipped —— 行菜单重开 flyout 残留修复(issue 26-11-20-0321)
> 基线时间: 2026-11-22 11:59

## 验收数字

`commands run test.full` 实测(2026-11-22 11:56, Windows, 2m29s, HEAD = 8ff76f0b + 本批未提交改动, 分支 develop):

```
TOTAL                                                30681     85  10942     87    99%
6790 passed, 6 skipped, 8 warnings in 149.04s (0:02:29)
```

覆盖率闸门通过(99% 线 rc=0)。与上基线(26-11-22-0821, 6789P/6S)相比 passed +1(本轮新增
`test_frontend_row_menu_reopen_clears_flyout` 守阵), skipped 持平; TOTAL 表语句/分支数与上基线
一致, 覆盖率同为 99% 无回退。

## 本改动面

- 产品侧: `shared/menu.js` 的 `openMenu` / `openMemberMenu` 开层补 keepSub + subMenu/subFlip/subTop 清链
  (与 openHeadMenu 同款; virtual 组行走 openMemberMenu 委派同款覆盖)。
- 守阵: node 电池直跑三入口(修复前 12 项残留断言红, 修复后全绿); e2e 双入口双皮肤真浏览器用例
  (修复前 vm.subMenu 停在 transfer, 修复后绿); fast 门禁 542 passed / 5 skipped。
- 真机轨: 纯前端状态清链, 桩 + 真浏览器双皮肤可验, 无 qB 真执行需求。
