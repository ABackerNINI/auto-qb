# webui-password-autofill-dirty

> 摘要: 修 WEBUI「点进常规就显示有改动还没保存」: 根因是密码框被包成登录表单形状且无 autocomplete, 浏览器/密码管理器自动填充在未聚焦时派发 input, 原 @input=set() 把填充值写进配置树; 改 autocomplete=new-password + setSecret 焦点判据(未聚焦不写树并回填显示), 静态守阵 + 双皮肤 e2e 各一条(红绿双验), 全量 3758 passed / 10 skipped
> 最后活动: 2026-10-20 01:12

**R0(2026-10-20 01:07):** 修 WEBUI「点进常规就显示有改动还没保存」: 根因是密码框被包成登录表单形状且无 autocomplete, 浏览器/密码管理器自动填充在未聚焦时派发 input, 原 @input=set() 把填充值写进配置树; 改 autocomplete=new-password + setSecret 焦点判据(未聚焦不写树并回填显示), 静态守阵 + 双皮肤 e2e 各一条(红绿双验), 全量 3758 passed / 10 skipped

**R1(2026-10-20 01:12):** 用户追加报障「HR 在线核实页同样」: 取证确认同一根因(该页唯一密码框 config.hr_check.channel.token 与常规共用同一模板分支), 旧实现未聚焦 input 即把 token 写脏, 修复后不再; 补 e2e 一条(page.route 注入 hr_check 段, 双皮肤 4 passed, 回退源码 4 failed 红验), 坑档与基线切片同步补 HR 页判据
