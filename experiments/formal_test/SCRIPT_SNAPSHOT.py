#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TinyLearner v1.56.2 — LC-QuAD 2.0 Formal Integrated TEST
Python 3.11

Scientific goal
---------------
Test the already-proven learned ENTITY and PROPERTY skills together in one
end-to-end Tiny execution chain on a genuinely formal TEST subset:

  question
    -> robust exact entity candidates
    -> entity scorer + frozen property-evidence reranking
    -> frozen ENTITY competence gate
    -> real Qwen fallback only when Tiny declines
    -> resolved subject entity
    -> subject-conditioned property resolver
    -> frozen PROPERTY consensus gate
    -> real Qwen fallback only when Tiny declines
    -> (subject QID, property PID)

Two complete branches are run on the SAME rows:
  BASELINE = base entity model + base property model
  LEARNED  = learned entity model v1.53.6 + learned property model v1.54.2b

The entity evidence semantics are kept frozen to the original base property
semantic model in BOTH branches. This preserves the proven entity competence
policy context; the learned property model is introduced only at the downstream
property-mapping stage where its effect was independently validated.

Formal source
-------------
Official LC-QuAD 2.0 TEST. PREREG_TEST.json is written BEFORE this split is
downloaded or parsed. The formal claim is scoped to a frozen structural subset.

Evaluation eligibility is frozen BEFORE TEST access:
- natural English question is non-empty
- exactly one distinct wd:Q... constant in sparql_wikidata
- exactly one distinct direct wdt:P... property in sparql_wikidata
- exactly one explicit direct triple wd:Q... wdt:P... ?variable
- PID exists in the frozen 13,830-property catalog
- PID is present in the pinned TinyMemory property set of the gold subject
- ALL qualifying TEST rows are used; there is no model-based subset selection

Gold QID/PID are used ONLY to apply this frozen structural eligibility rule and
are immediately written to GOLD_SEALED.jsonl. All model ranking, competence
policy and Qwen inference are then executed from TEST_INPUTS_PRE_GOLD.jsonl,
which contains only id/question/sample_key. GOLD_SEALED is reloaded only after
ALL baseline + learned entity/property teacher passes have completed and Qwen
has been deleted.

No training, threshold tuning or checkpoint selection occurs. LC-QuAD 2.0 TEST
is intentionally opened once, only after preregistration. Mintaka TEST,
SimpleQuestions TEST and QALD-10 TEST remain unopened.

PRIMARY PASS (all required)
---------------------------
- at least 100 structurally eligible TEST rows
- robust-exact entity candidate recall >= 0.60
- learned real Qwen calls/question <= baseline - 0.05
- learned end-to-end exact (subject, property) hybrid accuracy is no more than
  1.0 percentage point below baseline
- learned autonomous zero-call pair precision >= 0.85 with >=20 such rows
- all hygiene/integrity guardrails pass

STRONG PASS
-----------
- calls/question reduction >= 0.10
- learned hybrid pair accuracy >= baseline
- learned autonomous zero-call pair precision >= 0.90 with >=40 such rows
- all PRIMARY integrity guardrails pass

