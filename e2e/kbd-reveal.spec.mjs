// @ts-check
import { expect, test } from '@playwright/test';
import { SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';
import { clickRow, ctxItemById, openApp } from './lib/gestures.mjs';
import { installRouteCleanup } from './lib/route-cleanup.mjs';

/**
 * 键位提示显影链(计划 26-11-14-0041 §09 明确要求的新增用例面; S1/W1 机制 · S7/W7 守阵)。
 *
 * 为什么单独成文件(而非塞进 statusbar-kbd-entry / menus):
 *   本条链的断言面是**全局生命周期**(blur / visibilitychange / 丢 keyup 自愈 / 输入态 /
 *   录制态 / 组合键不吞), 与「状态栏开关两态」和「右键菜单版式」是三条正交的验收面;
 *   statusbar-kbd-entry.spec.mjs 已承载开关两态 + 零几何副作用 + 刷新保留, menus.spec.mjs
 *   已承载菜单键帽版式 / 键位槽对齐 / 零跳动, drawer-merge.spec.mjs 已承载页签徽标显影 +
 *   宽度零跳动 —— 本文件只补**缺口**, 不重复上述断言(下面每条用例注释标了已覆盖项)。
 *
 * 断言口径(与既有 spec 一致): 真实键盘/鼠标手势 + DOM 几何, 不借道 vm; 唯一例外是
 * visibilitychange(hidden) —— Playwright 无「把标签切后台」的原生手势, 按 §08 风险对策
 * 「e2e 补切窗用例」的要求用 defineProperty 改 document.hidden 再派发同名事件(合成 DOM,
 * 断言的是产品监听器本身, 不是浏览器行为)。
 *
 * 每条用例都对准一个**可失效的实现点**(不是摆设):
 *   1. 切窗自愈 —— 删掉 blur / visibilitychange / 自愈任一分支, class 就留在 body 上;
 *      同一条用例末尾还守两态互斥: 删掉 _setKbdReveal 的常驻态早退, 常驻时会多挂 kbd-reveal;
 *   2. 输入态 —— 去掉输入态跳过或误加 preventDefault, 显影 class 亮起 / 字符打不出来;
 *   3. 录制态 —— 录制器丢了捕获段全吞(或 kbRecId 二道防线), 显影 class 亮起;
 *   4. 显影落点 —— 共享 CSS 两态规则或某个角标挂点丢了, 对应键帽显不出来 / 松手不隐;
 *   5. 组合键不吞 —— 显影监听若 preventDefault 或抢在引擎前, 动作整条被跳过(零请求);
 *   6. 组合键不吞(队列+抽屉页签) —— 同上, 落在 Ctrl+Home 的 POST 与 Alt+1/2 的页签切换上。
 */

for (const skin of SKINS) {
  test.describe(`键位提示显影链 ${skin}`, () => {
    installRuntimeErrorGuard(test);
    installRouteCleanup(test);

    test(`切窗自愈: blur / visibilitychange(hidden) / 丢 keyup 后下一次 keydown 纠正 + 常驻态不叠显影 @fast (${skin})`, async ({ page }) => {
      /* I4 四重兜底的三条不可用真实手势构造的(第四条 keyup 由下方 up 直接验):
       *   · 丢 keyup = 按住反引号时 OS 把 up 吞了(Alt+Tab 切窗的经典签名) -> 下一次任意
       *     keydown 必须立即摘 class;
       *   · window blur -> 强制清;
       *   · visibilitychange(hidden) -> 强制清。
       * 任一分支删除, body 上的 kbd-reveal 会一直留着(键帽永久常亮 = 用户报的「卡死」)。 */
      collectRuntimeErrors(page);
      await openApp(page, skin);
      const body = page.locator('body');

      // 前提: 默认关态(仅按住显影), 否则 _setKbdReveal 在常驻态早退, 本用例失去载体
      await expect(body, '默认不常驻(本用例载体 = 仅按住显影)').not.toHaveClass(/kbd-persist/);
      await expect(body).not.toHaveClass(/kbd-reveal/);

      // 1) 丢 keyup 自愈: 按住反引号(进入显影) -> 不松手 -> 按任意其它键 -> class 必须被摘
      await page.keyboard.down('Backquote');
      await expect(body, '按住反引号进入显影态').toHaveClass(/kbd-reveal/);
      await page.keyboard.press('KeyA'); // 任意非反引号 keydown = 自愈触发器
      await expect(body, '丢 keyup 后下一次任意 keydown 立即纠正(I4 自愈)').not.toHaveClass(/kbd-reveal/);
      await page.keyboard.up('Backquote'); // 收口(反引号本身的 up)

      // 2) window blur 兜底
      await page.keyboard.down('Backquote');
      await expect(body).toHaveClass(/kbd-reveal/);
      await page.evaluate("window.dispatchEvent(new Event('blur'))");
      await expect(body, 'window blur 强制清显影 class(I4)').not.toHaveClass(/kbd-reveal/);
      await page.keyboard.up('Backquote');

      // 3) visibilitychange(hidden) 兜底(切后台标签)
      await page.keyboard.down('Backquote');
      await expect(body).toHaveClass(/kbd-reveal/);
      await page.evaluate(`(() => {
        Object.defineProperty(document, 'hidden', { configurable: true, get: () => true });
        document.dispatchEvent(new Event('visibilitychange'));
      })()`);
      await expect(body, 'visibilitychange(hidden) 强制清显影 class(I4)').not.toHaveClass(/kbd-reveal/);
      await page.evaluate('delete document.hidden'); // 还原(不留假 hidden 给后续断言)
      await page.keyboard.up('Backquote');
      await expect(body, '收口: 三条兜底之后仍是关态').not.toHaveClass(/kbd-reveal/);

      /* 4) 两态互斥(S5/W2 的单开关不变式): _setKbdReveal 在常驻态早退(body 上只允许一态,
       * 否则 CSS 与断言会各说一套)。这条分支若无断言, 删掉 `if (on && this._kbdPersistOn) return;`
       * 全仓 e2e 仍绿 —— 常驻用户按住反引号会多挂一个 kbd-reveal。 */
      await page.locator('.statusbar button.sb-kbd-sw').click();
      await expect(body, '开关打开后进入常驻态').toHaveClass(/kbd-persist/);
      await page.keyboard.down('Backquote');
      await expect(body, '常驻态按住反引号不叠加显影 class(两态互斥)').not.toHaveClass(/kbd-reveal/);
      await page.keyboard.up('Backquote');
      await page.locator('.statusbar button.sb-kbd-sw').click(); // 收回常驻(不留态给后续断言)
      await expect(body).not.toHaveClass(/kbd-persist/);
    });

    test(`输入态: 搜索框内按住反引号不显影、字符照常输入、不吞默认行为 @fast (${skin})`, async ({ page }) => {
      /* §03 约束 2 / §08「反引号输入态」: 输入态跳过显影 + 绝不 preventDefault。
       * 断言面 = 显影 class 不亮(键帽不闪) + 输入框真的收到反引号字符(证明没被吞) +
       * 键帽本身保持不可见。去掉输入态判据 -> class 亮 -> 第一条先红; 误加
       * preventDefault -> 字符进不去 -> 第二条红。 */
      collectRuntimeErrors(page);
      await openApp(page, skin);
      const body = page.locator('body');
      const input = page.locator('.top-search input');
      await input.click();
      await expect(input, '搜索框已聚焦(真实手势)').toBeFocused();
      await expect(input).toHaveValue('');

      await page.keyboard.down('Backquote');
      await expect(body, '输入态跳过显影: 键帽不闪(§03 约束 2)').not.toHaveClass(/kbd-reveal/);
      await expect(input, '反引号字符照常输入(不 preventDefault)').toHaveValue('`');
      // 键帽不闪的第二重证据: 显影态键帽与按住期间都不可见
      await expect(page.locator('.topbar .add-btn .aq-kbd'), '输入态按住反引号键帽仍不可见').toBeHidden();
      await page.keyboard.up('Backquote');
      await expect(body, '松手后仍是关态').not.toHaveClass(/kbd-reveal/);

      // 收口: 清掉搜索词(搜索框非空会过滤列表, 不把状态带出本用例)
      await page.locator('.search-clear').click();
      await expect(input).toHaveValue('');
    });

    test(`录制态: 键位面板录制中按住反引号不显影、录制照常收键 @fast (${skin})`, async ({ page }) => {
      /* §03 约束 5 / §08「录制态干扰」: 录制器在捕获段对所有 keydown preventDefault +
       * stopPropagation(shortcuts_panel.js _kbOnRecordKey), 显影监听在冒泡段且再判 kbRecId。
       * 断言面 = 按住反引号时 body 无 kbd-reveal(不误加) + 录制器照常把反引号收为该条新键位
       * (不误清) + 收键后 .rec 摘除。丢捕获段全吞 -> 显影 class 亮 -> 红; 显影链抢在录制器
       * 之前消费按键 -> 键位收不到 -> 文本断言红。收口走「放弃改动」, 草稿只在本页内存。 */
      collectRuntimeErrors(page);
      await openApp(page, skin);

      // 进设置 -> WebUI 卡 -> 快捷键块「展开」= 全屏键位编辑覆盖层
      await page.locator('nav.tabs-right button').first().click();
      await expect(page.locator('.hb-grid .hb-card').first()).toBeVisible({ timeout: 20_000 });
      await page.locator('.hb-card', { hasText: 'WebUI' }).first().click();
      await page.locator('.hb-blk-hd', { hasText: '快捷键' }).locator('button', { hasText: '展开' }).click();
      const modal = page.locator('.hr-full-modal.kb-full');
      await expect(modal, '键位编辑覆盖层展开').toBeVisible({ timeout: 10_000 });

      // 按条目文案定位(不依赖面板分组/条目序 —— 那是注册表排列, 不是本用例的契约)
      const row = modal.locator('.kb-row', { hasText: '切到辅种页' });
      await expect(row, '选一条普通绑定条目(非 fixed)作录制载体').toHaveCount(1);
      await expect(row.locator('.kb-row-keys'), '录前键位 = 1').toHaveText('1');
      await row.locator('button', { hasText: '录制' }).click();
      await expect(row, '进入录制态(.rec)').toHaveClass(/rec/);
      await expect(modal.locator('.kb-rec-tip'), '录制提示可见').toBeVisible();

      await page.keyboard.down('Backquote');
      await expect(page.locator('body'), '录制中按住反引号不得点亮显影 class(捕获段 + kbRecId 双保险)')
        .not.toHaveClass(/kbd-reveal/);
      await page.keyboard.up('Backquote');

      await expect(row.locator('.kb-row-keys'), '录制照常收键: 反引号成为该条新键位(显示串 = 反引号)')
        .toHaveText('`');
      await expect(row, '收键后退出录制态').not.toHaveClass(/rec/);
      await expect(page.locator('body'), '整个录制过程未留显影 class').not.toHaveClass(/kbd-reveal/);

      // 收口: 放弃试用稿(内存态), 不 PUT /api/keys
      await modal.locator('button', { hasText: '放弃改动' }).click();
      await expect(row.locator('.kb-row-keys'), '放弃改动后键位回落到模板基准').toHaveText('1');
    });

    test(`显影落点: 顶栏 7 处 + 菜单一级/次级 随显影出现、松手全隐 @fast (${skin})`, async ({ page }) => {
      /* I1 取数单点 + 两态显示规则(body.kbd-reveal 与 body.kbd-persist 共用同一块)的浏览器面。
       * 既往已覆盖(不重复): 状态栏开关钮键帽两态 statusbar-kbd-entry.spec; 抽屉页签徽标显影 +
       * 宽度零跳动 drawer-merge.spec; 菜单键位槽逐行对齐 / 文字零位移 menus.spec。
       * 本用例只补缺口: 顶栏 7 处(三视图页签 / 添加种子 / 列 / 搜索框 / 设置)与菜单一级+次级
       * 键帽在**显影态**下真的出现(此前只在常驻态或菜单结构面被断言过)。删掉共享显示规则
       * 或任一角标挂点 -> 对应 toBeVisible 红; 松手不清 -> 最后一批 toBeHidden 红。 */
      collectRuntimeErrors(page);
      await openApp(page, skin);
      const body = page.locator('body');

      /** 顶栏七处: 选择器 + 注册表现算显示串(逐条对账 I1, 不是模板手抄)。 */
      const topKeys = [
        ['.topbar nav.tabs [data-view="groups"] .aq-kbd', '1', '视图页签 view-groups'],
        ['.topbar nav.tabs [data-view="torrents"] .aq-kbd', '2', '视图页签 view-torrents'],
        ['.topbar nav.tabs [data-view="shows"] .aq-kbd', '3', '视图页签 view-shows'],
        ['.topbar .add-btn .aq-kbd', 'N', '添加种子 add-torrent'],
        ['.topbar .col-picker .aq-kbd', 'K', '列选择器 col-picker'],
        ['.top-search .aq-kbd', '/', '搜索框 focus-search'],
        ['.topbar .tabs-right button .aq-kbd', 'Ctrl + ,', '设置 open-settings'],
      ];
      for (const [sel, text, name] of topKeys) {
        await expect(page.locator(sel), `默认隐藏: ${name}`).toBeHidden();
      }
      await page.keyboard.down('Backquote');
      await expect(body).toHaveClass(/kbd-reveal/);
      for (const [sel, text, name] of topKeys) {
        await expect(page.locator(sel), `显影态可见: ${name}`).toBeVisible();
        await expect(page.locator(sel), `显影态显示串(注册表现算): ${name}`).toHaveText(text);
      }
      await page.keyboard.up('Backquote');
      for (const [sel, text, name] of topKeys) {
        await expect(page.locator(sel), `松手全隐: ${name}`).toBeHidden();
      }

      // 菜单一级 + 次级(种子页 member 菜单): 菜单项键帽同样只在显影态出现
      await page.click('nav.tabs [data-view="torrents"]');
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
      await clickRow(page, page.locator('.torrent-row').nth(0), { button: 'right' });
      await expect(page.locator('.ctx-menu')).toBeVisible({ timeout: 5_000 });
      const primaryKbd = ctxItemById(page, 'reannounce').locator('.aq-kbd');
      await expect(primaryKbd, '菜单键帽默认隐藏').toBeHidden();
      await page.keyboard.down('Backquote');
      await expect(primaryKbd, '显影态菜单一级键帽可见').toBeVisible();
      await expect(primaryKbd).toHaveText('Shift + A');
      await page.locator('.ctx-menu > .ctx-item.has-sub[data-item="sub-more"]').hover();
      const subMore = page.locator('.ctx-menu > .ctx-item.has-sub[data-item="sub-more"] > .ctx-sub');
      const subKbd = subMore.locator('.ctx-item[data-item="copy-name"] .aq-kbd');
      await expect(subKbd, '显影态菜单次级键帽可见').toBeVisible({ timeout: 3_000 });
      await expect(subKbd).toHaveText('Shift + C');
      await page.keyboard.up('Backquote');
      await expect(primaryKbd, '松手后菜单一级键帽隐藏').toBeHidden();
      await expect(subKbd, '松手后菜单次级键帽隐藏').toBeHidden();
      await page.keyboard.press('Escape');
      await expect(page.locator('.ctx-menu')).toHaveCount(0);
    });

    test(`显影落点 + 组合键: 设置保存键帽随显影出现, Ctrl+S 动作照常 @fast (${skin})`, async ({ page }) => {
      /* S6/W6 表 B 的 settings-save 落点(此前只在守阵静态面被断言) + §03 约束「不吞」在
       * 设置 scope 上的实证: settings-save 是 inputSafe 条目, 显影链若 preventDefault,
       * 引擎 defaultPrevented 早退 -> PUT /api/config 不发 -> 本用例红。
       * PUT 用 page.route 拦下(不落盘, 不碰 config.yml), GET 照常透传(保存后会重拉树)。 */
      collectRuntimeErrors(page);
      const puts = [];
      await page.route('**/api/config', async (route) => {
        if (route.request().method() === 'PUT') {
          puts.push(route.request().postData() || '');
          return route.fulfill({ json: { changes: [], restart_required: [] } });
        }
        return route.continue();
      });
      await openApp(page, skin);
      await page.locator('nav.tabs-right button').first().click();
      await expect(page.locator('.hb-grid .hb-card').first()).toBeVisible({ timeout: 20_000 });

      const saveKbd = page.locator('.hb-actbar .hb-btn.primary .aq-kbd');
      await expect(saveKbd, '保存键帽现算显示串(注册表 settings-save)').toHaveText('Ctrl + S');
      await expect(saveKbd, '默认隐藏').toBeHidden();
      await page.keyboard.down('Backquote');
      await expect(saveKbd, '显影态保存键帽可见').toBeVisible();
      await page.keyboard.up('Backquote');
      await expect(saveKbd, '松手隐藏').toBeHidden();

      // Ctrl+S: 显影链不吞 -> 引擎照常跑 cfgSave -> PUT /api/config + 保存回执 toast
      await page.keyboard.press('Control+KeyS');
      await expect.poll(() => puts.length, { message: 'Ctrl+S 未发出 PUT /api/config(动作被显影链吞掉)', timeout: 10_000 }).toBe(1);
      await expect(page.locator('.toast', { hasText: '已保存' }).first(), '保存回执 toast 可见').toBeVisible({ timeout: 10_000 });
      await expect(page.locator('body'), '组合键不触发显影态').not.toHaveClass(/kbd-reveal/);
    });

    test(`组合键不吞: Alt+1/2 抽屉页签 + Ctrl+Home 队列顶部 @fast (${skin})`, async ({ page }) => {
      /* §08「组合键被吞」+ §05 S1 验收判据点名 Ctrl+Home / Alt+1..5:
       * 显影监听注册在引擎之后、冒泡段、且对非反引号按键只做自愈早退(不 preventDefault) ——
       * 这里用**动作真的发生了**作证据, 不看 DOM 类:
       *   · Alt+1 开抽屉到「常规」/ Alt+2 切到「Tracker」(注册表 drawer-tab-*);
       *   · Ctrl+Home 对单目标发队列顶部命令(POST /api/torrents/<hash>/queue, body action=top)。
       * 任一处被吞 -> 页签不动 / 零请求 -> 红。宽视口 = 停靠抽屉的门(与 drawer-merge 同值)。 */
      collectRuntimeErrors(page);
      await page.setViewportSize({ width: 2560, height: 1200 });
      await openApp(page, skin);
      const body = page.locator('body');
      await page.click('nav.tabs [data-view="torrents"]');
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
      await page.keyboard.press('ArrowDown'); // 光标落到首行 = 抽屉页签的目标解析依据

      // Alt+1 -> 抽屉打开并停在「常规」; Alt+2 -> 切到「Tracker」
      await page.keyboard.press('Alt+Digit1');
      const drawer = page.locator('.drawer-dock > .drawer');
      await expect(drawer, 'Alt+1 打开详情抽屉(显影链不阻断)').toBeVisible({ timeout: 8_000 });
      await expect(drawer.locator('.drawer-tabs button.active'), 'Alt+1 落在常规页签').toContainText('常规');
      await page.keyboard.press('Alt+Digit2');
      await expect(drawer.locator('.drawer-tabs button.active'), 'Alt+2 切到 Tracker 页签').toContainText('Tracker');

      // Ctrl+Home -> 队列顶部命令真的发出(动作面证据, 不看 toast 文案)
      const queueReq = page.waitForRequest(
        (r) => r.method() === 'POST' && /\/api\/torrents\/[^/]+\/queue$/.test(new URL(r.url()).pathname),
        { timeout: 10_000 },
      );
      await page.keyboard.press('Control+Home');
      const req = await queueReq;
      expect(JSON.parse(req.postData() || '{}'), 'Ctrl+Home 载荷 = 队列顶部').toEqual({ action: 'top' });
      await expect(body, '组合键不点亮显影 class').not.toHaveClass(/kbd-reveal/);
    });
  });
}
