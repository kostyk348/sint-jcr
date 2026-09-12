"""Consolidation — one authority per layer (docs/13-mcp-review.md).

Two jobs:

* **Identity.** The Character Ledger is the authority (it has evidence and
  drift). This module exports it, audits divergence against `sint-self`, and
  mirrors traits into `sint-self` *only when given an embedder* — because
  `sint-self` recall breaks on NULL embeddings, a blind insert would corrupt it.
* **Memory format.** Export `sint-memory` blocks as EML-IPC `.eml`, so the
  memory store and the JCR bus converge on one hash-chained format.
"""

from __future__ import annotations

import json
import sqlite3
import struct
from pathlib import Path

from jcr_core.character import CharacterLedger

IDENTITY_TAG = "jcr-trait"
IDENTITY_SOURCE = "jcr-character"


def export_identity(character: CharacterLedger) -> dict:
    """Canonical identity export from the authority (Character Ledger)."""
    return {
        "authority": "jcr-character-ledger",
        "traits": [
            {"statement": t.statement, "weight": t.weight, "scope": t.scope, "polarity": t.polarity}
            for t in character.all_traits()
        ],
        "drift": character.drift(),
    }


def _self_rows(self_db_path: str | Path) -> list[dict]:
    p = Path(self_db_path).expanduser()
    if not p.exists():
        return []
    conn = sqlite3.connect(str(p))
    try:
        rows = conn.execute(
            "SELECT id, text, tag, source FROM self WHERE tag = ?", (IDENTITY_TAG,)
        ).fetchall()
    finally:
        conn.close()
    return [{"id": r[0], "text": r[1], "tag": r[2], "source": r[3]} for r in rows]


def audit_identity(character: CharacterLedger, self_db_path: str | Path) -> dict:
    """Read-only divergence report between the two identity stores."""
    traits = {t.statement: t for t in character.all_traits()}
    mirrored = {r["text"]: r for r in _self_rows(self_db_path)}
    missing = [s for s in traits if s not in mirrored]
    stale = [s for s in mirrored if s not in traits]
    counts: dict[str, int] = {}
    for r in _self_rows(self_db_path):
        counts[r["text"]] = counts.get(r["text"], 0) + 1
    duplicates = [s for s, n in counts.items() if n > 1]
    return {
        "authority_traits": len(traits),
        "mirrored": len(mirrored),
        "missing_in_self": missing,
        "stale_in_self": stale,
        "duplicates": duplicates,
        "consistent": not (missing or stale or duplicates),
    }


def mirror_identity(
    character: CharacterLedger,
    self_db_path: str | Path,
    embed_fn=None,
    dry_run: bool = True,
) -> dict:
    """Mirror traits into sint-self.

    Without ``embed_fn`` this is a *plan only* (no write): a NULL embedding would
    break sint-self's cosine recall. Pass sint-self's own ``embed`` to apply.
    """
    p = Path(self_db_path).expanduser()
    traits = character.all_traits()
    existing = {r["text"] for r in _self_rows(p)}
    to_add = [t for t in traits if t.statement not in existing]
    plan = {"to_add": [t.statement for t in to_add], "already": len(existing), "applied": False}
    if dry_run or embed_fn is None or not p.exists():
        return plan

    conn = sqlite3.connect(str(p))
    try:
        for t in to_add:
            emb = embed_fn(t.statement)
            blob = struct.pack(f"<{len(emb)}f", *emb)
            conn.execute(
                "INSERT INTO self(text, tag, source, voice, emb, created_at) VALUES(?,?,?,?,?,datetime('now'))",
                (t.statement, IDENTITY_TAG, IDENTITY_SOURCE, "any", blob),
            )
        conn.commit()
    finally:
        conn.close()
    plan["applied"] = True
    return plan


# ------------------------------------------------------------------ memory


def memory_to_eml(chain_path: str | Path, out_dir: str | Path, limit: int | None = None) -> dict:
    """Export sint-memory blocks as EML-IPC `.eml` messages (format convergence)."""
    src = Path(chain_path).expanduser()
    out = Path(out_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    written = 0
    if not src.exists():
        return {"written": 0, "out_dir": str(out)}
    with src.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            if limit is not None and written >= limit:
                break
            try:
                b = json.loads(line)
            except json.JSONDecodeError:
                continue
            body = json.dumps(
                {"content": b.get("content", ""), "register": b.get("register"), "project": b.get("project")},
                ensure_ascii=False,
                sort_keys=True,
            )
            text = (
                "From: <sint-memory@localhost>\n"
                "To: <jcr-core@localhost>\n"
                "X-EMLBox-Msg: v1\n"
                f"X-Event: memory_block\n"
                f"X-JCR-Block-ID: {b.get('id', '')}\n"
                f"X-JCR-Register: {b.get('register', '')}\n"
                f"X-JCR-Project: {b.get('project', '')}\n"
                f"X-JCR-Prev-Hash: {b.get('prev_hash', '')}\n"
                f"X-JCR-Hash: {b.get('hash', '')}\n"
                f"Message-ID: <block{b.get('id', '')}@sint-memory>\n"
                "Content-Type: application/json; charset=utf-8\n"
                "\n"
                f"{body}\n"
            )
            name = f"{str(b.get('id', written)).zfill(6)}.{b.get('register', 'X')}.msg.eml"
            (out / name).write_text(text, encoding="utf-8")
            written += 1
    return {"written": written, "out_dir": str(out)}


def main(argv: list[str] | None = None) -> int:
    import argparse

    from jcr_core.bridge import DEFAULT_CHAIN
    from jcr_core.runtime import Runtime

    ap = argparse.ArgumentParser(description="JCR consolidation utilities")
    ap.add_argument("--identity", action="store_true", help="export canonical identity JSON")
    ap.add_argument("--audit", metavar="SELF_DB", help="audit divergence against sint-self db")
    ap.add_argument("--memory-eml", metavar="OUT_DIR", help="export sint-memory chain as .eml")
    ap.add_argument("--chain", default=str(DEFAULT_CHAIN))
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args(argv)

    rt = Runtime()
    try:
        if args.identity:
            print(json.dumps(export_identity(rt.character), indent=2))
        if args.audit:
            print(json.dumps(audit_identity(rt.character, args.audit), indent=2))
        if args.memory_eml:
            print(json.dumps(memory_to_eml(args.chain, args.memory_eml, args.limit), indent=2))
    finally:
        rt.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
