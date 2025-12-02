"""
Command-line interface for comparing Explora Lang programs via embeddings.

Usage example:

    python -m explora_similarity.cli path/to/a.exp path/to/b.exp
"""

from __future__ import annotations

import argparse
from typing import Sequence

import torch
from tqdm import tqdm

from .explora_similarity import DEFAULT_MAX_LENGTH, CodeT5EmbeddingService


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compute similarity between two Explora Lang programs using Salesforce CodeT5p.",
    )
    parser.add_argument("program_a", help="First Explora program (code string or file path).")
    parser.add_argument("program_b", help="Second Explora program (code string or file path).")
    parser.add_argument(
        "--cache-dir",
        default=None,
        help="Optional Hugging Face cache directory for model downloads.",
    )
    parser.add_argument(
        "--device",
        default=None,
        help="Force computation device (e.g., 'cuda', 'cpu'). Defaults to auto-detection.",
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=DEFAULT_MAX_LENGTH,
        help=f"Maximum tokenized length (default: {DEFAULT_MAX_LENGTH}).",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Print only the raw float value instead of a descriptive sentence.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    print(f"Comparing {args.program_a} vs {args.program_b}", flush=True)

    total_steps = 4
    with tqdm(total=total_steps, ncols=80, desc="Loading service") as progress:
        service = CodeT5EmbeddingService(
            cache_dir=args.cache_dir,
            device=args.device,
            max_length=args.max_length,
        )
        progress.update(1)

        progress.set_description("Embedding program A")
        embedding_a = service.embed(args.program_a)
        progress.update(1)

        progress.set_description("Embedding program B")
        embedding_b = service.embed(args.program_b)
        progress.update(1)

        progress.set_description("Computing similarity")
        similarity = float(
            torch.nn.functional.cosine_similarity(
                embedding_a,
                embedding_b,
                dim=0,
            ).item()
        )
        progress.update(1)

    if args.raw:
        print(similarity, flush=True)
    else:
        print(f"Cosine similarity: {similarity:.6f}", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

