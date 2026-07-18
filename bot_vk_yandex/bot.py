import logging
import time
from pathlib import Path
from typing import List, Tuple
import docx
import vk_api
from vk_api.bot_longpoll import VkBotEventType, VkBotLongPoll
from config import (
    DOCS_PATH,
    LOG_FORMAT,
    LOG_LEVEL,
    MAX_HISTORY_LENGTH,
    TARGET_DOC_FILES,
    VK_ACCESS_TOKEN,
    VK_GROUP_ID,
    LOGS_DB_PATH,
)
from rag.pipeline import RAGPipeline
from db_logger import DatabaseLogger

# Настройка стандартного логирования в файл и консоль
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    handlers=[logging.FileHandler("bot.log", encoding="utf-8"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Инициализация логгера базы данных
db_logger = DatabaseLogger(db_path=str(LOGS_DB_PATH))

def chunk_text(text: str, max_chars: int = 6000) -> List[str]:
    if len(text) <= max_chars:
        return [text]
    parts = []
    start = 0
    while start < len(text):
        parts.append(text[start : start + max_chars])
        start += max_chars
    return parts

def read_docx(file_path: Path) -> str:
    document = docx.Document(str(file_path))
    return "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text.strip())

def load_documents_from_directory(directory: Path) -> Tuple[List[str], List[str]]:
    documents, sources = [], []
    if not directory.exists():
        logger.warning("Директория %s не существует", directory)
        return documents, sources
    
    allowed_files = {name.lower() for name in TARGET_DOC_FILES}
    for file_path in sorted(directory.iterdir()):
        if not file_path.is_file():
            continue
        if file_path.name.lower() not in allowed_files:
            continue
        
        ext = file_path.suffix.lower()
        text = ""
        try:
            if ext == ".txt":
                text = file_path.read_text(encoding="utf-8")
            elif ext in {".docx", ".doc"}:
                text = read_docx(file_path)
            else:
                continue
        except Exception as error:
            logger.error("Ошибка чтения %s: %s", file_path.name, error)
            continue
        
        text = text.strip()
        if not text:
            continue
        
        chunks = chunk_text(text)
        for idx, chunk in enumerate(chunks, start=1):
            documents.append(chunk)
            if len(chunks) == 1:
                sources.append(file_path.name)
            else:
                sources.append(f"{file_path.name} (часть {idx}/{len(chunks)})")
    
    logger.info(
        "Загружено %s частей из целевых файлов: %s",
        len(documents),
        ", ".join(TARGET_DOC_FILES),
    )
    return documents, sources

class VKRAGBot:
    def __init__(self):
        self.vk_session = vk_api.VkApi(token=VK_ACCESS_TOKEN)
        self.longpoll = VkBotLongPoll(self.vk_session, int(VK_GROUP_ID))
        self.rag_pipeline = RAGPipeline()
        self.conversation_history = {}

    def send_message(self, user_id: int, text: str):
        self.vk_session.method(
            "messages.send",
            {"user_id": user_id, "message": text, "random_id": 0},
        )

    def handle_command(self, user_id: int, text: str):
        if text in ["/start", "старт", "привет"]:
            self.send_message(
                user_id,
                "Привет! Я VK-бот-репетитор по программированию ЧПУ.\n"
                "Команды: /help, /ingest, /stats, /clear\n"
                "Просто напишите вопрос, и я отвечу по базе знаний.",
            )
            return True
        if text == "/help":
            self.send_message(
                user_id,
                "Я отвечаю по материалам учебного центра.\n"
                "/ingest - переиндексация базы из data/docs (.txt/.doc/.docx)\n"
                "/stats - статус индекса и логи\n"
                "/clear - очистка истории диалога",
            )
            return True
        if text == "/clear":
            self.conversation_history[user_id] = []
            self.send_message(user_id, "История очищена.")
            return True
        if text == "/stats":
            rag_stats = self.rag_pipeline.get_stats()
            db_stats = db_logger.get_stats()
            
            stats_text = (
                "Статистика RAG:\n"
                f"- База загружена: {'да' if rag_stats['is_loaded'] else 'нет'}\n"
                f"- Документов: {rag_stats['total_documents']}\n"
                f"- Векторов: {rag_stats['total_vectors']}\n\n"
                "Статистика логов:\n"
                f"- Всего вопросов: {db_stats['total_interactions']}\n"
                f"- Среднее время ответа: {db_stats['avg_response_time_ms']} мс"
            )
            self.send_message(user_id, stats_text)
            return True
        if text == "/ingest":
            self.send_message(user_id, "Индексация запущена, подождите...")
            documents, sources = load_documents_from_directory(DOCS_PATH)
            if not documents:
                self.send_message(user_id, f"Не нашел документов в {DOCS_PATH}")
                return True
            ok = self.rag_pipeline.index_documents(documents, sources)
            if ok:
                stats = self.rag_pipeline.get_stats()
                self.send_message(
                    user_id,
                    "Индексация завершена.\n"
                    f"- Документов: {stats['total_documents']}\n"
                    f"- Векторов: {stats['total_vectors']}",
                )
            else:
                self.send_message(user_id, "Ошибка индексации, проверьте bot.log")
            return True
        return False

    def handle_text_message(self, user_id: int, text: str):
        start_time = time.time()
        history = self.conversation_history.setdefault(user_id, [])
        
        try:
            result = self.rag_pipeline.query_with_history(text, history)
            answer = result["answer"]
            source = result.get("source", "rag") # Если в pipeline есть источник
            
            # Запись в историю
            history.append({"role": "user", "content": text})
            history.append({"role": "assistant", "content": answer})
            if len(history) > MAX_HISTORY_LENGTH * 2:
                self.conversation_history[user_id] = history[-(MAX_HISTORY_LENGTH * 2):]
            
            # Расчет времени и логирование
            response_time_ms = int((time.time() - start_time) * 1000)
            db_logger.log_interaction(
                user_id=user_id,
                query=text,
                response=answer,
                source=source,
                from_cache=False, # Пока считаем, что кэш внутри RAG pipeline, здесь фиксируем факт запроса
                response_time_ms=response_time_ms
            )
            
            self.send_message(user_id, answer[:3900])
            
        except Exception as e:
            logger.exception("Ошибка обработки сообщения: %s", e)
            self.send_message(user_id, "Произошла ошибка при обработке вашего вопроса.")
            # Логируем ошибку
            response_time_ms = int((time.time() - start_time) * 1000)
            db_logger.log_interaction(
                user_id=user_id,
                query=text,
                response=f"Error: {str(e)}",
                status="error",
                response_time_ms=response_time_ms
            )

    def run(self):
        logger.info("VK RAG бот запущен с системой логирования в logs.db")
        for event in self.longpoll.listen():
            if event.type != VkBotEventType.MESSAGE_NEW or not event.from_user:
                continue
            message = event.object["message"]
            user_id = message["from_id"]
            text = (message.get("text") or "").strip()
            
            if not text:
                self.send_message(user_id, "Пришлите текстовый вопрос.")
                continue
            
            try:
                if not self.handle_command(user_id, text.lower()):
                    self.handle_text_message(user_id, text)
            except Exception as error:
                logger.exception("Критическая ошибка в цикле событий: %s", error)
                self.send_message(user_id, "Произошла системная ошибка. Попробуйте еще раз.")

if __name__ == "__main__":
    VKRAGBot().run()
