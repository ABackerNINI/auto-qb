// @ts-check
/**
 * 流量步进 SSE 事件泵助手(plan 26-11-18-0037 阶段 3 e2e 面)。
 *
 * 桩侧单点 = scripts/ui_harness.py::_install_traffic_stream_probe(POST /__harness__/traffic_stream,
 * start/stop/status 三形态): 泵把每 tick 显示点真值按到生产同一发布点(WebUIRuntime.
 * publish_traffic_batch), 帧走真 /api/traffic/qb/stream 线(票据/心跳/seq/扇出全真)。
 * e2e 只负责: pumpT0(si) 算好 t0(锚当前墙钟)后开泵、等流 live、按需停泵。
 *
 * 时序纪律: 泵首帧**立即落** —— 必须先等流 live(waitStreamLive)再 pumpStart, 否则首帧
 * 扑空(无订阅者时 publish 静默丢弃, hub 契约: 静默是停流信号, seq 不虚增)。steps=0 不限
 * 泵量, ttl_s(默认 45s)安全自停; start 自带顶槽(单泵, 上一用例残留自动清)。
 *
 * t0 口径(评审 T4b #1, 锚墙钟单点 pumpT0): t0 = floor(now/si)*si + si —— 首帧 t = 当前
 * si 网格的下一格: 恒 > GET 桩列末 colEnd(colEnd <= 桩安装时刻 <= now < t0) => _qbStream
 * Append 恒走追加分支, 显示列 = GET 组点列 + 事件尾点; 且事件 lastT 跟住墙钟 —— 前端
 * watchdog(D9: lastT 落后墙钟 >3x si 立即 GET 重拉)与「滞后 Ns」徽标量纲不误触发。旧
 * 「锚桩安装时刻 colEnd + si」在慢环境(建桩->开泵耗时 >3x si)下 lastT 落后墙钟超阈:
 * 徽标案「来帧期 toBeHidden」假红; 泵案经 watchdog 重拉沿 tail 归并产出与停推前逐位相同
 * 列 -> 零变化拍段 spawn 非空 -> per-run 断言假红(两面同修, 断言面过滤见各 spec)。
 */

import { expect } from '@playwright/test';
import { baseUrl } from '../harness.mjs';
import { readInst } from './vm.mjs';

/** 泵数值缺省(与桩端点 up/dl 缺省一致: 1000/2000; si 无缺省 —— pumpStart 必传, 桩端点的
 * si=1.5 缺省只服务手工调用; 快拍档各案显式传 si) */
export const PUMP_UP_DEFAULT = 1000;
export const PUMP_DL_DEFAULT = 2000;

/**
 * 泵 t0 锚(墙钟, 评审 T4b #1 单点): t0 = floor(now/si)*si + si —— 首帧 t = 当前 si 网格的
 * 下一格, 恒 > GET 桩列末 colEnd 且事件 lastT 跟住墙钟(口径详见文件头 t0 口径注)。
 * @param {number} si 帧间隔秒(与 pumpStart 的 si 同值)
 * @returns {number} 首帧 epoch 秒
 */
export function pumpT0(si) {
  return Math.floor(Date.now() / 1000 / si) * si + si;
}

/**
 * 开泵(start 顶槽)。si/t0 必传: si = 帧间隔秒(也是每帧 t 的步进), t0 = 首帧 epoch 秒
 * (调用点一律 pumpT0(si) 锚当前墙钟 —— 见文件头 t0 口径注)。
 * @param {import('@playwright/test').APIRequestContext} request
 * @param {{scope: string, si: number, t0: number, steps?: number, up?: number, dl?: number, ttl?: number}} cfg
 */
export async function pumpStart(request, cfg) {
  const res = await request.post(baseUrl() + '/__harness__/traffic_stream', {
    params: {
      mode: 'start',
      scope: cfg.scope,
      si: cfg.si,
      t0: cfg.t0,
      steps: cfg.steps ?? 0,
      up: cfg.up ?? PUMP_UP_DEFAULT,
      dl: cfg.dl ?? PUMP_DL_DEFAULT,
      ttl_s: cfg.ttl ?? 45,
    },
  });
  if (!res.ok()) throw new Error('traffic pump start failed: HTTP ' + res.status() + ' ' + (await res.text()));
  const body = await res.json();
  if (body && body.ok === false) throw new Error('traffic pump start rejected: ' + JSON.stringify(body));
  return body;
}

/** 停泵(幂等; 用例收尾不必显式调 —— ttl 自停兜底, 这里供需要精确停推时点的用例) */
export async function pumpStop(request) {
  const res = await request.post(baseUrl() + '/__harness__/traffic_stream', {
    params: { mode: 'stop' },
  });
  if (!res.ok()) throw new Error('traffic pump stop failed: HTTP ' + res.status());
  return res.json().catch(() => null);
}

/**
 * 泵状态(status): {running, scope, si, steps, pushed, last_t, last_push_at, last_hit, subs}。
 * last_push_at = 末次 publish 墙钟秒(time.time) —— 渲染延迟断言的「样本落地」时刻;
 * last_hit = 末次 publish 送达的订阅队列数(0 = 无订阅者, 帧被静默丢弃); subs = 订阅队列总数。
 */
export async function pumpStatus(request) {
  const res = await request.post(baseUrl() + '/__harness__/traffic_stream', {
    params: { mode: 'status' },
  });
  if (!res.ok()) throw new Error('traffic pump status failed: HTTP ' + res.status());
  return res.json();
}

/**
 * 等 SSE 流进 live 态(T4a 状态机: connecting -> live; 票据/握手失败卡 connecting 即超时红)。
 * 泵必须在本断言通过后再开 —— 见文件头时序纪律。
 * @param {import('@playwright/test').Page} page
 * @param {string} scope —— vm._qbStreams 的键: torrent | global | group
 */
export async function waitStreamLive(page, scope = 'torrent') {
  await expect.poll(() => readInst(page,
    `vm._qbStreams && vm._qbStreams.${scope} ? vm._qbStreams.${scope}.state : null`), {
    message: 'SSE 流未进 live(T4a connecting -> live 链路断了: 票据/握手/开流任一环)',
    timeout: 15_000,
  }).toBe('live');
}
