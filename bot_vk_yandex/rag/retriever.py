import logging
from typing import List, Tuple

from config import TOP_K_RESULTS

logger = logging.getLogger(__name__)


class DocumentRetriever:
    def __init__(self, embedder, vectorstore):
        self.embedder = embedder
        self.vectorstore = vectorstore

    def retrieve(self, query: str, top_k: int = TOP_K_RESULTS) -> List[Tuple[str, str, float]]:
        query_embedding = self.embedder.embed_text(query)
        return self.vectorstore.search(query_embedding, k=top_k)

    def retrieve_context(self, query: str, top_k: int = TOP_K_RESULTS, max_length: int = 3000) -> str:
        results = self.retrieve(query, top_k)
        if not results:
            return "Релевантная информация не найдена в базе знаний."

        context_parts = []
        total_length = 0
        for i, (text, source, _) in enumerate(results, 1):
            doc_text = f"[Документ {i} из {source}]\n{text}\n"
            if total_length + len(doc_text) > max_length:
                remaining = max_length - total_length
                if remaining > 100:
                    context_parts.append(doc_text[:remaining] + "...\n")
                break
            context_parts.append(doc_text)
            total_length += len(doc_text)
        return "\n".join(context_parts)

    def get_relevant_sources(self, query: str, top_k: int = TOP_K_RESULTS) -> List[str]:
        results = self.retrieve(query, top_k)
        return list(set(source for _, source, _ in results))
