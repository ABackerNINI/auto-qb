# 压缩产物上的脱敏断言必须解压后扫文本(.gz 原始字节子串匹配会假绿)

> 摘要: 对 .gz 原始字节做子串断言恒真, 必须解压后扫文本再验内容
> 触发: gz,压缩产物,脱敏断言,假绿,no_credentials
**Refs:** memory-bank/issues/26-11-03-1144-bug-qb-capture-fs-delta-sanitize.html

### 对 `.gz` 原始字节做 `in` 子串断言 = 恒真假绿

- **触发**: 断言「真 infohash / 真文件名 / 凭据没落进 `*.json.gz` / `*.jsonl.gz`」时，直接读 `Path(...).read_bytes()` 再 `assert b"真名" not in raw`。gzip 是压缩流，明文本来就不以字面字节出现，断言永远通过；而 `no_credentials` 扫描又跳过 `.gz`(qb_capture.py 凭据扫描只查明文产物)，两处都拦不住真实泄漏。
- **判别**: 断言「删掉脱敏代码也照样绿」——典型信号是把被测行为改回未脱敏，测试仍 100% 通过；或断言只对 `.gz` 用字节匹配，同文件里却又有 `gzip.open(...).read()` 的文本读取可用。
- **处置**: 走 `with gzip.open(path, "rt", encoding="utf-8") as fh: txt = fh.read()`，再对 `txt` 做字符串子串与 `json.loads` 结构断言；字节级只用来验 gzip magic/完整性，不用来验内容。落盘型泄漏断言至少两条：解压文本零命中 + 结构键已伪名化(外层 hash 在 files_map、内层 rel 在 files name 集合)。
- **守阵**: `tests/test_qb_capture.py::test_write_corpus_end_to_end_minimal`(解压后 `raw_txt` 零真值) + `test_sanitize_all_rewrites_fs_delta_with_same_derivation`(同源派生断言)
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)
