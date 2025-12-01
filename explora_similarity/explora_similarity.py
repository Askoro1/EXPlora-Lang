from __future__ import annotations

from pathlib import Path
from threading import Lock
from typing import Optional, Union

import torch
from torch import Tensor
from transformers import AutoModel, AutoTokenizer, PreTrainedModel, PreTrainedTokenizerBase

MODEL_NAME = "Salesforce/codet5p-110m-embedding"
DEFAULT_MAX_LENGTH = 1024

ProgramSource = Union[str, Path]


def _read_program_source(source: ProgramSource) -> str:
    if isinstance(source, Path):
        return source.read_text(encoding="utf-8")

    potential_path = Path(source)
    if potential_path.exists():
        return potential_path.read_text(encoding="utf-8")

    return source


class CodeT5EmbeddingService:
    def __init__(
        self,
        model_name: str = MODEL_NAME,
        *,
        cache_dir: Optional[str] = None,
        device: Optional[str] = None,
        max_length: int = DEFAULT_MAX_LENGTH,
    ) -> None:
        self.model_name = model_name
        self.cache_dir = cache_dir
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.max_length = max_length

        self._tokenizer: Optional[PreTrainedTokenizerBase] = None
        self._model: Optional[PreTrainedModel] = None
        self._lock = Lock()

    def _ensure_ready(self) -> None:
        if self._tokenizer is not None and self._model is not None:
            return

        with self._lock:
            if self._tokenizer is None or self._model is None:
                tokenizer = AutoTokenizer.from_pretrained(
                    self.model_name,
                    cache_dir=self.cache_dir,
                    use_fast=True,
                    trust_remote_code=True,
                )
                model = AutoModel.from_pretrained(
                    self.model_name,
                    cache_dir=self.cache_dir,
                    trust_remote_code=True,
                )
                model.to(self.device)
                model.eval()
                self._tokenizer = tokenizer
                self._model = model

    def embed(self, program: ProgramSource) -> Tensor:
        """
        Convert a program (string literal or path) into a normalized embedding vector.
        """
        self._ensure_ready()
        assert self._tokenizer is not None and self._model is not None

        program_text = _read_program_source(program)
        inputs = self._tokenizer(
            program_text,
            return_tensors="pt",
            truncation=True,
            max_length=self.max_length,
        )
        inputs = {key: value.to(self.device) for key, value in inputs.items()}

        with torch.no_grad():
            outputs = self._model(**inputs)

        if hasattr(outputs, "last_hidden_state"):
            hidden_state = outputs.last_hidden_state
        elif isinstance(outputs, (tuple, list)):
            hidden_state = outputs[0]
        else:
            hidden_state = outputs

        if hidden_state.dim() == 3:
            # BaseModelOutput: mean-pool over the sequence dimension.
            embedding = hidden_state.mean(dim=1).squeeze(0)
        elif hidden_state.dim() == 2:
            # Already pooled embeddings (batch, hidden_dim).
            embedding = hidden_state.squeeze(0)
        else:
            raise ValueError("Unexpected embedding shape returned by the model.")

        normalized = torch.nn.functional.normalize(embedding, p=2, dim=0)
        return normalized.cpu()


_DEFAULT_SERVICE: Optional[CodeT5EmbeddingService] = None


def _get_default_service() -> CodeT5EmbeddingService:
    global _DEFAULT_SERVICE
    if _DEFAULT_SERVICE is None:
        _DEFAULT_SERVICE = CodeT5EmbeddingService()
    return _DEFAULT_SERVICE


def compare_programs(
    code_a: ProgramSource,
    code_b: ProgramSource,
    *,
    service: Optional[CodeT5EmbeddingService] = None,
) -> float:
    """
    Public API that returns cosine similarity between two Explora programs.
    """
    svc = service or _get_default_service()
    embedding_a = svc.embed(code_a)
    embedding_b = svc.embed(code_b)
    similarity = torch.nn.functional.cosine_similarity(
        embedding_a,
        embedding_b,
        dim=0,
    )
    return similarity.item()

