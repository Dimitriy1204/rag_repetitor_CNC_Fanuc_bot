import json
import logging
from pathlib import Path
from typing import List, Tuple
import shutil
import tempfile

import faiss
import numpy as np

from config import FAISS_INDEX_PATH, FAISS_METADATA_PATH

logger = logging.getLogger(__name__)


class FAISSVectorStore:
    def __init__(self, index_path: Path = FAISS_INDEX_PATH, metadata_path: Path = FAISS_METADATA_PATH):
        self.index_path = Path(index_path)
        self.metadata_path = Path(metadata_path)
        self.index = None
        self.metadata = []

    def create_index(self, dimension: int):
        self.index = faiss.IndexFlatL2(dimension)
        self.metadata = []

    def add_documents(self, texts: List[str], embeddings: List[List[float]], sources: List[str] = None):
        if self.index is None:
            raise ValueError("Индекс не инициализирован.")
        if len(texts) != len(embeddings):
            raise ValueError("Количество текстов и эмбеддингов не совпадает.")

        self.index.add(np.array(embeddings, dtype=np.float32))
        for i, text in enumerate(texts):
            self.metadata.append(
                {
                    "text": text,
                    "source": sources[i] if sources else f"doc_{i}",
                    "index": len(self.metadata),
                }
            )

    def search(self, query_embedding: List[float], k: int = 3) -> List[Tuple[str, str, float]]:
        if self.index is None or self.index.ntotal == 0:
            return []
        query_array = np.array([query_embedding], dtype=np.float32)
        distances, indices = self.index.search(query_array, min(k, self.index.ntotal))
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.metadata):
                meta = self.metadata[idx]
                results.append((meta["text"], meta["source"], float(distances[0][i])))
        return results

    def save(self):
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)
        if self.index is None:
            raise ValueError("Индекс не инициализирован.")

        # On Windows FAISS can fail to write directly to paths with non-ASCII symbols.
        # Save into temp ASCII path first, then move to target location.
        with tempfile.NamedTemporaryFile(delete=False, suffix=".faiss") as tmp_file:
            temp_path = tmp_file.name
        faiss.write_index(self.index, temp_path)
        shutil.move(temp_path, str(self.index_path))

        with open(self.metadata_path, "w", encoding="utf-8") as file:
            json.dump(self.metadata, file, ensure_ascii=False, indent=2)

    def load(self) -> bool:
        if not self.index_path.exists() or not self.metadata_path.exists():
            return False
        try:
            # On Windows FAISS can fail with non-ASCII paths.
            # Read index through temporary ASCII path.
            with tempfile.NamedTemporaryFile(delete=False, suffix=".faiss") as tmp_file:
                temp_path = tmp_file.name
            shutil.copy2(str(self.index_path), temp_path)
            self.index = faiss.read_index(temp_path)
            Path(temp_path).unlink(missing_ok=True)

            with open(self.metadata_path, "r", encoding="utf-8") as file:
                self.metadata = json.load(file)
            return True
        except Exception as error:
            logger.error("Не удалось загрузить FAISS индекс: %s", error)
            self.index = None
            self.metadata = []
            return False

    def get_stats(self) -> dict:
        return {
            "total_vectors": self.index.ntotal if self.index else 0,
            "total_documents": len(self.metadata),
            "dimension": self.index.d if self.index else 0,
            "index_exists": self.index_path.exists(),
            "metadata_exists": self.metadata_path.exists(),
        }
