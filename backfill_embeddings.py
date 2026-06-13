#!/usr/bin/env python3
"""
Backfill embeddings for existing buckets.
为存量桶批量生成 embedding。

Usage:
    OMBRE_BUCKETS_DIR=/data OMBRE_API_KEY=xxx python backfill_embeddings.py [--batch-size 20] [--dry-run] [--force]

Options:
    --force      Force regenerate ALL embeddings (use after switching embedding model)
    --dry-run    Show what would be done without actually doing it
    --batch-size Number of buckets per batch (default: 20)

Each batch calls Gemini embedding API once per bucket.
Free tier: 1500 requests/day, so ~75 batches of 20.
"""

import asyncio
import argparse
import sys

sys.path.insert(0, ".")
from utils import load_config
from bucket_manager import BucketManager
from embedding_engine import EmbeddingEngine


async def _detect_expected_dim(engine: EmbeddingEngine) -> int | None:
    """Generate a test embedding to detect the current model's dimension."""
    try:
        test_emb = await engine._generate_embedding("dimension check")
        if test_emb:
            return len(test_emb)
    except Exception:
        pass
    return None


async def backfill(batch_size: int = 20, dry_run: bool = False, force: bool = False):
    config = load_config()
    bucket_mgr = BucketManager(config)
    engine = EmbeddingEngine(config)

    if not engine.enabled:
        print("ERROR: Embedding engine not enabled (missing API key?)")
        return

    # Detect current model's embedding dimension
    expected_dim = await _detect_expected_dim(engine)
    if expected_dim:
        print(f"Current embedding model: {engine.model} ({expected_dim}-dim)")
    else:
        print(f"WARNING: Could not detect embedding dimension for {engine.model}")

    all_buckets = await bucket_mgr.list_all(include_archive=True)
    print(f"Total buckets: {len(all_buckets)}")

    # Find buckets that need (re)embedding
    needs_embed = []
    dim_mismatch = 0
    no_embedding = 0

    for b in all_buckets:
        emb = await engine.get_embedding(b["id"])
        if emb is None:
            needs_embed.append(b)
            no_embedding += 1
        elif force:
            needs_embed.append(b)
        elif expected_dim and len(emb) != expected_dim:
            needs_embed.append(b)
            dim_mismatch += 1

    print(f"Need embedding: {len(needs_embed)} (missing: {no_embedding}, dim mismatch: {dim_mismatch}, force: {len(needs_embed) - no_embedding - dim_mismatch})")

    if dry_run:
        for b in needs_embed[:20]:
            emb = await engine.get_embedding(b["id"])
            status = "missing" if emb is None else f"dim={len(emb)}" if emb else "empty"
            name = b['metadata'].get('name', '?')
            pinned = " 📌" if b['metadata'].get('pinned') else ""
            print(f"  would embed: {b['id'][:12]} ({name[:40]}){pinned} [{status}]")
        if len(needs_embed) > 20:
            print(f"  ... and {len(needs_embed) - 20} more")
        return

    total = len(needs_embed)
    if total == 0:
        print("All embeddings are up to date!")
        return

    success = 0
    failed = 0

    for i in range(0, total, batch_size):
        batch = needs_embed[i : i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (total + batch_size - 1) // batch_size
        print(f"\n--- Batch {batch_num}/{total_batches} ({len(batch)} buckets) ---")

        for b in batch:
            name = b["metadata"].get("name", b["id"])
            content = b.get("content", "")
            if not content or not content.strip():
                print(f"  SKIP (empty): {b['id'][:12]} ({name[:30]})")
                continue

            try:
                ok = await engine.generate_and_store(b["id"], content)
                if ok:
                    success += 1
                    print(f"  OK: {b['id'][:12]} ({name[:30]})")
                else:
                    failed += 1
                    print(f"  FAIL: {b['id'][:12]} ({name[:30]})")
            except Exception as e:
                failed += 1
                print(f"  ERROR: {b['id'][:12]} ({name[:30]}): {e}")

        if i + batch_size < total:
            print("  Waiting 2s before next batch...")
            await asyncio.sleep(2)

    print(f"\n=== Done: {success} success, {failed} failed, {total - success - failed} skipped ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill embeddings for Ombre Brain buckets")
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    parser.add_argument("--force", action="store_true", help="Force regenerate ALL embeddings (use after model switch)")
    args = parser.parse_args()
    asyncio.run(backfill(batch_size=args.batch_size, dry_run=args.dry_run, force=args.force))
