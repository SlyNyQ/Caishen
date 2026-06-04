"""Build retrieval-ready JSONL chunks from Caishen Markdown research notes."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import logging
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Caishen knowledge-base chunks.")
    parser.add_argument("--input-dir", default="backend/kb/raw_docs")
    parser.add_argument("--output-dir", default="backend/kb/processed_docs")
    parser.add_argument("--metadata-dir", default="backend/kb/metadata")
    parser.add_argument("--chunk-size", type=int, default=1000)
    parser.add_argument("--chunk-overlap", type=int, default=160)
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args()


def split_into_chunks(text: str, *, chunk_size: int, chunk_overlap: int) -> list[str]:
    normalized = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if not normalized:
        return []
    overlap = max(0, min(chunk_overlap, chunk_size - 1))
    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        target_end = min(len(normalized), start + chunk_size)
        end = target_end
        if target_end < len(normalized):
            boundary = max(
                normalized.rfind("\n", start, target_end),
                normalized.rfind(" ", start, target_end),
            )
            if boundary > start + (chunk_size // 2):
                end = boundary
        chunk = normalized[start:end].strip()
        if chunk and (not chunks or chunks[-1] != chunk):
            chunks.append(chunk)
        if end >= len(normalized):
            break
        start = max(end - overlap, start + 1)
    return chunks


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(levelname)s %(message)s",
    )
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    metadata_dir = Path(args.metadata_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, object]] = []
    documents: list[str] = []
    for path in sorted(input_dir.rglob("*.md")):
        relative_path = path.relative_to(input_dir).as_posix()
        text = path.read_text(encoding="utf-8")
        chunks = split_into_chunks(
            text,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
        )
        if not chunks:
            logging.warning("Skipping empty source: %s", relative_path)
            continue
        documents.append(relative_path)
        title = path.stem.replace("_", " ").title()
        for index, chunk in enumerate(chunks):
            records.append(
                {
                    "doc_id": relative_path.replace("/", "_").replace(".", "_"),
                    "chunk_id": index,
                    "title": title,
                    "text": chunk,
                    "metadata": {
                        "source_path": relative_path,
                        "type": path.parent.name,
                    },
                }
            )

    chunks_path = output_dir / "chunks.jsonl"
    chunks_path.write_text(
        "".join(json.dumps(record, ensure_ascii=True) + "\n" for record in records),
        encoding="utf-8",
    )
    manifest = {
        "build_id": datetime.now(timezone.utc).strftime("caishen_kb_%Y%m%dT%H%M%SZ"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "documents": documents,
        "chunk_count": len(records),
    }
    (metadata_dir / "kb_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    logging.info("Caishen KB build complete: %s documents, %s chunks", len(documents), len(records))


if __name__ == "__main__":
    main()
