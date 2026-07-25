import logging
from typing import List

import requests

from config import (
    EMBED_MODEL,
    REQUEST_TIMEOUT,
    YANDEX_API_KEY,
    YANDEX_EMBED_URL,
    YANDEX_FOLDER_ID,
)

logger = logging.getLogger(__name__)


class YandexEmbedder:
    def __init__(self, model: str = EMBED_MODEL):
        self.model = model
        self.headers_api_key = {
            "Content-Type": "application/json",
            "Authorization": f"Api-Key {YANDEX_API_KEY}",
            "x-folder-id": YANDEX_FOLDER_ID,
        }
        # Fallback for setups where IAM token is used instead of API key.
        self.headers_bearer = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {YANDEX_API_KEY}",
            "x-folder-id": YANDEX_FOLDER_ID,
        }

    def embed_text(self, text: str) -> List[float]:
        payload = {"modelUri": self.model, "text": text}
        response = requests.post(
            YANDEX_EMBED_URL,
            headers=self.headers_api_key,
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code == 401:
            logger.warning("401 with Api-Key header, retrying with Bearer header")
            response = requests.post(
                YANDEX_EMBED_URL,
                headers=self.headers_bearer,
                json=payload,
                timeout=REQUEST_TIMEOUT,
            )
        if response.status_code >= 400:
            logger.error("Embedding request failed: %s", response.text[:500])
        response.raise_for_status()
        return response.json()["embedding"]

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        embeddings = []
        for text in texts:
            embeddings.append(self.embed_text(text))
        return embeddings