If PRIMARY passes, formal integrated confirmation is complete and the result
is frozen. If PRIMARY fails, report the failure and do not tune or rerun on
LC-QuAD 2.0 TEST.
"""

from __future__ import annotations

import argparse
import ast
from collections import defaultdict
from datetime import datetime, timezone
import gc
import hashlib
import json
import os
from pathlib import Path
import py_compile
import re
import shutil
import statistics
import sys
import tempfile
import time
import traceback
import unicodedata
import urllib.request
from typing import Any, Iterable

VERSION = "TinyLearner-v1.56.2-lcquad2-formal-integrated-test"
EXPERIMENT = "v1562_lcquad2_formal_integrated_test"

ROOT = Path(r"C:\TinyLearner")
RESULTS = ROOT / "results"
OUTPUT = RESULTS / EXPERIMENT

TINYMEMORY = Path(r"D:\TinyMemory\wikidata_20260817_v2")
STATEMENT_ACCEL = Path(r"D:\TinyMemory\wikidata_20260817_v2_accel_v1483")
ENTITY_ACCEL = Path(r"D:\TinyMemory\wikidata_20260817_v2_entity_accel_v1491")

DRIVE_ROOT_CANDIDATES = [
    Path(r"G:\Мой диск\Tiny"),
    Path(r"G:\My Drive\Tiny"),
    Path(r"G:\Tiny"),
]

EXPECTED_STORE_VERSION = "TinyLearner-v1.47.3-tinymemory-v2-wikidata-stream-builder-mul-label-fix"
EXPECTED_STATEMENT_ACCEL_VERSION = "TinyLearner-v1.48.3-tinymemory-exact-subject-bucket-shard-accelerator"
EXPECTED_DUMP_SHA1 = "9888bb6c50f1310b229c077084991f3ea6e6406a"
EXPECTED_PROPERTIES = 13_830

# Entity models.
BASE_ENTITY_SHA256 = "2a2cffa693f6f7e65da7553417e1c18a0839df27d2f744a9add37ba0aebfcfc0"
LEARNED_ENTITY_SHA256 = "82cdae409e28b7c392fea7d37872dc6d82f4a306c5e6dc4646b060837f6d8e4b"
ENTITY_PARAMS = 109_482_240

BASE_ENTITY_DIRS = [
    RESULTS / "v1520_tiny_entity_base_train_compare" / "MODEL",
    Path(r"G:\Мой диск\Tiny\v1520_tiny_entity_base_train_compare\MODEL"),
    Path(r"G:\My Drive\Tiny\v1520_tiny_entity_base_train_compare\MODEL"),
    Path(r"G:\Tiny\v1520_tiny_entity_base_train_compare\MODEL"),
]
LEARNED_ENTITY_DIRS = [
    RESULTS / "v1536_combined_verified_skill_absorption_dev" / "MODEL",
    RESULTS / "v1536_skill_absorption" / "MODEL",
    Path(r"G:\Мой диск\Tiny\v1536_combined_verified_skill_absorption_dev\MODEL"),
    Path(r"G:\Мой диск\Tiny\v1536_skill_absorption\MODEL"),
    Path(r"G:\My Drive\Tiny\v1536_combined_verified_skill_absorption_dev\MODEL"),
    Path(r"G:\Tiny\v1536_combined_verified_skill_absorption_dev\MODEL"),
]

# Property models.
PROPERTY_MODEL = "cointegrated/rubert-tiny2"
PROPERTY_REVISION = "e8ed3b0c8bbf4fb6984c3de043bf7d2f4e5969ae"
LEARNED_PROPERTY_SHA256 = "fec50285e9727d9ee7fa1b4b1f60b1702bea1f61c14298f3f61d79d1e8eb4083"
LEARNED_PROPERTY_CONFIG_SHA256 = "c927981ea4365eed1de7aa4674c6e86fd7c93ea7d2d425dfa2e430f6003798e2"
LEARNED_PROPERTY_TOKENIZER_SHA256 = "2475c0f7e72668b4cd5ae8a758acf4cbe66a18759b8eebaf4e00e82133a38a26"
LEARNED_PROPERTY_TOKENIZER_CONFIG_SHA256 = "d99e2f473ca870e62b0950222ea0c0eff398a1f2b7e321aef4b0539d2f60c39a"
PROPERTY_PARAMS = 29_193_768
LEARNED_PROPERTY_DIRS = [
    RESULTS / "v1542b_property_skill_absorption_clean_holdout_dev" / "MODEL",
    Path(r"G:\Мой диск\Tiny\v1542b_property_skill_absorption_clean_holdout_dev\MODEL"),
    Path(r"G:\My Drive\Tiny\v1542b_property_skill_absorption_clean_holdout_dev\MODEL"),
    Path(r"G:\Tiny\v1542b_property_skill_absorption_clean_holdout_dev\MODEL"),
]

# Official LC-QuAD 2.0 TEST. This split is intentionally first accessed
# only AFTER PREREG_TEST.json is written by this script.
LCQUAD2_TEST_URL = (
    "https://raw.githubusercontent.com/AskNowQA/LC-QuAD2.0/"
    "master/dataset/test.json"
)
FORMAL_MIN_ROWS = 100
SPLIT_SALT = "TinyLearner-v1.56.2-lcquad2-test-formal-v1"

# The formal claim is scoped to a preregistered structural subset:
# - natural English question is non-empty
# - SPARQL has exactly one distinct wd:Q... constant
# - SPARQL has exactly one distinct direct wdt:P... property
# - there is exactly one explicit direct triple wd:Q... wdt:P... ?variable
# - that exact PID is present in the pinned 2026-08-17 TinyMemory
#   property set for that subject (snapshot compatibility)
# - PID is in the frozen 13,830-property catalog
#
# ALL qualifying TEST rows are used. No model outcome participates in
# eligibility or row selection.
SPARQL_QID_RE = re.compile(r"\bwd:(Q\d+)\b", re.IGNORECASE)
SPARQL_WDT_PID_RE = re.compile(r"\bwdt:(P\d+)\b", re.IGNORECASE)
SPARQL_DIRECT_PAIR_RE = re.compile(
    r"\bwd:(Q\d+)\s+wdt:(P\d+)\s+\?[A-Za-z_]\w*",
    re.IGNORECASE,
)

# Frozen ranking machinery.
RRF_K = 60
EVIDENCE_TOPK = 20
ENTITY_TEACHER_TOPK = 20
PROPERTY_TEACHER_TOPK = 10
MAX_SPAN_TOKENS = 10
MAX_ENTITY_LENGTH = 96
MAX_PROPERTY_LENGTH = 128
LEXICAL_MAX_FEATURES = 100_000
SAVE_CANDIDATE_DOC_CHARS = 500
RRF_MAX = 2.0 / (RRF_K + 1.0)
RRF_MAX_TOL = 1e-7

# Teacher exact pin.
TEACHER_MODEL = "Qwen/Qwen2.5-3B-Instruct"
TEACHER_REVISION = "aa8e72537993ba99e69dfaafa59ed015b17504d1"
TEACHER_PARAMS = 3_085_938_688
MAX_PROMPT_TOKENS = 1536
MAX_NEW_TOKENS = 8
INT_RE = re.compile(r"(?<!\d)(\d+)(?!\d)")

PRIMARY_MIN_CANDIDATE_RECALL = 0.60
PRIMARY_MIN_CALL_REDUCTION = 0.05
PRIMARY_MAX_HYBRID_DROP = 0.01
PRIMARY_MIN_AUTONOMOUS_PRECISION = 0.85
PRIMARY_MIN_AUTONOMOUS_N = 20
STRONG_MIN_CALL_REDUCTION = 0.10
STRONG_MIN_AUTONOMOUS_PRECISION = 0.90
STRONG_MIN_AUTONOMOUS_N = 40

STOPWORDS = frozenset("""
a an the who what when where why how which whose whom
is are was were be been being do does did
has have had can could would should will
of in on at to from for with by about as into
and or but if then than this that these those
me you your his her its their our
name names tell give
""".split())
TOKEN_RE = re.compile(r"[^\W_]+(?:['’][^\W_]+)?", re.UNICODE)
SPECIAL_TRANSLATION = str.maketrans({
    "ø":"o", "ł":"l", "đ":"d", "ð":"d", "þ":"th", "æ":"ae", "œ":"oe", "ß":"ss"
})
QID_RE = re.compile(r"^Q\d+$")
PID_RE = re.compile(r"^P\d+$")


class Tee:
    def __init__(self, *streams: Any) -> None:
        self.streams = streams
    def write(self, data: str) -> int:
        for s in self.streams:
            s.write(data); s.flush()
        return len(data)
    def flush(self) -> None:
        for s in self.streams:
            s.flush()
    def isatty(self) -> bool:
        return any(bool(getattr(s, "isatty", lambda: False)()) for s in self.streams)
    def fileno(self) -> int:
        for s in self.streams:
            fn = getattr(s, "fileno", None)
            if fn is not None:
                return int(fn())
        raise OSError("Tee has no fileno")
    @property
    def encoding(self) -> str:
        for s in self.streams:
            v = getattr(s, "encoding", None)
            if v:
                return str(v)
        return "utf-8"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    out = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if line.strip():
                obj = json.loads(line)
                if not isinstance(obj, dict):
                    raise RuntimeError(f"non-object JSONL {path}:{line_no}")
                out.append(obj)
    return out


def resolve_file(candidates: list[Path], label: str) -> Path:
    for p in candidates:
        if p.is_file():
            return p
    raise FileNotFoundError(label + " not found:\n  " + "\n  ".join(map(str, candidates)))


def resolve_model_dir(candidates: list[Path], label: str) -> Path:
    for p in candidates:
        if p.is_dir() and (p / "model.safetensors").is_file():
            return p
    raise FileNotFoundError(label + " not found:\n  " + "\n  ".join(map(str, candidates)))


def drive_root() -> Path:
    for p in DRIVE_ROOT_CANDIDATES:
        if p.is_dir():
            return p
    raise FileNotFoundError("Google Drive Tiny root not found")


def mirror_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def preflight(script_path: Path) -> dict[str, Any]:
    text = script_path.read_text(encoding="utf-8")
    ast.parse(text)
    compile(text, str(script_path), "exec")
    with tempfile.TemporaryDirectory() as td:
        py_compile.compile(str(script_path), cfile=str(Path(td) / "check.pyc"), doraise=True)
    tree = ast.parse(text)
    run_defs = sum(isinstance(n, ast.FunctionDef) and n.name == "run" for n in ast.walk(tree))
    cli_defs = sum(isinstance(n, ast.FunctionDef) and n.name == "cli" for n in ast.walk(tree))
    main_guards = sum(1 for line in text.splitlines() if line.strip() in ('if __name__ == "__main__":', "if __name__ == '__main__':"))
    if (run_defs, cli_defs, main_guards) != (1, 1, 1):
        raise RuntimeError(f"structure invalid {run_defs=} {cli_defs=} {main_guards=}")
    return {"ast_parse":"PASS", "compile":"PASS", "py_compile":"PASS", "run_defs":run_defs, "cli_defs":cli_defs, "main_guards":main_guards}


def fold_unicode(text: str) -> str:
    x = unicodedata.normalize("NFKC", str(text)).casefold().translate(SPECIAL_TRANSLATION)
    x = unicodedata.normalize("NFKD", x)
    return "".join(c for c in x if not unicodedata.combining(c))


def surface_normalize(text: str) -> str:
    x = fold_unicode(text)
    x = re.sub(r"[^a-z0-9]+", " ", x)
    return re.sub(r"\s+", " ", x).strip()


def simple_normalize(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(text)).casefold()).strip()


def raw_tokens(text: str) -> list[str]:
    return [unicodedata.normalize("NFKC", t).casefold().replace("’", "'") for t in TOKEN_RE.findall(text)]


def possessive_stripped(parts: list[str]) -> list[str] | None:
    if not parts:
        return None
    last = parts[-1]
    if last.endswith("'s") and len(last) > 2:
        return parts[:-1] + [last[:-2]]
    if last.endswith("'") and len(last) > 1:
        return parts[:-1] + [last[:-1]]
    return None


def question_spans(question: str) -> list[dict[str, Any]]:
    toks = raw_tokens(question)
    rows, seen = [], set()
    for start in range(len(toks)):
        for end in range(start + 1, min(len(toks), start + MAX_SPAN_TOKENS) + 1):
            parts = toks[start:end]
            for variant, pp in (("base", parts), ("possessive_stripped", possessive_stripped(parts))):
                if pp is None:
                    continue
                text = surface_normalize(" ".join(pp))
                words = text.split()
                if not text or all(w in STOPWORDS for w in words):
                    continue
                key = (text, len(parts), variant)
                if key in seen:
                    continue
                seen.add(key)
                rows.append({"text":text, "token_len":len(parts), "char_len":len(text), "variant":variant})
    return rows


def sql_normalize(column: str) -> str:
    x = f"lower(trim({column}))"
    for a,b in (("ø","o"),("ł","l"),("đ","d"),("ð","d"),("þ","th"),("æ","ae"),("œ","oe"),("ß","ss")):
        x = f"replace({x}, '{a}', '{b}')"
    x = f"strip_accents({x})"
    x = f"regexp_replace({x}, '[^a-z0-9]+', ' ', 'g')"
    return f"trim(regexp_replace({x}, ' +', ' ', 'g'))"


def choose(*vals: Any) -> str:
    for v in vals:
        if v is not None and str(v).strip():
            return str(v).strip()
    return ""


def entity_doc(m: dict[str, Any]) -> str:
    label = choose(m.get("label_en"), m.get("label_mul"), m.get("label_ru"), m.get("entity_id"))
    desc = choose(m.get("description_en"), m.get("description_ru"))
    return f"{label}. {desc}".strip(". ") if desc else label


def entity_teacher_doc(m: dict[str, Any]) -> str:
    label = choose(m.get("label_en"), m.get("label_mul"), m.get("label_ru"), "unknown entity")
    desc = choose(m.get("description_en"), m.get("description_ru"))
    return (f"{label} — {desc}" if desc else label)[:SAVE_CANDIDATE_DOC_CHARS]


def property_canonical_doc(p: dict[str, Any]) -> str:
    label = choose(p.get("label_en"), p.get("label_mul"), p.get("label_ru"), p.get("pid"))
    desc = choose(p.get("description_en"), p.get("description_ru"))
    return f"{label}. {desc}".strip(". ") if desc else label


def property_memory_doc(p: dict[str, Any], aliases: list[str]) -> str:
    parts = [property_canonical_doc(p)]
    seen = {surface_normalize(parts[0])} if parts[0] else set()
    for alias in aliases:
        norm = surface_normalize(alias)
        if norm and norm not in seen:
            seen.add(norm); parts.append(alias)
    return " ; ".join(x for x in parts if x)


def property_teacher_doc(p: dict[str, Any]) -> str:
    label = choose(p.get("label_en"), p.get("label_mul"), p.get("label_ru"), "unknown property")
    desc = choose(p.get("description_en"), p.get("description_ru"))
    return (f"{label} — {desc}" if desc else label)[:SAVE_CANDIDATE_DOC_CHARS]


def parse_entity_id(eid: str) -> tuple[str, int]:
    s = str(eid).strip().upper()
    if not re.fullmatch(r"[QP]\d+", s):
        raise ValueError(f"bad entity id {eid!r}")
    return s[0], int(s[1:])


def sql_string_list(values: list[str]) -> str:
    return "[" + ",".join("'" + str(v).replace("'", "''") + "'" for v in values) + "]"


def encode_cls(texts, tokenizer, model, torch, device: str, batch_size: int, max_length: int):
    import numpy as np
    chunks = []
    model.eval()
    for start in range(0, len(texts), batch_size):
        batch = texts[start:start+batch_size]
        toks = tokenizer(batch, padding=True, truncation=True, max_length=max_length, return_tensors="pt")
        toks = {k:v.to(device) for k,v in toks.items()}
        with torch.inference_mode():
            out = model(**toks)
            emb = torch.nn.functional.normalize(out.last_hidden_state[:,0,:].float(), p=2, dim=1)
        chunks.append(emb.cpu().numpy().astype("float32"))
        done = min(start+batch_size, len(texts))
        if done == len(texts) or done % max(batch_size*20,1) == 0:
            print(f"    encoded {done:,}/{len(texts):,}", flush=True)
    return np.concatenate(chunks, axis=0)


def ranks_from_scores(scores):
    import numpy as np
    order = np.argsort(-scores, axis=1, kind="stable")
    ranks = np.empty_like(order, dtype=np.int32)
    ranks[np.arange(scores.shape[0])[:,None], order] = np.arange(1, scores.shape[1]+1, dtype=np.int32)[None,:]
    return ranks


def dense_property_scores(query_emb, phrase_emb, phrase_pid_indices, n_properties: int):
    import numpy as np
    raw = query_emb @ phrase_emb.T
    out = np.full((raw.shape[0], n_properties), -1e9, dtype=np.float32)
    idx = np.asarray(phrase_pid_indices, dtype=np.int32)
    for i in range(raw.shape[0]):
        np.maximum.at(out[i], idx, raw[i])
    return out


def final_entity_order(shortlist: list[str], compatibility: dict[str,int]) -> list[str]:
    if not shortlist:
        return []
    tiny_rank = {q:i+1 for i,q in enumerate(shortlist)}
    compat_order = sorted(shortlist, key=lambda q:(compatibility.get(q, EXPECTED_PROPERTIES+1), q))
    compat_rank = {q:i+1 for i,q in enumerate(compat_order)}
    scored = []
    for q in shortlist:
        s = 1/(RRF_K + tiny_rank[q]) + 1/(RRF_K + compat_rank[q])
        scored.append((-s, q))
    scored.sort()
    return [q for _,q in scored]


def validate_tinymemory(root: Path, accel_root: Path) -> dict[str,Any]:
    sm = json.loads((root / "BUILD_MANIFEST.json").read_text(encoding="utf-8"))
    ss = json.loads((root / "_SUCCESS.json").read_text(encoding="utf-8"))
    am = json.loads((accel_root / "BUILD_MANIFEST.json").read_text(encoding="utf-8"))
    ass = json.loads((accel_root / "_SUCCESS.json").read_text(encoding="utf-8"))
    if ss.get("status") != "SUCCESS" or ass.get("status") != "SUCCESS":
        raise RuntimeError("TinyMemory/accelerator not SUCCESS")
    if sm.get("version") != EXPECTED_STORE_VERSION:
        raise RuntimeError("TinyMemory version mismatch")
    if am.get("version") != EXPECTED_STATEMENT_ACCEL_VERSION:
        raise RuntimeError("statement accelerator version mismatch")
    dump = str((sm.get("dump") or {}).get("sha1") or "").lower()
    adump = str((am.get("source") or {}).get("dump_sha1") or "").lower()
    if dump != EXPECTED_DUMP_SHA1 or adump != EXPECTED_DUMP_SHA1:
        raise RuntimeError("dump SHA1 mismatch")
    if not ENTITY_ACCEL.is_dir():
        raise RuntimeError(f"entity accel missing: {ENTITY_ACCEL}")
    return {"store_version":sm.get("version"), "statement_accel_version":am.get("version"), "dump_sha1":dump}


def load_property_catalog(root: Path):
    import duckdb
    db = duckdb.connect(str(root / "tinymemory.duckdb"), read_only=True)
    try:
        prop_rows = db.execute("""
        SELECT property_id,datatype,label_ru,label_en,label_mul,description_ru,description_en
        FROM property_catalog ORDER BY property_id
        """).fetchall()
        alias_rows = db.execute("""
        SELECT entity_id,lang,alias FROM aliases
        WHERE starts_with(entity_id,'P') AND lang IN ('en','mul')
        ORDER BY entity_id,lang,alias
        """).fetchall()
    finally:
        db.close()
    if len(prop_rows) != EXPECTED_PROPERTIES:
        raise RuntimeError(f"property count {len(prop_rows)} != {EXPECTED_PROPERTIES}")
    props = [{"pid":str(r[0]),"datatype":r[1],"label_ru":r[2],"label_en":r[3],"label_mul":r[4],"description_ru":r[5],"description_en":r[6]} for r in prop_rows]
    pidset = {p["pid"] for p in props}
    aliases = defaultdict(list); seen = defaultdict(set)
    for pid, _lang, alias in alias_rows:
        pid = str(pid); a = str(alias).strip(); n = surface_normalize(a)
        if pid in pidset and n and n not in seen[pid]:
            seen[pid].add(n); aliases[pid].append(a)
    return props, dict(aliases)


def load_entity_metadata(root: Path, qids: list[str]) -> dict[str,dict[str,Any]]:
    import duckdb
    if not qids:
        return {}
    db = duckdb.connect(str(root / "tinymemory.duckdb"), read_only=True)
    try:
        db.execute("CREATE TEMP TABLE wanted_entities(entity_id VARCHAR PRIMARY KEY)")
        for start in range(0,len(qids),5000):
            db.executemany("INSERT INTO wanted_entities VALUES (?)", [(x,) for x in qids[start:start+5000]])
        rows = db.execute("""
        SELECT e.entity_id,e.label_ru,e.label_en,e.label_mul,e.description_ru,e.description_en
        FROM entities e JOIN wanted_entities w ON e.entity_id=w.entity_id
        """).fetchall()
    finally:
        db.close()
    out = {str(r[0]):{"entity_id":str(r[0]),"label_ru":r[1],"label_en":r[2],"label_mul":r[3],"description_ru":r[4],"description_en":r[5]} for r in rows}
    missing = set(qids)-set(out)
    if missing:
        raise RuntimeError(f"missing entity metadata {len(missing)}")
    return out


def generate_exact_candidates(root: Path, questions: list[str]):
    import duckdb
    span_rows=[]; phrases=set()
    for q in questions:
        ss=question_spans(q); span_rows.append(ss); phrases.update(x["text"] for x in ss)
    db=duckdb.connect(str(root / "tinymemory.duckdb"), read_only=True)
    try:
        db.execute("CREATE TEMP TABLE wanted_phrases(phrase VARCHAR PRIMARY KEY)")
        pp=sorted(phrases)
        for start in range(0,len(pp),5000):
            db.executemany("INSERT INTO wanted_phrases VALUES (?)",[(x,) for x in pp[start:start+5000]])
        en=sql_normalize("e.label_en"); mul=sql_normalize("e.label_mul"); al=sql_normalize("a.alias")
        rows=db.execute(f"""
        WITH m AS (
          SELECT e.entity_id,{en} phrase FROM entities e JOIN wanted_phrases w ON {en}=w.phrase
          WHERE starts_with(e.entity_id,'Q') AND e.label_en IS NOT NULL
          UNION ALL
          SELECT e.entity_id,{mul} phrase FROM entities e JOIN wanted_phrases w ON {mul}=w.phrase
          WHERE starts_with(e.entity_id,'Q') AND e.label_mul IS NOT NULL
          UNION ALL
          SELECT a.entity_id,{al} phrase FROM aliases a JOIN wanted_phrases w ON {al}=w.phrase
          WHERE starts_with(a.entity_id,'Q') AND a.lang IN ('en','mul')
        ) SELECT entity_id,phrase FROM m GROUP BY entity_id,phrase
        """).fetchall()
    finally:
        db.close()
    phrase_candidates=defaultdict(set)
    for qid,phrase in rows:
        phrase_candidates[str(phrase)].add(str(qid))
    per=[]; union=set()
    for ss in span_rows:
        cset=set()
        for sp in ss:
            cset.update(phrase_candidates.get(sp["text"],set()))
        cands=sorted(cset); per.append(cands); union.update(cands)
    return per, sorted(union), {"phrases":len(phrases),"candidate_union":len(union),"candidate_counts":[len(x) for x in per]}


def load_subject_property_sets(accel_root: Path, subject_ids: list[str], valid_pids: set[str]):
    import duckdb
    manifest=json.loads((accel_root / "BUILD_MANIFEST.json").read_text(encoding="utf-8"))
    bucket_size=int(manifest["bucket_size"])
    unique=sorted(set(q for q in subject_ids if q))
    result={q:set() for q in unique}; buckets=defaultdict(list)
    for q in unique:
        kind,num=parse_entity_id(q); buckets[(kind,num//bucket_size)].append(q)
    accel=duckdb.connect(str(accel_root / "tinymemory_bucket_accel.duckdb"),read_only=True)
    try:
        done=0
        for (kind,bid),ids in sorted(buckets.items()):
            routes=accel.execute("""
            SELECT c.file_path FROM subject_bucket_shards b
            JOIN shard_catalog c ON c.shard_id=b.shard_id
            WHERE b.entity_kind=? AND b.bucket_id=? ORDER BY c.file_name
            """,[kind,bid]).fetchall()
            paths=[str(r[0]) for r in routes]
            if paths:
                placeholders=",".join("?" for _ in ids)
                rr=accel.execute(f"""
                SELECT subject_id,property_id FROM read_parquet({sql_string_list(paths)},union_by_name=true)
                WHERE subject_id IN ({placeholders}) GROUP BY subject_id,property_id
                """,ids).fetchall()
                for q,p in rr:
                    ps=str(p)
                    if ps in valid_pids: result[str(q)].add(ps)
            done+=len(ids)
            if done==len(unique) or done%250==0:
                print(f"    subject sets {done:,}/{len(unique):,}",flush=True)
    finally:
        accel.close()
    return result


def discover_entity_value_column(accel, paths: list[str]) -> tuple[str,list[tuple[Any,...]]]:
    schema=accel.execute(f"DESCRIBE SELECT * FROM read_parquet({sql_string_list(paths[:1])},union_by_name=true)").fetchall()
    names=[str(r[0]) for r in schema]
    lower={n.lower():n for n in names}
    preferred=["value_entity_id","value_entity","entity_value","object_id","value_qid","entity_value_id","value_entity_qid"]
    for p in preferred:
        if p in lower:
            return lower[p],schema
    excluded={"subject_id","property_id","statement_id"}
    for n in names:
        nl=n.lower()
        if nl in excluded: continue
        typ=next(str(r[1]).upper() for r in schema if str(r[0])==n)
        if "CHAR" not in typ and "VARCHAR" not in typ and "STRING" not in typ: continue
        if not any(k in nl for k in ("entity","object","value")): continue
        qn='"'+n.replace('"','""')+'"'
        vals=accel.execute(f"SELECT CAST({qn} AS VARCHAR) FROM read_parquet({sql_string_list(paths[:1])},union_by_name=true) WHERE {qn} IS NOT NULL LIMIT 100").fetchall()
        good=sum(bool(QID_RE.fullmatch(str(r[0]))) for r in vals if r and r[0] is not None)
        if vals and good/max(len(vals),1)>=0.20:
            return n,schema
    raise RuntimeError("Could not discover entity-valued object column in statement parquet schema: "+repr(schema))


def direct_edge_properties(accel_root: Path, pairs: list[tuple[str,str]], valid_pids: set[str]):
    import duckdb
    manifest=json.loads((accel_root / "BUILD_MANIFEST.json").read_text(encoding="utf-8"))
    bucket_size=int(manifest["bucket_size"])
    buckets=defaultdict(list)
    for s,o in pairs:
        kind,num=parse_entity_id(s); buckets[(kind,num//bucket_size)].append((s,o))
    result={(s,o):set() for s,o in pairs}
    discovered_col=None; schema_saved=None
    accel=duckdb.connect(str(accel_root / "tinymemory_bucket_accel.duckdb"),read_only=True)
    try:
        for (kind,bid),local_pairs in sorted(buckets.items()):
            routes=accel.execute("""
            SELECT c.file_path FROM subject_bucket_shards b JOIN shard_catalog c ON c.shard_id=b.shard_id
            WHERE b.entity_kind=? AND b.bucket_id=? ORDER BY c.file_name
            """,[kind,bid]).fetchall()
            paths=[str(r[0]) for r in routes]
            if not paths: continue
            if discovered_col is None:
                discovered_col,schema_saved=discover_entity_value_column(accel,paths)
                print("    discovered entity-value column:",discovered_col)
            qcol='"'+discovered_col.replace('"','""')+'"'
            accel.execute("DROP TABLE IF EXISTS wanted_pairs")
            accel.execute("CREATE TEMP TABLE wanted_pairs(subject_id VARCHAR, answer_id VARCHAR)")
            accel.executemany("INSERT INTO wanted_pairs VALUES (?,?)",local_pairs)
            rr=accel.execute(f"""
            SELECT s.subject_id,w.answer_id,s.property_id
            FROM read_parquet({sql_string_list(paths)},union_by_name=true) s
            JOIN wanted_pairs w ON s.subject_id=w.subject_id
            WHERE CAST(s.{qcol} AS VARCHAR)=w.answer_id
            GROUP BY s.subject_id,w.answer_id,s.property_id
            """).fetchall()
            for s,o,p in rr:
                ps=str(p)
                if ps in valid_pids: result[(str(s),str(o))].add(ps)
    finally:
        accel.close()
    return result,{"entity_value_column":discovered_col,"schema":schema_saved}


def build_phrasebank(properties,aliases_by_pid):
    pids=[p["pid"] for p in properties]; pidx={p:i for i,p in enumerate(pids)}
    texts=[]; indices=[]
    for p in properties:
        j=pidx[p["pid"]]; seen=set(); canon=property_canonical_doc(p)
        if canon:
            n=surface_normalize(canon)
            if n not in seen: seen.add(n); texts.append(canon); indices.append(j)
        for a in aliases_by_pid.get(p["pid"],[]):
            n=surface_normalize(a)
            if n and n not in seen: seen.add(n); texts.append(a); indices.append(j)
    return texts,indices,pids


def make_lexical_scores(questions,properties,aliases_by_pid):
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    docs=[property_memory_doc(p,aliases_by_pid.get(p["pid"],[])) for p in properties]
    vec=TfidfVectorizer(analyzer="char_wb",ngram_range=(3,5),lowercase=True,dtype=np.float32,max_features=LEXICAL_MAX_FEATURES)
    pm=vec.fit_transform(docs); qm=vec.transform(questions)
    return (qm@pm.T).toarray()


def make_neural_scores(questions,phrase_texts,phrase_indices,n_props,tokenizer,model,torch,device,batch_size):
    pe=encode_cls(phrase_texts,tokenizer,model,torch,device,batch_size,MAX_PROPERTY_LENGTH)
    qe=encode_cls(questions,tokenizer,model,torch,device,batch_size,MAX_PROPERTY_LENGTH)
    return dense_property_scores(qe,pe,phrase_indices,n_props)


def entity_direct_orders(questions,per_candidates,meta,model_dir,expected_sha,expected_params,torch,AutoTokenizer,AutoModel,device,batch_size):
    import numpy as np
    sha=sha256_file(model_dir/"model.safetensors")
    if sha!=expected_sha: raise RuntimeError(f"entity model SHA {sha} != {expected_sha}")
    qids=sorted({q for c in per_candidates for q in c})
    tok=AutoTokenizer.from_pretrained(model_dir,local_files_only=True)
    model=AutoModel.from_pretrained(model_dir,local_files_only=True).to(device).eval()
    params=int(sum(p.numel() for p in model.parameters()))
    if params!=expected_params: raise RuntimeError(f"entity params {params} != {expected_params}")
    docs=[entity_doc(meta[q]) for q in qids]; qidx={q:i for i,q in enumerate(qids)}
    de=encode_cls(docs,tok,model,torch,device,batch_size,MAX_ENTITY_LENGTH)
    qe=encode_cls(questions,tok,model,torch,device,batch_size,MAX_ENTITY_LENGTH)
    orders=[]
    for i,cands in enumerate(per_candidates):
        if not cands: orders.append([]); continue
        idxs=np.asarray([qidx[x] for x in cands],dtype=np.int32)
        scores=de[idxs]@qe[i]; local=np.argsort(-scores,kind="stable")
        orders.append([cands[int(j)] for j in local])
    del model,tok,de,qe; gc.collect()
    if device.startswith("cuda"): torch.cuda.empty_cache()
    return orders,{"sha256":sha,"params":params}


def entity_final_rankings(direct_orders,subject_props,global_property_ranks,pid_idx):
    outputs=[]
    for i,direct in enumerate(direct_orders):
        shortlist=direct[:EVIDENCE_TOPK]; compat={}
        for q in shortlist:
            inds=[pid_idx[p] for p in subject_props.get(q,set()) if p in pid_idx]
            compat[q]=min((int(global_property_ranks[i,j]) for j in inds),default=EXPECTED_PROPERTIES+1)
        order=final_entity_order(shortlist,compat)
        top=order[0] if order else None
        direct_top=direct[0] if direct else None
        evidence_rank=compat.get(top,EXPECTED_PROPERTIES+1) if top else EXPECTED_PROPERTIES+1
        prop_count=len(subject_props.get(top,set())) if top else 0
        accept=bool(top and direct_top==top and evidence_rank<=5 and prop_count>=20)
        outputs.append({
            "direct_top1_qid":direct_top,"final_top1_qid":top,"final_top20":order[:ENTITY_TEACHER_TOPK],
            "best_global_property_rank":evidence_rank,"property_count":prop_count,"accept":accept,"fallback":not accept,
            "top20_evidence":[{"qid":q,"best_global_property_rank":compat.get(q,EXPECTED_PROPERTIES+1),"property_count":len(subject_props.get(q,set()))} for q in order[:EVIDENCE_TOPK]]
        })
    return outputs


def entity_teacher_prompt(question,ordered_qids,meta):
    docs=[f"{i}. {entity_teacher_doc(meta[q])}" for i,q in enumerate(ordered_qids,start=1)]
    return (
        "Question:\n"+question+"\n\nCandidate entities:\n"+"\n".join(docs)+"\n\n"
        "The candidates are ordered by Tiny from most likely to least likely. Candidate 1 is Tiny's current best answer. "
        "Use that ranking as a strong prior: keep candidate 1 unless another candidate is clearly a better semantic match to the question. "
        f"Return ONLY one integer from 1 to {len(ordered_qids)}. Return 0 only if none of the candidates plausibly match."
    )


def entity_teacher_messages(prompt):
    return [{"role":"system","content":"You are a careful cooperative entity-linking teacher. The supplied candidates are ranked by a smaller system. Treat earlier candidates as more likely unless semantics clearly justify an override. Choose only from the supplied candidates. Do not explain your answer. Output only the integer candidate number, or 0."},{"role":"user","content":prompt}]


def property_teacher_prompt(question,candidate_docs):
    lines=[f"{i}. {doc}" for i,doc in enumerate(candidate_docs,start=1)]
    return (
        "Question:\n"+question+"\n\nCandidate relation/property meanings:\n"+"\n".join(lines)+"\n\n"
        "The candidates are ordered by the frozen smaller property resolver from most likely to least likely. Candidate 1 is its current best mapping. "
        "Use that order as a strong prior: keep candidate 1 unless another candidate is clearly a better semantic match to the question. "
        f"Return ONLY one integer from 1 to {len(candidate_docs)}. Return 0 only if none of the candidates plausibly match."
    )


def property_teacher_messages(prompt):
    return [{"role":"system","content":"You are a careful cooperative relation/property-mapping teacher. Choose only from the supplied natural-language property candidates. Earlier candidates are more likely. Do not explain. Output only the integer candidate number, or 0."},{"role":"user","content":prompt}]


def parse_teacher_choice(text,n):
    m=INT_RE.search(str(text))
    if not m: return None
    v=int(m.group(1))
    return v if 0<=v<=n else None


def teacher_infer(tasks,mode,tokenizer,model,torch,device,batch_size):
    tokenizer.padding_side="left"
    if tokenizer.pad_token_id is None: tokenizer.pad_token_id=tokenizer.eos_token_id
    total=len(tasks)
    for start in range(0,total,batch_size):
        batch=tasks[start:start+batch_size]; rendered=[]
        for t in batch:
            msgs=entity_teacher_messages(t["teacher_prompt"]) if mode=="entity" else property_teacher_messages(t["teacher_prompt"])
            rendered.append(tokenizer.apply_chat_template(msgs,tokenize=False,add_generation_prompt=True))
        inputs=tokenizer(rendered,padding=True,truncation=True,max_length=MAX_PROMPT_TOKENS,return_tensors="pt")
        inputs={k:v.to(device) for k,v in inputs.items()}
        with torch.inference_mode():
            outputs=model.generate(**inputs,max_new_tokens=MAX_NEW_TOKENS,do_sample=False,pad_token_id=tokenizer.pad_token_id,eos_token_id=tokenizer.eos_token_id)
        generated=outputs[:,inputs["input_ids"].shape[1]:]
        decoded=tokenizer.batch_decode(generated,skip_special_tokens=True)
        for t,text in zip(batch,decoded):
            hidden=t["candidate_ids_hidden"]
            choice=parse_teacher_choice(text,len(hidden))
            t["teacher_raw_output"]=str(text).strip(); t["teacher_choice_index"]=choice
            if choice is None:
                t["teacher_selected_id_hidden"]=None; t["teacher_outcome"]="PARSE_FAILURE"
            elif choice==0:
                t["teacher_selected_id_hidden"]=None; t["teacher_outcome"]="ABSTAIN"
            else:
                t["teacher_selected_id_hidden"]=hidden[choice-1]; t["teacher_outcome"]="SELECTED"
        done=min(start+batch_size,total)
        if done==total or done%max(batch_size*10,1)==0: print(f"    {mode} teacher {done:,}/{total:,}",flush=True)


def property_rankings(questions,resolved_subjects,subject_props,properties,lexical_scores,neural_scores):
    import numpy as np
    pids=[p["pid"] for p in properties]; pidx={p:i for i,p in enumerate(pids)}; pmeta={p["pid"]:p for p in properties}
    out=[]
    for i,(q,subject) in enumerate(zip(questions,resolved_subjects)):
        inds=sorted(pidx[p] for p in subject_props.get(subject,set()) if p in pidx) if subject else []
        if not inds:
            out.append({"subject_id":subject,"candidate_count":0,"top10":[],"lexical_top1_pid":None,"neural_top1_pid":None,"rrf_top1_pid":None,"accept":False,"fallback":True}); continue
        idx=np.asarray(inds,dtype=np.int32); lv=lexical_scores[i,idx]; nv=neural_scores[i,idx]
        lo=np.argsort(-lv,kind="stable"); no=np.argsort(-nv,kind="stable")
        lr=np.empty(len(inds),dtype=np.int32); nr=np.empty(len(inds),dtype=np.int32)
        lr[lo]=np.arange(1,len(inds)+1); nr[no]=np.arange(1,len(inds)+1)
        rrf=1.0/(RRF_K+lr.astype(float))+1.0/(RRF_K+nr.astype(float)); ro=np.argsort(-rrf,kind="stable")
        ltop=pids[inds[int(lo[0])]]; ntop=pids[inds[int(no[0])]]; accept=ltop==ntop
        top10=[]
        for pos in ro[:PROPERTY_TEACHER_TOPK]:
            gi=inds[int(pos)]; pid=pids[gi]
            top10.append({"pid":pid,"teacher_doc":property_teacher_doc(pmeta[pid]),"score":float(rrf[int(pos)]),"lexical_rank":int(lr[int(pos)]),"neural_rank":int(nr[int(pos)])})
        if (abs(float(top10[0]["score"])-RRF_MAX)<=RRF_MAX_TOL)!=accept:
            raise RuntimeError("property consensus equivalence failure")
        out.append({"subject_id":subject,"candidate_count":len(inds),"top10":top10,"lexical_top1_pid":ltop,"neural_top1_pid":ntop,"rrf_top1_pid":top10[0]["pid"],"accept":accept,"fallback":not accept})
    return out


def make_entity_teacher_tasks(rows,rankings,meta,branch):
    tasks=[]
    for i,(row,r) in enumerate(zip(rows,rankings)):
        if not r["fallback"] or not r["final_top20"]: continue
        ids=r["final_top20"][:ENTITY_TEACHER_TOPK]
        tasks.append({"branch":branch,"row_index":i,"row_id_hidden_from_prompt":row["id"],"question":row["question"],"candidate_ids_hidden":ids,"teacher_prompt":entity_teacher_prompt(row["question"],ids,meta),"teacher_raw_output":None,"teacher_choice_index":None,"teacher_selected_id_hidden":None,"teacher_outcome":None})
    return tasks


def resolve_entity_subjects(rankings,tasks):
    by={int(t["row_index"]):t for t in tasks}; subjects=[]; calls=[]
    for i,r in enumerate(rankings):
        t=by.get(i); tiny=r["final_top1_qid"]
        if r["accept"]:
            subjects.append(tiny); calls.append(0)
        elif t is not None:
            sel=t.get("teacher_selected_id_hidden")
            subjects.append(sel if t.get("teacher_outcome")=="SELECTED" and sel else tiny); calls.append(1)
        else:
            subjects.append(tiny); calls.append(0)
    return subjects,calls


def make_property_teacher_tasks(rows,rankings,branch):
    tasks=[]
    for i,(row,r) in enumerate(zip(rows,rankings)):
        if not r["fallback"] or not r["top10"]: continue
        ids=[x["pid"] for x in r["top10"]]; docs=[x["teacher_doc"] for x in r["top10"]]
        tasks.append({"branch":branch,"row_index":i,"row_id_hidden_from_prompt":row["id"],"question":row["question"],"candidate_ids_hidden":ids,"candidate_docs":docs,"teacher_prompt":property_teacher_prompt(row["question"],docs),"teacher_raw_output":None,"teacher_choice_index":None,"teacher_selected_id_hidden":None,"teacher_outcome":None})
    return tasks


def resolve_properties(rankings,tasks):
    by={int(t["row_index"]):t for t in tasks}; pids=[]; calls=[]
    for i,r in enumerate(rankings):
        t=by.get(i); tiny=r["rrf_top1_pid"]
        if r["accept"]:
            pids.append(tiny); calls.append(0)
        elif t is not None:
            sel=t.get("teacher_selected_id_hidden")
            pids.append(sel if t.get("teacher_outcome")=="SELECTED" and sel else tiny); calls.append(1)
        else:
            pids.append(tiny); calls.append(0)
    return pids,calls


def sample_key(mid,question):
    return sha256_text(f"{SPLIT_SALT}\t{mid}\t{question}")


def natural_question(row: dict[str, Any]) -> str:
    p = str(row.get("paraphrased_question") or "").strip()
    if p and p.casefold() not in {"na", "n/a", "none", "null"}:
        return p
    return str(row.get("question") or "").strip()


def download_test_after_prereg(url: str, target: Path) -> None:
    if target.exists() and target.stat().st_size > 0:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "TinyLearner-v1.56.2-formal-test/1.0"},
    )
    with urllib.request.urlopen(req, timeout=120) as response:
        data = response.read()
    if not data:
        raise RuntimeError("Downloaded LC-QuAD 2.0 TEST is empty")
    target.write_bytes(data)


def extract_formal_pair(sparql: str) -> tuple[str, str] | None:
    s = str(sparql or "")
    qids = sorted({m.group(1).upper() for m in SPARQL_QID_RE.finditer(s)})
    pids = sorted({m.group(1).upper() for m in SPARQL_WDT_PID_RE.finditer(s)})
    direct_pairs = sorted({
        (m.group(1).upper(), m.group(2).upper())
        for m in SPARQL_DIRECT_PAIR_RE.finditer(s)
    })
    if len(qids) != 1 or len(pids) != 1 or len(direct_pairs) != 1:
        return None
    pair = direct_pairs[0]
    if pair != (qids[0], pids[0]):
        return None
    return pair


def build_formal_test_sample(test_path: Path, valid_pids: set[str]):
    raw = json.loads(test_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise RuntimeError("LC-QuAD 2.0 TEST root must be a list")

    syntactic = []
    nonempty_questions = 0
    for row in raw:
        if not isinstance(row, dict):
            continue
        question = natural_question(row)
        if not question:
            continue
        nonempty_questions += 1
        pair = extract_formal_pair(str(row.get("sparql_wikidata") or ""))
        if pair is None:
            continue
        qid, pid = pair
        if pid not in valid_pids:
            continue
        uid = str(row.get("uid") if row.get("uid") is not None else "")
        syntactic.append({
            "id": uid,
            "question": question,
            "subject_id": qid,
            "gold_pid": pid,
            "sample_key": sample_key(uid, question),
        })

    # Snapshot-compatibility gate is structural and frozen before TEST access:
    # the gold PID must be an actual property of the gold subject in pinned
    # TinyMemory. This does not consult any model score, gate, or teacher.
    subject_ids = sorted({r["subject_id"] for r in syntactic})
    subject_props = load_subject_property_sets(
        STATEMENT_ACCEL, subject_ids, valid_pids
    )

    qualified = [
        r for r in syntactic
        if r["gold_pid"] in subject_props.get(r["subject_id"], set())
    ]
    qualified.sort(key=lambda r: (r["sample_key"], r["id"]))

    if len(qualified) < FORMAL_MIN_ROWS:
        raise RuntimeError(
            f"formal eligible rows {len(qualified)} < {FORMAL_MIN_ROWS}"
        )

    return qualified, {
        "raw_test_rows": len(raw),
        "nonempty_question_rows": nonempty_questions,
        "single_direct_qid_pid_rows_in_catalog": len(syntactic),
        "snapshot_compatible_rows": len(qualified),
        "selected_rows": len(qualified),
        "selection_uses_model_outputs": False,
        "all_qualifying_rows_used": True,
        "test_source_sha256": sha256_file(test_path),
        "test_source_bytes": test_path.stat().st_size,
        "test_url": LCQUAD2_TEST_URL,
    }


def build_property_semantics(questions,properties,aliases,base_model_tok,base_model,learned_tok,learned_model,torch,device,batch_size):
    phrase_texts,phrase_indices,pids=build_phrasebank(properties,aliases)
    print("    lexical property matrix...")
    lexical=make_lexical_scores(questions,properties,aliases)
    print("    base property neural scores...")
    base=make_neural_scores(questions,phrase_texts,phrase_indices,len(pids),base_model_tok,base_model,torch,device,batch_size)
    print("    learned property neural scores...")
    learned=make_neural_scores(questions,phrase_texts,phrase_indices,len(pids),learned_tok,learned_model,torch,device,batch_size)
    return lexical,base,learned,pids


def score_branch(name,rows,gold,entity_rankings,resolved_subjects,entity_calls,property_rankings_,resolved_pids,property_calls,per_candidates):
    n=len(rows); pair_hits=entity_hits=property_hits=tiny_pair_hits=0; autonomous_n=autonomous_hits=0; any_calls=0; total_calls=0
    trace=[]
    for i,row in enumerate(rows):
        g=gold[row["id"]]; subj=resolved_subjects[i]; pid=resolved_pids[i]
        eok=subj==g["subject_id"]; pok=pid==g["gold_pid"]; pair=eok and pok
        entity_hits+=int(eok); property_hits+=int(pok); pair_hits+=int(pair)
        calls=int(entity_calls[i])+int(property_calls[i]); total_calls+=calls; any_calls+=int(calls>0)
        autonomous=bool(entity_rankings[i]["accept"] and property_rankings_[i]["accept"])
        if autonomous:
            autonomous_n+=1; autonomous_hits+=int(pair)
        tiny_subj=entity_rankings[i]["final_top1_qid"]
        tiny_pid=property_rankings_[i]["rrf_top1_pid"] if property_rankings_[i]["subject_id"]==tiny_subj else None
        tiny_pair_hits+=int(tiny_subj==g["subject_id"] and tiny_pid==g["gold_pid"])
        trace.append({"id":row["id"],"question":row["question"],"gold_subject_id":g["subject_id"],"gold_pid":g["gold_pid"],"candidate_count":len(per_candidates[i]),"gold_subject_in_candidates":g["subject_id"] in per_candidates[i],"entity_accept":entity_rankings[i]["accept"],"entity_final_top1":entity_rankings[i]["final_top1_qid"],"resolved_subject":subj,"entity_calls":entity_calls[i],"property_accept":property_rankings_[i]["accept"],"property_rrf_top1":property_rankings_[i]["rrf_top1_pid"],"resolved_pid":pid,"property_calls":property_calls[i],"total_calls":calls,"pair_correct":pair,"autonomous_zero_call":autonomous})
    return {
        "branch":name,"rows":n,"total_real_qwen_calls":total_calls,"calls_per_question":total_calls/n,"any_llm_call_n":any_calls,"any_llm_call_rate":any_calls/n,
        "zero_actual_call_n":n-any_calls,"zero_actual_call_rate":1-any_calls/n,"entity_hybrid_accuracy":entity_hits/n,"property_pid_accuracy_unconditional":property_hits/n,"hybrid_pair_accuracy":pair_hits/n,
        "autonomous_zero_call_n":autonomous_n,"autonomous_zero_call_coverage":autonomous_n/n,"autonomous_zero_call_pair_hits":autonomous_hits,"autonomous_zero_call_pair_precision":autonomous_hits/autonomous_n if autonomous_n else None,
        "tiny_best_effort_pair_accuracy":tiny_pair_hits/n,
    },trace


def build_manifest(output:Path):
    files=[]
    for p in sorted((x for x in output.rglob("*") if x.is_file()),key=str):
        rel=str(p.relative_to(output)).replace("\\","/")
        if rel=="ARTIFACT_MANIFEST.json": continue
        files.append({"name":rel,"bytes":p.stat().st_size,"sha256":sha256_file(p)})
    return {"version":VERSION,"created_utc":utc_now(),"files":files}


def make_prereg(script_sha):
    return {
        "version": VERSION,
        "status": "FORMAL_TEST_FROZEN_BEFORE_TEST_SOURCE_ACCESS",
        "created_utc": utc_now(),
        "script_sha256": script_sha,
        "hypothesis": (
            "On the previously unopened official LC-QuAD 2.0 TEST structural "
            "single-(subject, property) subset, the already-learned entity and "
            "property skills jointly reduce real Qwen fallback calls versus "
            "the frozen baseline without materially reducing exact "
            "(subject QID, property PID) hybrid accuracy."
        ),
        "dev_qualification": {
            "source": "v1561a_integrated_end_to_end_fresh_dev",
            "primary_dev_pass": True,
            "strong_dev_pass": False,
            "dev_rows": 351,
            "dev_calls_per_question_reduction": 0.15099715099715105,
            "dev_hybrid_pair_accuracy_delta_pp": 9.686609686609687,
            "dev_learned_autonomous_pair_precision": 0.8529411764705882,
            "no_model_or_gate_changes_after_dev": True,
        },
        "source": {
            "dataset": "LC-QuAD 2.0",
            "split": "OFFICIAL TEST",
            "url": LCQUAD2_TEST_URL,
            "test_unopened_before_this_prereg": True,
            "use_all_qualifying_rows": True,
            "formal_min_rows": FORMAL_MIN_ROWS,
        },
        "eligibility": [
            "natural_question is non-empty",
            "exactly one distinct wd:Q... in sparql_wikidata",
            "exactly one distinct direct wdt:P... in sparql_wikidata",
            "exactly one explicit direct triple wd:Q... wdt:P... ?variable",
            "PID is in frozen 13,830-property catalog",
            "PID is present in pinned TinyMemory property set of the gold subject",
            "ALL rows satisfying these structural rules are used",
        ],
        "gold_hygiene": (
            "Gold QID/PID are used only for preregistered structural eligibility, "
            "written to GOLD_SEALED, then excluded from ranking, competence "
            "gates, and teacher prompts until all baseline and learned teacher "
            "passes finish."
        ),
        "baseline": {
            "entity_model_sha256": BASE_ENTITY_SHA256,
            "property_model": PROPERTY_MODEL,
            "property_revision": PROPERTY_REVISION,
        },
        "learned": {
            "entity_model_sha256": LEARNED_ENTITY_SHA256,
            "property_model_sha256": LEARNED_PROPERTY_SHA256,
        },
        "entity_policy": {
            "accept_iff_all": [
                "direct Top1 == FINAL Top1",
                "best property evidence rank <=5",
                "selected entity property_count >=20",
            ],
            "entity_evidence_property_model": (
                "frozen BASE property semantic model in both branches"
            ),
        },
        "property_policy": {
            "accept_iff": (
                "lexical subject-conditioned Top1 PID == "
                "neural subject-conditioned Top1 PID"
            ),
            "threshold_tuning": False,
        },
        "teacher": {
            "model": TEACHER_MODEL,
            "revision": TEACHER_REVISION,
            "parameters": TEACHER_PARAMS,
            "real_calls": True,
            "separate_passes_by_branch_and_stage": True,
            "do_sample": False,
        },
        "primary_all_required": {
            "eligible_rows_gte": FORMAL_MIN_ROWS,
            "candidate_recall_gte": PRIMARY_MIN_CANDIDATE_RECALL,
            "calls_per_question_reduction_gte": PRIMARY_MIN_CALL_REDUCTION,
            "learned_hybrid_drop_lte_pp": PRIMARY_MAX_HYBRID_DROP * 100,
            "learned_autonomous_pair_precision_gte":
                PRIMARY_MIN_AUTONOMOUS_PRECISION,
            "learned_autonomous_n_gte": PRIMARY_MIN_AUTONOMOUS_N,
            "guardrails": True,
        },
        "strong_all_required": {
            "calls_per_question_reduction_gte": STRONG_MIN_CALL_REDUCTION,
            "learned_hybrid_accuracy_gte_baseline": True,
            "learned_autonomous_pair_precision_gte":
                STRONG_MIN_AUTONOMOUS_PRECISION,
            "learned_autonomous_n_gte": STRONG_MIN_AUTONOMOUS_N,
            "guardrails": True,
        },
        "guardrails": {
            "training": False,
            "threshold_tuning": False,
            "checkpoint_selection": False,
            "mintaka_test_accessed": False,
            "simplequestions_test_accessed": False,
            "qald10_test_accessed": False,
            "lcquad2_test_accessed_before_prereg": False,
            "posthoc_rescue_forbidden": True,
            "no_second_test_run_for_tuning": True,
        },
        "next_if_primary_pass": (
            "Formal integrated confirmation complete. Freeze result; no more "
            "benchmark tuning. Move to paper/runtime productization."
        ),
        "next_if_primary_fail": (
            "Formal integrated claim fails on this protocol. Report failure; "
            "do not tune or rerun on LC-QuAD 2.0 TEST."
        ),
    }


def run(args: argparse.Namespace) -> int:
    try:
        import duckdb
        import numpy as np
        import torch
        from transformers import AutoConfig,AutoModel,AutoModelForCausalLM,AutoTokenizer
    except Exception as exc:
        raise RuntimeError("Required: duckdb numpy torch transformers scikit-learn") from exc

    script_path=Path(__file__).resolve(); script_sha=sha256_file(script_path)
    if OUTPUT.exists(): shutil.rmtree(OUTPUT)
    OUTPUT.mkdir(parents=True,exist_ok=True)
    log_path=OUTPUT/"RUN_LOG.txt"; dest=None; rc=1

    with log_path.open("w",encoding="utf-8",newline="\n") as log:
        oldout,olderr=sys.stdout,sys.stderr; sys.stdout=Tee(oldout,log); sys.stderr=Tee(olderr,log)
        try:
            print("="*110); print("LC-QUAD 2.0 FORMAL INTEGRATED TEST"); print("="*110)
            print("version:",VERSION); print("started_utc:",utc_now()); print("script_sha256:",script_sha); print("preflight:",json.dumps(preflight(script_path),sort_keys=True))
            prereg=make_prereg(script_sha); write_json(OUTPUT/"PREREG_TEST.json",prereg); print("FORMAL prereg frozen before LC-QuAD 2.0 TEST source access")
            dest=drive_root()/EXPERIMENT; print("drive_output:",dest)

            print("[1] Frozen dependency validation...")
            tm=validate_tinymemory(TINYMEMORY,STATEMENT_ACCEL); print("  TinyMemory:",json.dumps(tm,sort_keys=True))
            source=OUTPUT/"SOURCE"/"lcquad2_test.json"
            print("[2] FIRST ACCESS to official LC-QuAD 2.0 TEST after prereg...")
            download_test_after_prereg(LCQUAD2_TEST_URL, source)
            source_sha=sha256_file(source)
            print("  TEST source SHA256:", source_sha)
            base_entity_dir=resolve_model_dir(BASE_ENTITY_DIRS,"base entity model"); learned_entity_dir=resolve_model_dir(LEARNED_ENTITY_DIRS,"learned entity model"); learned_prop_dir=resolve_model_dir(LEARNED_PROPERTY_DIRS,"learned property model")
            if sha256_file(base_entity_dir/"model.safetensors")!=BASE_ENTITY_SHA256: raise RuntimeError("base entity SHA mismatch")
            if sha256_file(learned_entity_dir/"model.safetensors")!=LEARNED_ENTITY_SHA256: raise RuntimeError("learned entity SHA mismatch")
            for name,sha in [("model.safetensors",LEARNED_PROPERTY_SHA256),("config.json",LEARNED_PROPERTY_CONFIG_SHA256),("tokenizer.json",LEARNED_PROPERTY_TOKENIZER_SHA256),("tokenizer_config.json",LEARNED_PROPERTY_TOKENIZER_CONFIG_SHA256)]:
                p=learned_prop_dir/name
                if not p.is_file() or sha256_file(p)!=sha: raise RuntimeError(f"learned property artifact mismatch {name}")

            properties,aliases=load_property_catalog(TINYMEMORY); valid_pids={p["pid"] for p in properties}; pid_idx={p["pid"]:i for i,p in enumerate(properties)}

            print("[3] Applying preregistered structural TEST eligibility and sealing gold...")
            sample,source_audit=build_formal_test_sample(source,valid_pids)
            sealed=[{"id":r["id"],"question":r["question"],"sample_key":r["sample_key"],"subject_id":r["subject_id"],"gold_pid":r["gold_pid"]} for r in sample]
            runtime_rows=[{"id":r["id"],"question":r["question"],"sample_key":r["sample_key"]} for r in sample]
            write_jsonl(OUTPUT/"GOLD_SEALED.jsonl",sealed); write_jsonl(OUTPUT/"TEST_INPUTS_PRE_GOLD.jsonl",runtime_rows); write_json(OUTPUT/"SOURCE_AUDIT.json",source_audit)
            del sample,sealed; gc.collect()
            # From here until scoring, runtime consumes only question/id/sample_key.
            runtime_rows=load_jsonl(OUTPUT/"TEST_INPUTS_PRE_GOLD.jsonl"); questions=[r["question"] for r in runtime_rows]

            print("[4] Robust exact entity candidates (question text only)...")
            per_candidates,candidate_union,cand_summary=generate_exact_candidates(TINYMEMORY,questions); meta=load_entity_metadata(TINYMEMORY,candidate_union)
            print("  candidate union:",len(candidate_union),"median count:",statistics.median(cand_summary["candidate_counts"]) if cand_summary["candidate_counts"] else 0)

            device="cuda" if args.device=="auto" and torch.cuda.is_available() else ("cpu" if args.device=="auto" else args.device)
            if device=="cuda" and not torch.cuda.is_available(): raise RuntimeError("CUDA requested but unavailable")
            print("  device:",device)

            print("[4] Shared frozen property semantics + base/learned neural property scores...")
            phrase_texts,phrase_indices,pids=build_phrasebank(properties,aliases)
            lexical=make_lexical_scores(questions,properties,aliases)
            base_ptok=AutoTokenizer.from_pretrained(PROPERTY_MODEL,revision=PROPERTY_REVISION,trust_remote_code=False)
            base_pcfg=AutoConfig.from_pretrained(PROPERTY_MODEL,revision=PROPERTY_REVISION,trust_remote_code=False)
            if getattr(base_pcfg,"_commit_hash",None)!=PROPERTY_REVISION: raise RuntimeError("base property revision mismatch")
            base_pmodel=AutoModel.from_pretrained(PROPERTY_MODEL,revision=PROPERTY_REVISION,trust_remote_code=False).to(device).eval()
            if int(sum(p.numel() for p in base_pmodel.parameters()))!=PROPERTY_PARAMS: raise RuntimeError("base property params mismatch")
            print("    base property neural...")
            base_neural=make_neural_scores(questions,phrase_texts,phrase_indices,len(pids),base_ptok,base_pmodel,torch,device,args.property_batch_size)
            del base_pmodel,base_ptok,base_pcfg; gc.collect();
            if device.startswith("cuda"): torch.cuda.empty_cache()

            learned_ptok=AutoTokenizer.from_pretrained(learned_prop_dir,local_files_only=True)
            learned_pmodel=AutoModel.from_pretrained(learned_prop_dir,local_files_only=True).to(device).eval()
            if int(sum(p.numel() for p in learned_pmodel.parameters()))!=PROPERTY_PARAMS: raise RuntimeError("learned property params mismatch")
            print("    learned property neural...")
            learned_neural=make_neural_scores(questions,phrase_texts,phrase_indices,len(pids),learned_ptok,learned_pmodel,torch,device,args.property_batch_size)
            del learned_pmodel,learned_ptok; gc.collect();
            if device.startswith("cuda"): torch.cuda.empty_cache()
            base_global_ranks=ranks_from_scores(1/(RRF_K+ranks_from_scores(lexical).astype(np.float32))+1/(RRF_K+ranks_from_scores(base_neural).astype(np.float32)))

            print("[5] BASELINE and LEARNED entity direct ranking...")
            base_direct,base_entity_info=entity_direct_orders(questions,per_candidates,meta,base_entity_dir,BASE_ENTITY_SHA256,ENTITY_PARAMS,torch,AutoTokenizer,AutoModel,device,args.entity_batch_size)
            learned_direct,learned_entity_info=entity_direct_orders(questions,per_candidates,meta,learned_entity_dir,LEARNED_ENTITY_SHA256,ENTITY_PARAMS,torch,AutoTokenizer,AutoModel,device,args.entity_batch_size)
            shortlist_union=sorted({q for order in base_direct+learned_direct for q in order[:EVIDENCE_TOPK]})
            print("[6] Verified TinyMemory property sets for entity evidence...")
            subject_props=load_subject_property_sets(STATEMENT_ACCEL,shortlist_union,valid_pids)
            base_entity_rank=entity_final_rankings(base_direct,subject_props,base_global_ranks,pid_idx)
            learned_entity_rank=entity_final_rankings(learned_direct,subject_props,base_global_ranks,pid_idx)
            write_jsonl(OUTPUT/"BASELINE_ENTITY_PRE_TEACHER.jsonl",[{**runtime_rows[i],**r} for i,r in enumerate(base_entity_rank)])
            write_jsonl(OUTPUT/"LEARNED_ENTITY_PRE_TEACHER.jsonl",[{**runtime_rows[i],**r} for i,r in enumerate(learned_entity_rank)])

            base_entity_tasks=make_entity_teacher_tasks(runtime_rows,base_entity_rank,meta,"BASELINE")
            learned_entity_tasks=make_entity_teacher_tasks(runtime_rows,learned_entity_rank,meta,"LEARNED")
            print(f"  entity real calls planned baseline={len(base_entity_tasks)} learned={len(learned_entity_tasks)}")

            print("[7] Loading exact Qwen teacher; separate REAL entity passes...")
            os.environ.setdefault("HF_HUB_DISABLE_XET","1")
            qtok=AutoTokenizer.from_pretrained(TEACHER_MODEL,revision=TEACHER_REVISION,trust_remote_code=False)
            qcfg=AutoConfig.from_pretrained(TEACHER_MODEL,revision=TEACHER_REVISION,trust_remote_code=False)
            qmodel=AutoModelForCausalLM.from_pretrained(TEACHER_MODEL,revision=TEACHER_REVISION,trust_remote_code=False,torch_dtype=(torch.bfloat16 if device=="cuda" and torch.cuda.is_bf16_supported() else (torch.float16 if device=="cuda" else torch.float32)),low_cpu_mem_usage=True).to(device).eval()
            if getattr(qcfg,"_commit_hash",None)!=TEACHER_REVISION: raise RuntimeError("teacher revision mismatch")
            if int(sum(p.numel() for p in qmodel.parameters()))!=TEACHER_PARAMS: raise RuntimeError("teacher parameter count mismatch")
            t0=time.perf_counter(); teacher_infer(base_entity_tasks,"entity",qtok,qmodel,torch,device,args.teacher_batch_size); t_base_entity=time.perf_counter()-t0
            t0=time.perf_counter(); teacher_infer(learned_entity_tasks,"entity",qtok,qmodel,torch,device,args.teacher_batch_size); t_learned_entity=time.perf_counter()-t0
            write_jsonl(OUTPUT/"BASELINE_ENTITY_TEACHER_PRE_GOLD.jsonl",base_entity_tasks); write_jsonl(OUTPUT/"LEARNED_ENTITY_TEACHER_PRE_GOLD.jsonl",learned_entity_tasks)
            base_subjects,base_entity_calls=resolve_entity_subjects(base_entity_rank,base_entity_tasks); learned_subjects,learned_entity_calls=resolve_entity_subjects(learned_entity_rank,learned_entity_tasks)

            print("[9] Subject-conditioned property rankings using resolved subjects...")
            resolved_union=sorted(set(q for q in base_subjects+learned_subjects if q))
            missing_subjects=[q for q in resolved_union if q not in subject_props]
            if missing_subjects:
                extra=load_subject_property_sets(STATEMENT_ACCEL,missing_subjects,valid_pids); subject_props.update(extra)
            base_property_rank=property_rankings(questions,base_subjects,subject_props,properties,lexical,base_neural)
            learned_property_rank=property_rankings(questions,learned_subjects,subject_props,properties,lexical,learned_neural)
            write_jsonl(OUTPUT/"BASELINE_PROPERTY_PRE_TEACHER.jsonl",[{**runtime_rows[i],**r} for i,r in enumerate(base_property_rank)])
            write_jsonl(OUTPUT/"LEARNED_PROPERTY_PRE_TEACHER.jsonl",[{**runtime_rows[i],**r} for i,r in enumerate(learned_property_rank)])
            base_prop_tasks=make_property_teacher_tasks(runtime_rows,base_property_rank,"BASELINE"); learned_prop_tasks=make_property_teacher_tasks(runtime_rows,learned_property_rank,"LEARNED")
            print(f"  property real calls planned baseline={len(base_prop_tasks)} learned={len(learned_prop_tasks)}")

            print("[10] Separate REAL property teacher passes...")
            t0=time.perf_counter(); teacher_infer(base_prop_tasks,"property",qtok,qmodel,torch,device,args.teacher_batch_size); t_base_prop=time.perf_counter()-t0
            t0=time.perf_counter(); teacher_infer(learned_prop_tasks,"property",qtok,qmodel,torch,device,args.teacher_batch_size); t_learned_prop=time.perf_counter()-t0
            write_jsonl(OUTPUT/"BASELINE_PROPERTY_TEACHER_PRE_GOLD.jsonl",base_prop_tasks); write_jsonl(OUTPUT/"LEARNED_PROPERTY_TEACHER_PRE_GOLD.jsonl",learned_prop_tasks)
            base_pids,base_prop_calls=resolve_properties(base_property_rank,base_prop_tasks); learned_pids,learned_prop_calls=resolve_properties(learned_property_rank,learned_prop_tasks)

            teacher_config={"model":TEACHER_MODEL,"revision":TEACHER_REVISION,"commit_hash":getattr(qcfg,"_commit_hash",None),"parameter_count":TEACHER_PARAMS,"device":device,"do_sample":False,"max_prompt_tokens":MAX_PROMPT_TOKENS,"max_new_tokens":MAX_NEW_TOKENS,"passes":{"baseline_entity_seconds":t_base_entity,"learned_entity_seconds":t_learned_entity,"baseline_property_seconds":t_base_prop,"learned_property_seconds":t_learned_prop}}
            write_json(OUTPUT/"TEACHER_CONFIG.json",teacher_config)
            del qmodel,qtok,qcfg; gc.collect();
            if device.startswith("cuda"): torch.cuda.empty_cache()

            print("[11] ALL inference finished. Reloading sealed gold for scoring ONLY NOW...")
            gold_rows=load_jsonl(OUTPUT/"GOLD_SEALED.jsonl"); gold={r["id"]:r for r in gold_rows}
            candidate_recall=sum(gold[r["id"]]["subject_id"] in per_candidates[i] for i,r in enumerate(runtime_rows))/len(runtime_rows)
            base_metrics,base_trace=score_branch("BASELINE",runtime_rows,gold,base_entity_rank,base_subjects,base_entity_calls,base_property_rank,base_pids,base_prop_calls,per_candidates)
            learned_metrics,learned_trace=score_branch("LEARNED",runtime_rows,gold,learned_entity_rank,learned_subjects,learned_entity_calls,learned_property_rank,learned_pids,learned_prop_calls,per_candidates)
            write_jsonl(OUTPUT/"BASELINE_END_TO_END_TRACES.jsonl",base_trace); write_jsonl(OUTPUT/"LEARNED_END_TO_END_TRACES.jsonl",learned_trace)

            call_reduction=base_metrics["calls_per_question"]-learned_metrics["calls_per_question"]
            hybrid_delta=learned_metrics["hybrid_pair_accuracy"]-base_metrics["hybrid_pair_accuracy"]
            lp=learned_metrics["autonomous_zero_call_pair_precision"] or 0.0; ln=learned_metrics["autonomous_zero_call_n"]
            guardrails={"training":False,"threshold_tuning":False,"checkpoint_selection":False,"mintaka_test_accessed":False,"simplequestions_test_accessed":False,"qald10_test_accessed":False,"lcquad2_test_accessed":True,"lcquad2_test_accessed_only_after_prereg":True,"formal_test_claim":True,"gold_excluded_from_ranking_and_teacher_after_structural_sealing":True,"separate_real_teacher_passes":True,"posthoc_rescue":False,"second_test_run_for_tuning":False}
            guardrails_pass=(
                guardrails["training"] is False
                and guardrails["threshold_tuning"] is False
                and guardrails["checkpoint_selection"] is False
                and guardrails["mintaka_test_accessed"] is False
                and guardrails["simplequestions_test_accessed"] is False
                and guardrails["qald10_test_accessed"] is False
                and guardrails["lcquad2_test_accessed"] is True
                and guardrails["lcquad2_test_accessed_only_after_prereg"] is True
                and guardrails["formal_test_claim"] is True
                and guardrails["gold_excluded_from_ranking_and_teacher_after_structural_sealing"] is True
                and guardrails["separate_real_teacher_passes"] is True
                and guardrails["posthoc_rescue"] is False
                and guardrails["second_test_run_for_tuning"] is False
            )
            primary_conditions={"eligible_rows_gte_100":len(runtime_rows)>=FORMAL_MIN_ROWS,"candidate_recall_gte_060":candidate_recall>=PRIMARY_MIN_CANDIDATE_RECALL,"calls_per_question_reduction_gte_005":call_reduction>=PRIMARY_MIN_CALL_REDUCTION,"learned_hybrid_drop_lte_1pp":hybrid_delta>=-PRIMARY_MAX_HYBRID_DROP,"learned_autonomous_pair_precision_gte_085":lp>=PRIMARY_MIN_AUTONOMOUS_PRECISION,"learned_autonomous_n_gte_20":ln>=PRIMARY_MIN_AUTONOMOUS_N,"guardrails":guardrails_pass}
            strong_conditions={"calls_per_question_reduction_gte_010":call_reduction>=STRONG_MIN_CALL_REDUCTION,"learned_hybrid_accuracy_gte_baseline":hybrid_delta>=0,"learned_autonomous_pair_precision_gte_090":lp>=STRONG_MIN_AUTONOMOUS_PRECISION,"learned_autonomous_n_gte_40":ln>=STRONG_MIN_AUTONOMOUS_N,"primary_integrity":primary_conditions["eligible_rows_gte_100"] and primary_conditions["candidate_recall_gte_060"] and primary_conditions["guardrails"]}
            primary_pass=all(primary_conditions.values()); strong_pass=all(strong_conditions.values())
            result={"version":VERSION,"status":"INTEGRATED_END_TO_END_FORMAL_TEST_COMPLETE","completed_utc":utc_now(),"script_sha256":script_sha,"source":{"dataset":"LC-QuAD 2.0","split":"OFFICIAL TEST","url":LCQUAD2_TEST_URL,"sha256":source_sha,"sample_audit":source_audit,"eval_rows":len(runtime_rows),"candidate_recall":candidate_recall,"test_inputs_sha256":sha256_file(OUTPUT/"TEST_INPUTS_PRE_GOLD.jsonl"),"gold_sealed_sha256":sha256_file(OUTPUT/"GOLD_SEALED.jsonl")},"models":{"base_entity":base_entity_info,"learned_entity":learned_entity_info,"learned_property_sha256":LEARNED_PROPERTY_SHA256,"property_base_revision":PROPERTY_REVISION},"teacher":teacher_config,"baseline":base_metrics,"learned":learned_metrics,"effect":{"real_qwen_calls_saved":base_metrics["total_real_qwen_calls"]-learned_metrics["total_real_qwen_calls"],"calls_per_question_reduction":call_reduction,"hybrid_pair_accuracy_delta_pp":100*hybrid_delta,"autonomous_zero_call_coverage_delta_pp":100*(learned_metrics["autonomous_zero_call_coverage"]-base_metrics["autonomous_zero_call_coverage"])},"primary_test":{"conditions":primary_conditions,"pass":primary_pass},"strong_test":{"conditions":strong_conditions,"pass":strong_pass},"guardrails":guardrails,"next_step":prereg["next_if_primary_pass"] if primary_pass else prereg["next_if_primary_fail"]}
            write_json(OUTPUT/"RESULT.json",result); shutil.copy2(script_path,OUTPUT/"SCRIPT_SNAPSHOT.py")
            print("candidate_recall:",candidate_recall); print("BASELINE:",json.dumps(base_metrics,sort_keys=True)); print("LEARNED:",json.dumps(learned_metrics,sort_keys=True)); print("EFFECT:",json.dumps(result["effect"],sort_keys=True)); print("PRIMARY FORMAL TEST PASS:",primary_pass); print("STRONG FORMAL TEST PASS:",strong_pass); print("next_step:",result["next_step"]); print("="*110); print("LC-QUAD 2.0 FORMAL INTEGRATED TEST: COMPLETE"); print("="*110)
            rc=0
        except Exception as exc:
            traceback.print_exc()
            try:
                shutil.copy2(script_path,OUTPUT/"SCRIPT_SNAPSHOT.py")
                write_json(OUTPUT/"RESULT.json",{"version":VERSION,"status":"ERROR","completed_utc":utc_now(),"script_sha256":script_sha,"error_type":type(exc).__name__,"error":str(exc),"guardrails":{"mintaka_test_accessed":False,"simplequestions_test_accessed":False,"qald10_test_accessed":False,"lcquad2_test_may_have_been_accessed_after_prereg":(OUTPUT/"SOURCE"/"lcquad2_test.json").exists(),"training":False,"threshold_tuning":False,"posthoc_rescue":False}})
            except Exception: traceback.print_exc()
        finally:
            sys.stdout=oldout; sys.stderr=olderr

    write_json(OUTPUT/"ARTIFACT_MANIFEST.json",build_manifest(OUTPUT))
    try:
        if dest is None: dest=drive_root()/EXPERIMENT
        mirror_tree(OUTPUT,dest); print("Google Drive mirror:",dest)
    except Exception:
        traceback.print_exc(); print("Google Drive mirror: FAILED")
    return rc


def cli() -> argparse.Namespace:
    p=argparse.ArgumentParser(); p.add_argument("--device",default="auto",choices=["auto","cuda","cpu"]); p.add_argument("--entity-batch-size",type=int,default=128); p.add_argument("--property-batch-size",type=int,default=256); p.add_argument("--teacher-batch-size",type=int,default=16); return p.parse_args()


if __name__ == "__main__":
    raise SystemExit(run(cli()))
