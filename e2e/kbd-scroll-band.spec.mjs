// @ts-check
import { expect, test } from '@playwright/test';
import { BASE_URL, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';

/**
 * 键盘滚动跟随的可见带: 首个 / 末个种子必须**完整可见**(2026-10-09 用户报「键盘移动光标到
 * 第一个种子, 第一个种子只显示一半, 最后一个种子同理」)。
 *
 * 为什么必须有这条浏览器断言: 缺陷形态是「几何在视口内 ≠ 看得见」—— 静态守阵
 * (tests/test_web_shortcuts.py::test_kb_view_band_single_points)只能钉「上下界各有一个单点且被
 * 消费」, 探不到落点算错: 旧 `_kbScrollRowIntoView` 拿顶栏高当**上界**(漏了吸在顶栏下缘、盖住
 * 列表首行的吸顶列头 .group-head)、拿 window.innerHeight 当**下界**(漏了底部固定状态栏
 * .statusbar) —— 两条算式单看都对。真机指纹(修复前取证, 1440x900, 桩 300 种子 × windowing):
 *   prism · End  末行 bottom=887 > 状态栏 top=866 → 遮 21px / 行高 44
 *   prism · Home 首行 top=103  < 列头 bottom=126   → 遮 23px / 行高 71(矮行时过半)
 *   atlas · End 遮 16px / Home 遮 28px —— 两皮肤同病(chrome 高度随皮肤与内容变, 关系不变)。
 *
 * 断言口径: 按键走真实 keyboard(Home / End = 跳到首行 / 末行, 与用户报障同一条路径: 先 End
 * 沉到库里再 Home 回顶), 判据 = 光标行矩形与列头底缘 / 状态栏顶缘**零重叠**(留 1px 取整余量),
 * 且光标确实落在列表首/末行(data-hash 与窗口化渲染窗口的首/末行同值 —— 否则「没被遮」可能只是
 * 光标没走到极值行, 断言会退化成恒真)。
 *
 * 2026-10-09 第二轮(同一可见带专题): PageUp / PageDown 的「一屏」也必须按可见带算 —— 旧写法取
 * window.innerHeight, 而可见带已被顶栏/列头/状态栏/停靠面板吃掉一截: 实测 1440x900 桩 300 种子,
 * 面板关 可见带 739px(屏内 10~11 行) 而一屏前进 12 行(每屏跳 1 行); **面板开 可见带只剩 353px
 * (屏内 6 行) 而一屏仍前进 12 行 ⇒ 每翻一屏静默跳过 6 行**。判据 = 不跳行不变式: 前进量 ≤ 屏内
 * 可见行数 +1(取整余量), 面板关/开两档各测一遍。
 */

/** 读一次可见带 + 光标行几何(px 取整)。窗口化下只量渲染出来的行, 与用户所见同源。 */
const readBand = (page) =>
  page.evaluate(() => {
    const box = (el) => {
      if (!el) return null;
      const r = el.getBoundingClientRect();
      return { top: Math.round(r.top), bottom: Math.round(r.bottom), h: Math.round(r.height) };
    };
    const rows = [...document.querySelectorAll('.torrent-row')];
    const cur = document.querySelector('.torrent-row.kb-cursor');
    return {
      head: box(document.querySelector('.group-head')),
      sb: box(document.querySelector('.statusbar')),
      cur: box(cur),
      curHash: cur ? cur.getAttribute('data-hash') : null,
      firstHash: rows.length ? rows[0].getAttribute('data-hash') : null,
      lastHash: rows.length ? rows[rows.length - 1].getAttribute('data-hash') : null,
    };
  });

/**
 * 读一次「一屏」相关的三个量: 光标行号 / 可见带 / 屏内可见行数。
 * vm 内部读数属 D4 允许的第②类(filteredTorrents 与 kbCursor 没有 DOM 之外的取径; 可见带是
 * 两个内部单点); 行号取列表顺序里的下标, 与 _kbMove 的前进量同口径。
 */
const readPageState = (page) =>
  page.evaluate(() => {
    const vm = document.querySelector('#app')._vnode.component.proxy;
    const vTop = vm._kbViewTop();
    const vBot = vm._kbViewBottom();
    const visible = [...document.querySelectorAll('.torrent-row')].filter((el) => {
      const r = el.getBoundingClientRect();
      return r.bottom > vTop && r.top < vBot;
    }).length;
    const list = vm.filteredTorrents || [];
    const cur = vm.kbCursor;
    return {
      idx: cur ? list.findIndex((m) => m.hash === cur.id) : -1,
      band: Math.round(vBot - vTop),
      visible,
    };
  });

/** 等滚动落定(翻页是 nextTick 里发的滚动 + 窗口化重渲染, 不等待会把中间态读数当结果)。 */
const settleScroll = async (page) => {
  let prev = '';
  for (let i = 0; i < 40; i++) {
    const sig = await page.evaluate(
      () => `${Math.round(window.scrollY)}:${Math.round(document.querySelector('.kb-cursor')?.getBoundingClientRect().top ?? -1)}`,
    );
    if (sig === prev) return;
    prev = sig;
    await page.waitForTimeout(50);
  }
};

for (const skin of SKINS) {
  test.describe(`键盘滚动跟随可见带 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test(`Home / End 到首末行都不被吸顶列头 / 状态栏遮住 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);

      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      // 种子页平铺列表(用户报障所在视图; 也是行窗口化生效的视图 = 前缀和落点那条路)
      await page.click('nav.tabs [data-view="torrents"]');
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });

      /**
       * 等「光标落在极值行」且「该行完全避开上下 chrome」两件事同时成立 —— 滚动发生在
       * $nextTick(类名先落到 DOM、滚动随后), 不轮询会把中间态读成红。
       * 返回值: 0 = 已落定; -1 = 光标还没到极值行; >=2 = 到极值行了但仍被遮这么多 px。
       */
      const pollBand = async (extreme) => {
        const last = extreme === 'last';
        const probe = async () => {
          const b = await readBand(page);
          if (!b.cur) return { at: false, overlap: 999 };
          const at = b.curHash === (last ? b.lastHash : b.firstHash);
          const overlap = Math.round(last ? Math.max(0, b.cur.bottom - b.sb.top) : Math.max(0, b.head.bottom - b.cur.top));
          return { at, overlap };
        };
        try {
          await expect
            .poll(
              async () => {
                const r = await probe();
                if (!r.at) return -1;
                return r.overlap <= 1 ? 0 : r.overlap; // 1px = 取整余量
              },
              { timeout: 5_000 },
            )
            .toBe(0);
        } catch {
          // 超时把实测几何原样带出来(哪一路错、遮了多少 px) —— 静态守阵全绿而真机必红是这类
          // 缺陷的常态, 红在没有数字的断言消息上等于没取证(dock-panel 坑档同款教训)。
          const b = await readBand(page);
          const r = await probe();
          throw new Error(
            `${last ? '末行(End)' : '首行(Home)'} 未落定: 光标${r.at ? '已' : '未'}到极值行, ` +
              `光标行=${b.cur ? `${b.cur.top}~${b.cur.bottom}(h${b.cur.h})` : '未渲染'}, ` +
              `吸顶列头底=${b.head.bottom}, 状态栏顶=${b.sb.top}, 被 chrome 遮=${r.overlap}px`,
          );
        }
        return probe();
      };

      // --- End: 沉到最后一个种子(末行不得压进底部固定状态栏 --statusbar-h=34px) ---
      await page.keyboard.press('End');
      await pollBand('last');
      const bot = await readBand(page);
      expect(bot.curHash, 'End 必须把光标落到列表末行(否则"没被遮"只是光标没走到极值行)').toBe(bot.lastHash);
      expect(
        bot.cur.bottom,
        `末行底缘压进固定状态栏 ${bot.cur.bottom - bot.sb.top}px(状态栏 top=${bot.sb.top}, 行 bottom=${bot.cur.bottom}, 行高 ${bot.cur.h})`,
      ).toBeLessThanOrEqual(bot.sb.top + 1);

      // --- Home: 回到第一个种子(首行不得被吸在顶栏下缘的列头盖住) ---
      await page.keyboard.press('Home');
      await pollBand('first');
      const top = await readBand(page);
      expect(top.curHash, 'Home 必须把光标落到列表首行').toBe(top.firstHash);
      expect(
        top.cur.top,
        `首行顶缘被吸顶列头盖住 ${top.head.bottom - top.cur.top}px(列头 bottom=${top.head.bottom}, 行 top=${top.cur.top}, 行高 ${top.cur.h})`,
      ).toBeGreaterThanOrEqual(top.head.bottom - 1);
    });

    test(`PageUp / PageDown 一屏不超过屏内可见行数(不跳行; 面板开着同样) @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);

      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      await page.click('nav.tabs [data-view="torrents"]');
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });

      /**
       * 翻一屏: 从 Home 起算, 返回「本屏可见行数 / 光标前进量」。
       * 判据(不跳行不变式): 前进量 ≤ 屏内可见行数 +1(取整余量) —— 超了说明这一屏跳过了
       * 屏幕上从未出现过的行(修复前按 window.innerHeight 算一屏: 面板关 12 > 10, 面板开 12 > 6)。
       * 行高 71px 下 +1 余量足够, 而修复前两种情形的越界量都远大于 1 ⇒ 判据不虚。
       */
      const pageTurn = async () => {
        await page.keyboard.press('Home');
        await settleScroll(page);
        const before = await readPageState(page);
        await page.keyboard.press('PageDown');
        await settleScroll(page);
        const after = await readPageState(page);
        return { before, after, advance: after.idx - before.idx };
      };

      // --- 面板关(可见带 739px) ---
      const p1 = await pageTurn();
      expect(p1.after.idx, 'Home 后 PageDown 必须真的前进(光标行号要变大)').toBeGreaterThan(p1.before.idx);
      expect(
        p1.advance,
        `面板关: 一屏前进 ${p1.advance} 行 > 屏内可见 ${p1.before.visible} 行(+1 余量) ⇒ 这一屏跳过了看不见的行(可见带 ${p1.before.band}px)`,
      ).toBeLessThanOrEqual(p1.before.visible + 1);

      // --- 面板开(可见带被面板顶缘压窄) —— 缺陷最重的一档: 屏内只剩几行而一屏仍按整窗高算 ---
      await page.keyboard.press('Home');
      await settleScroll(page);
      await page.dblclick('.torrent-row >> nth=0', { force: true }); // force: 整表 2s 重渲染抢点击(smoke.md)
      await expect(page.locator('.drawer-dock > .drawer')).toBeVisible({ timeout: 5_000 });
      await page.waitForTimeout(800); // 面板长到自然高后可见带才落定
      const p2 = await pageTurn();
      expect(
        p2.advance,
        `面板开: 一屏前进 ${p2.advance} 行 > 屏内可见 ${p2.before.visible} 行(+1 余量) ⇒ 可见带被面板压窄后仍在按整窗高翻页(可见带 ${p2.before.band}px)`,
      ).toBeLessThanOrEqual(p2.before.visible + 1);
      expect(p2.before.visible, '面板开着时可见带必须明显变窄(否则本档没测到重点)').toBeLessThan(p1.before.visible);
    });
  });
}
