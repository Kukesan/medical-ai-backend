import json
from pathlib import Path

import faiss
import numpy as np

from app.core.config import settings


class FaissStore:
    def __init__(self, dim: int = 1536) -> None:
        self.dim = dim
        self.index_path = settings.faiss_index_path / "medical.index"
        self.meta_path = settings.faiss_index_path / "medical_meta.json"

        if self.index_path.exists():
            self.index = faiss.read_index(str(self.index_path))
        else:
            self.index = faiss.IndexFlatIP(dim)

        if self.meta_path.exists():
            self.metadata = json.loads(self.meta_path.read_text(encoding="utf-8"))
        else:
            self.metadata = []

    def add(self, vectors: list[list[float]], metadatas: list[dict]) -> list[int]:
        arr = np.array(vectors, dtype="float32")
        faiss.normalize_L2(arr)
        start = self.index.ntotal
        self.index.add(arr)
        positions = list(range(start, start + len(vectors)))
        self.metadata.extend(metadatas)
        self._persist()
        return positions

    def search(self, query_vector: list[float], top_k: int = 5) -> list[dict]:
        if self.index.ntotal == 0:
            return []
        arr = np.array([query_vector], dtype="float32")
        faiss.normalize_L2(arr)
        scores, indices = self.index.search(arr, top_k)

        hits: list[dict] = []
        for score, idx in zip(scores[0], indices[0], strict=False):
            if idx == -1 or idx >= len(self.metadata):
                continue
            hits.append({"score": float(score), "metadata": self.metadata[idx], "index": int(idx)})
        return hits

    def _persist(self) -> None:
        Path(self.index_path).parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(self.index_path))
        self.meta_path.write_text(json.dumps(self.metadata), encoding="utf-8")
