import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# VK
VK_GROUP_ID = os.getenv("VK_GROUP_ID", "")
VK_ACCESS_TOKEN = os.getenv("VK_ACCESS_TOKEN", "")
if not VK_GROUP_ID or not VK_ACCESS_TOKEN:
    raise ValueError("Укажите VK_GROUP_ID и VK_ACCESS_TOKEN в .env")

# Yandex
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY", "")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID", "")
if not YANDEX_API_KEY or not YANDEX_FOLDER_ID:
    raise ValueError("Укажите YANDEX_API_KEY и YANDEX_FOLDER_ID в .env")

YANDEX_BASE_URL = os.getenv("YANDEX_BASE_URL", "https://ai.api.cloud.yandex.net/v1")
YANDEX_EMBED_URL = os.getenv(
    "YANDEX_EMBED_URL",
    "https://ai.api.cloud.yandex.net/foundationModels/v1/textEmbedding",
)

CHAT_MODEL = "gpt://{folder}/yandexgpt-5-lite/latest".format(folder=YANDEX_FOLDER_ID)
EMBED_MODEL = "emb://{folder}/text-embeddings/latest".format(folder=YANDEX_FOLDER_ID)

# Paths
BASE_DIR = Path(__file__).parent
DOCS_PATH = BASE_DIR.parent / "data" / "docs"
FAISS_INDEX_PATH = BASE_DIR / "index.faiss"
FAISS_METADATA_PATH = BASE_DIR / "metadata.json"
LOGS_DB_PATH = BASE_DIR / "logs.db"

TARGET_DOC_FILES = [
    "PEr01_common_info.docx",
    "PEr01_FAQ.docx",
    "PEr01_study_plan.docx",
]

# RAG
TOP_K_RESULTS = 3
MAX_CONTEXT_LENGTH = 3500
MAX_HISTORY_LENGTH = 10
REQUEST_TIMEOUT = 60

SYSTEM_PROMPT = """Ты репетитор по программированию станков с ЧПУ учебного центра «Точка отсчета» на «Заводе Стройтехника».
Отвечай на русском языке, четко, по делу и дружелюбно.
Опирайся в первую очередь на контекст из базы знаний.
Если информации в базе нет, честно скажи об этом и предложи, как переформулировать вопрос."""

RAG_PROMPT_TEMPLATE = """Контекст из базы знаний:
{context}
Вопрос пользователя: {query}
Ответ:"""

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
