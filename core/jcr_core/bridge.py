"""Bridge: ingest existing SINT memory blocks into the libido ledger.

The JCR ledger should not start empty — the ecosystem already has thousands of
hash-chained memory blocks (`~/.opencode/memory/chain.jsonl`). This connects
them, preserving provenance, and verifies the source hash-chain so an imported
node can be traced.

Import is idempotent: a node already present for a block id is skipped unless
``force`` is set.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterator

from jcr_core.ledger import LibidoLedger
from jcr_core.types import Register

DEFAULT_CHAIN = Path.home() / ".opencode" / "memory" / "chain.jsonl"
MAX_CONTENT = 2000


def source_hash(block_id: str, register: str, content: str, prev_hash: str) -> str:
    """Reproduce the sint-memory hash convention (sha256[:16])."""
    payload = f"{block_id}:{register}:{content}:{prev_hash}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def load_blocks(path: str | Path = DEFAULT_CHAIN) -> Iterator[dict]:
    p = Path(path).expanduser()
    if not p.exists():
        return
    with p.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def verify_source_chain(path: str | Path = DEFAULT_CHAIN) -> dict:
    prev = "0" * 16
    checked = 0
    for b in load_blocks(path):
        expect = source_hash(b.get("id", ""), b.get("register", ""), b.get("content", ""), prev)
        if b.get("prev_hash") != prev or b.get("hash") != expect:
            return {"ok": False, "checked": checked, "broken_at": b.get("id")}
        prev = b["hash"]
        checked += 1
    return {"ok": True, "checked": checked, "broken_at": None}


def _register(value: str) -> Register:
    try:
        return Register[str(value).upper()]
    except KeyError:
        return Register.SENSE


def import_chain(
    ledger: LibidoLedger,
    path: str | Path = DEFAULT_CHAIN,
    limit: int | None = None,
    force: bool = False,
    max_content: int = MAX_CONTENT,
) -> dict:
    imported = skipped = 0
    for b in load_blocks(path):
        if limit is not None and imported + skipped >= limit:
            break
        node_id = f"n_mem{b.get('id', '')}"
        if not force and ledger.get_node(node_id) is not None:
            skipped += 1
            continue
        content = str(b.get("content", ""))[:max_content]
        ledger.add_node(
            content=content,
            register=_register(b.get("register", "SENSE")),
            project=str(b.get("project", "SYSTEM")),
            energy=float(b.get("confidence", 0.6)) * 0.6 + 0.2,
            node_id=node_id,
            provenance={
                "source": "sint-memory",
                "block_id": b.get("id"),
                "hash": b.get("hash"),
                "tags": b.get("tags", []),
                "truncated": len(str(b.get("content", ""))) > max_content,
            },
        )
        imported += 1
    return {"imported": imported, "skipped": skipped, "ledger": ledger.stats()}


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    from jcr_core.runtime import Runtime

    ap = argparse.ArgumentParser(description="Import sint-memory chain into the JCR ledger")
    ap.add_argument("--chain", default=str(DEFAULT_CHAIN))
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--verify-only", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)

    if args.verify_only:
        print(json.dumps(verify_source_chain(args.chain), indent=2))
        return 0

    rt = Runtime()
    try:
        print(json.dumps(verify_source_chain(args.chain), indent=2))
        print(json.dumps(import_chain(rt.ledger, args.chain, limit=args.limit, force=args.force), indent=2))
    finally:
        rt.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
