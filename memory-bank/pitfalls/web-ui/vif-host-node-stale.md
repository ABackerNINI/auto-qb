# v-if 拆建后模块级缓存的宿主节点失效: "已挂载"缓存的是节点身份, 节点会死缓存不会

> 摘要: 详情面板 aside 被 v-if 拆掉重建后, 变体宿主换了新节点, 而核心层模块级缓存 `_dtMounted` 仍持**旧节点**引用 —— 挂载函数看到"已挂"直接返回, 变体渲染进新宿主无人接管, 页签整幅空白; general/content 页签无独立通知源(不像 traffic/files 有数据轮询触发重渲), **永不自愈**。处置 = watch(drawerVisible) 种子支路进场补 `$nextTick(_dtSync)` 重挂, `_dtSync` 幂等(已挂且 `isConnected` 才跳过)。
> 触发: 切设置页返回详情面板空白, v-if 重建, 宿主节点失效, _dtMounted, 变体宿主, detached 引用, $nextTick 重挂, watch drawerVisible, 种子支路, 页签空白, 永不自愈, isConnected, 挂载缓存
**Refs:** memory-bank/tasks/26-10-07-webui-detail-panel-followups.md

## 条目

- **触发**: 面板 aside 容器用 v-if 控制(关面板拆节点、开面板建新节点); 核心层变体挂载用模块级
  `_dtMounted` 标记"宿主已挂"。用户从详情面板切到设置页再返回: aside 重建 → 变体宿主是**全新节点**,
  `_dtMounted` 仍为真 → 挂载逻辑短路跳过 → 变体没人挂载, 页签空白。有数据轮询的页签(traffic/files)
  靠下一拍数据通知侥幸自愈, general/content 纯静态字段**永远停在空白**。
- **判别**: 模块级缓存存的是**节点引用**而不是可重验的状态 —— "已挂载"这个事实的载体(节点)会死,
  缓存本身不会。凡「模块级持有 DOM 引用」与「v-if / innerHTML 重建」并存, 先问一句"这个引用还
  `isConnected` 吗"。复现: 开详情面板 → 切任一设置页 → 返回 → devtools 看面板内是否有 detached
  旧节点、变体内容是否缺失。
- **处置**: 可见性变化是 v-if 拆建的**伴随事件** —— watch(drawerVisible) 种子支路进场补
  `$nextTick(_dtSync)`(等新节点真的进文档再挂, 时序对齐 v-if 完成重建); `_dtSync` 幂等: 已挂**且**
  `isConnected` 才跳过, 旧引用失联就地重挂, 同目标重入零副作用。守阵
  `test_drawer_seed_reentry_variant_remount`。
- **复发**: 0(新记, 2026-10-07)
