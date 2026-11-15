# input.files 恒 truthy(FileList 对象) —— 取消选择兜底要查 .length

> 摘要: input.files 恒 truthy(FileList 对象) —— 取消选择兜底要查 .length
> 触发: input.files, FileList, truthy, 文件选择, 取消选择, FileReader, 导入, 上传, 兜底, if (!files)

## 本篇只回答

前端动态文件选择器里「用户取消选择」的兜底判定为什么不能用 `!input.files` —— FileList 对象恒 truthy。单点先例: `webui/static/shared/ui_prefs.js::aqbUiPrefsPickFile`。

### `if (!inp.files)` 恒假 —— 取消选择时 files 是空 FileList 对象不是 null

- **触发**: 动态建 `<input type="file">` 收文件, 用 focusout(或 cancel 事件不可用的老内核)兜底「用户取消选择」路径时, 用 `!inp.files` 判「没选文件」。
- **判别**: 用户取消选择后 Promise 悬挂不 resolve、input 节点泄漏留在 body 上 —— 因为取消时 `inp.files` 是**空的 FileList 对象**(恒 truthy), `!inp.files` 永远不成立。
- **处置**: 判空查 `.length`: `if (!settled && (!inp.files || !inp.files.length)) settle(null)`; 同理取文件用 `inp.files && inp.files[0] ? inp.files[0] : null`。Chromium 113+ 优先挂 `cancel` 事件, focusout + 延迟查 length 只作老内核兜底。
- **守阵**: 选文件终态由 e2e `e2e/settings-backup.spec.mjs` 的 filechooser 用例覆盖(filechooser 事件注入文件, 等价用户在系统对话框选中); **取消终态无自动化守阵**(原生文件对话框不可注入), 靠 focusout+`.length` 兜底代码位与人工验证。
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)
