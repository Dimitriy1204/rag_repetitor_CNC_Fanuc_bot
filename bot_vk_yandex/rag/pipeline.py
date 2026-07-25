import logging
from typing import Dict, List

from openai import OpenAI

from config import (
    CHAT_MODEL,
    MAX_CONTEXT_LENGTH,
    RAG_PROMPT_TEMPLATE,
    SYSTEM_PROMPT,
    TOP_K_RESULTS,
    YANDEX_API_KEY,
    YANDEX_BASE_URL,
    YANDEX_FOLDER_ID,
)
from rag.embedder import YandexEmbedder
from rag.retriever import DocumentRetriever
from rag.vectorstore import FAISSVectorStore

logger = logging.getLogger(__name__)


class RAGPipeline:
    def __init__(self):
        self.client = OpenAI(
            api_key=YANDEX_API_KEY,
            base_url=YANDEX_BASE_URL,
            project=YANDEX_FOLDER_ID,
        )
        self.embedder = YandexEmbedder()
        self.vectorstore = FAISSVectorStore()
        self.retriever = DocumentRetriever(self.embedder, self.vectorstore)
        self.is_loaded = self.vectorstore.load()

    def query(self, user_query: str, top_k: int = TOP_K_RESULTS) -> Dict[str, any]:
        return self.query_with_history(user_query, [], top_k)

    def query_with_history(self, user_query: str, history: list = None, top_k: int = TOP_K_RESULTS) -> Dict[str, any]:
        if not self.is_loaded:
            return {
                "answer": "База знаний не загружена. Напишите /ingest для индексации документов.",
                "context": "",
                "sources": [],
                "model": CHAT_MODEL,
            }

        context = self.retriever.retrieve_context(user_query, top_k=top_k, max_length=MAX_CONTEXT_LENGTH)
        sources = self.retriever.get_relevant_sources(user_query, top_k)
        prompt_with_context = RAG_PROMPT_TEMPLATE.format(context=context, query=user_query)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if history:
            messages.extend(history[-20:])
        messages.append({"role": "user", "content": prompt_with_context})

        try:
            response = self.client.chat.completions.create(
                model=CHAT_MODEL,
                messages=messages,
                temperature=0.3,
                max_tokens=1200,
            )
            answer = response.choices[0].message.content
        except Exception as error:
            logger.error("Ошибка генерации ответа: %s", error)
            answer = f"Ошибка генерации ответа: {error}"

        return {
            "answer": answer,
            "context": context,
            "sources": sources,
            "model": CHAT_MODEL,
        }

    def index_documents(self, documents: List[str], sources: List[str]) -> bool:
        try:
            embeddings = self.embedder.embed_texts(documents)
            if not embeddings:
                return False
            self.vectorstore.create_index(len(embeddings[0]))
            self.vectorstore.add_documents(documents, embeddings, sources)
            self.vectorstore.save()
            self.is_loaded = True
            return True
        except Exception as error:
            logger.error("Ошибка индексации: %s", error)
            return False

    def get_stats(self) -> Dict[str, any]:
        stats = self.vectorstore.get_stats()
        stats.update(
            {
                "is_loaded": self.is_loaded,
                "embed_model": self.embedder.model,
                "chat_model": CHAT_MODEL,
            }
        )
        return stats
