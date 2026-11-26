"""test_webui_config_normalize_parity 测试计划: 前端 cfgNormalize* 与后端 compat 规范化的跨语言对拍守卫
(issue 26-11-03-1120-test-webui-config-normalize-parity-gap)

`config_rules.js` 的 `cfgNormalize*` 是 `config/compat.py` 的 `normalize_*` 的**手抄镜像** ——
打开设置页显示的即归一形, 保存即写新形态, 两侧语义必须逐位等价。此前两侧各有独立的期望
电池(Python 侧 pytest / JS 侧 DOM 电池手写期望), 任一侧改语义都不会让另一侧红。本文件把
同一批 `PARITY_CASES` 同时喂两侧, 断言输出 JSON 等价。

无 node 的机器只跑 Python 侧基线(与 `test_webui_static_dom_page_layout.py` 的 node 探针同
口径, 不引入 pytest skip)。

## 测试计划(每个测试函数一条)
- test_python_side_idempotent: Python 侧基线 —— 每例 `normalize_legacy_rule` 幂等, 输入 spec
  不被就地改写(对拍前提: Python 侧输出是稳定且有判别力的金标准)
- test_python_side_effective: Python 侧基线 —— 对拍清单确实覆盖了归一语义(至少一例扁平动作
  被翻译成规范形 + 至少一例 choose 键面保留), 防清单被退化成"输入即输出"
- test_js_python_parity: 跨语言对拍 —— 有 node 时, 同一批 spec 走 `cfgNormalizeRulesDraft`
  后 dump 回 stdout, 与 `python_normalize` 逐例比对; 无 node 只守电池进场与清单非空
"""

import copy

import json

import os

import shutil

import subprocess

from config_normalize_parity_support import (
    PARITY_CASES,
    _NODE_PARITY_PROBE,
    cases_json,
    python_normalize,
)

from webui_helpers import STATIC_ROOT, bundle_file


def test_python_side_idempotent():
    """Python 侧基线: 幂等 + 输入不被就地改写(对拍金标准的前提)"""
    for cid, spec in PARITY_CASES:
        tmp = copy.deepcopy(spec)
        once = python_normalize(spec)
        twice = python_normalize(once)
        assert twice == once, f"{cid}: 后端 normalize 不幂等"
        assert spec == tmp, f"{cid}: 后端 normalize 就地改写了输入(对拍电池的期望会随之漂移)"


def test_python_side_effective():
    """Python 侧基线: 清单真的走到归一分支(不是一批原样透传的空转 case)"""
    flat = python_normalize({"actions": [{"add_tags": ["x"]}]})
    assert flat["actions"] == [{"type": "add_tags", "params": ["x"], "on_error": {"policy": "stop", "retries": 3, "backoff": 60}}], \
        "扁平动作未被翻译成规范形 —— 对拍金标准退化"
    choose = python_normalize(
        {"actions": [{
            "choose": [{
                "when": [],
                "then": [{
                    "add_tags": ["T"]
                }]
            }],
            "default": [{
                "add_tags": ["D"]
            }]
        }]}
    )
    assert "choose" in choose["actions"][0] and "default" in choose["actions"][0], "choose 键面未保留"
    conds = python_normalize({"conditions": [{"size": ">=1MiB"}]})
    assert conds["conditions"] == {"all": [{"size": ">=1MiB"}]}, "扁平条件未包隐式 all"


def test_js_python_parity():
    """跨语言对拍: 同一批 spec 两侧归一输出逐例等价"""
    node = shutil.which("node")
    if not node:
        # 无 node 的环境只守"镜像在场 + 清单非空", 与 DOM 电池同口径
        js = open(os.path.join(STATIC_ROOT, "shared", "config_rules.js"), encoding="utf-8").read()
        assert "cfgNormalizeRulesDraft()" in js, "config_rules.js 缺 cfgNormalizeRulesDraft(镜像被删? 同步本守阵)"
        assert PARITY_CASES, "对拍清单为空 —— 本守阵退化成恒真"
        return
    proc = subprocess.run(
        [
            node,
            "-e",
            _NODE_PARITY_PROBE,
            bundle_file("config_editor.js"),
            os.path.join(STATIC_ROOT, "shared", "config_rules.js"),
            cases_json(),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, f"node 对拍电池跑挂了: {(proc.stderr or '').strip()[:400]}"
    js_out = json.loads(proc.stdout.strip() or "{}")
    assert set(js_out) == {cid for cid, _ in PARITY_CASES}, "JS 侧返回的用例不足(电池被删减? 同步本守阵)"
    bad = []
    for cid, spec in PARITY_CASES:
        # 两侧拿到结构相同的输入(JS 侧经 JSON 往返, 用 Python 侧 deepcopy 对齐深拷贝语义)
        want = python_normalize(copy.deepcopy(spec))
        got = js_out[cid]
        if got != want:
            bad.append(
                f"{cid}\n   JS = {json.dumps(got, ensure_ascii=False, sort_keys=True)}"
                f"\n   PY = {json.dumps(want, ensure_ascii=False, sort_keys=True)}"
            )
    assert not bad, "前端 cfgNormalize* 与后端 compat 归一语义漂移:\n" + "\n".join(bad)
