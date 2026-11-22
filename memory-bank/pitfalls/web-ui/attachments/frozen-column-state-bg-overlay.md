# frozen-column · 半透明状态底「叠加非替换」(原文归档)
> 摘要: 选中/展开行用裸半透明令牌替换行底，致首格合成基准分家、名称列异色竖带；记录实测、层叠修法与推广判据。
> 触发: 选中行异色竖带, 展开行异色, 半透明状态底, background 简写, 承光层, 首格与行板逐字相等, group-row.selected, group-row.expanded, bg-row

- **⑩ 半透明状态底是「叠加」不是「替换」—— 行板把底换掉, 首格的合成基准就与它分家
  (2026-10-20 用户报「选中的行必显列背景与其它列不一致」)**: 选中/半选行原本写
  `.group-row.selected { background: var(--sel-bg) }`(裸半透明 tint) —— `background` 简写把行底
  `--bg-row` 一并**替换**掉, 行板实际承光层变成**页底** `--bg`; 而首格按 ②⑥ 的口径合成在
  `--bg-row` 上。两边基准分家 ⇒ 选中行名称列整列一条异色竖带。真浏览器逐像素(1440×900, 选中行
  首格与相邻格同相对位置取色): atlas 首格 rgb(38,45,73) vs 相邻列 rgb(34,39,64) = **Δ9**、prism
  rgb(229,234,249) vs rgb(224,230,246) = Δ5, 三主表(种子/辅种/追剧) × 双皮肤全中; 未选中行 Δ0
  (行底本就是 `--bg-row`)。承光层可反解验证: 相邻列可见底 = (tint 透明度回拆) ≈ `--bg`
  (#0e1218 / #f2f6fb), 而不是 `--bg-row`。
  **处置**: 行板改成**层叠**(与首格同一表达式) ——
  `background: linear-gradient(var(--sel-bg, var(--accent-soft)), var(--sel-bg, var(--accent-soft))), var(--bg-row)`;
  `.member-row` 没有吸左首格、也不承 row 底色 ⇒ 拆出来保持原裸柔底不动。修后行板与首格计算背景
  **逐字相等**, 逐像素 Δ0(prism) / ≤1 取整(atlas)。顺带收掉 ⑨ 残留里 selected/partial 那一半
  (渐层不可插值): 两侧基色都不再变, 只有 image 层同帧出现。
  **判据(推广)**: 「首格 == 行板」不能只量首格自己的合成式, 要问**行板自己的底还在不在** ——
  状态规则用 `background` 简写写半透明令牌时, 底就被静默换掉了。修法不是「把首格改成猜页底」——
  那会把正确性绑在「这张表刚好放在哪种底上」(撞 ⑥ 的按面重锚); 而是让行板恢复「状态叠在行底上」
  的结构, 与承载面无关。
  **同族拓展(2026-10-20 用户「group 一同修」同轮收)**: `.group-row.expanded { background: var(--bg-sunken) }`
  是同一个缺陷 —— 下沉底也是半透明、也是**替换**行底。实测展开行(辅种页)atlas 首格 rgb(9,15,25) vs
  相邻列 rgb(9,13,20) = Δ5/255、prism Δ2/255(上一条只报选中态时它低于可辨阈, 故首轮按范围守恒未动);
  处置同一口径: 三皮肤改 `linear-gradient(var(--bg-sunken), var(--bg-sunken)), var(--bg-row)`(prism
  在 views.css, atlas/console 在 components.css), 修后 Δ0。⚠ console 另有
  `.group-row.expanded:hover { background: var(--bg-sunken) }`(压过行板悬停) —— 不一起改则**悬停
  展开行**那一下又跌回半透明, 首格与行板重新分家; 判据是「凡自带 background 的展开态变体都要同款叠底」。
  **同族拓展(2026-10-30, issue 26-10-30-0818)**: 行语言 flat(ba2a91be)把「同一表达式」弱化成
  「视觉恒等」—— 行板取半透明 tint 叠页底、首格取 color-mix 不透明等价色, 肉眼逐帧一致
  (premultiplied 恒等), 但 e2e 守阵按**计算值**比较(逐帧通道/稳态逐字)即红(atlas 6 例)。
  判据再加一条: **行板与首格要逐字同一个表达式, 「数学上恒等」的另一种写法不算同** —— 恒等
  推导对人不透明, 守阵读的是计算样式。另: prism 例全绿是无头亮主题假象
  (testing/headless-prefers-light-theme-gate), 双皮肤绿≠两面都真正吃到待测规则。
