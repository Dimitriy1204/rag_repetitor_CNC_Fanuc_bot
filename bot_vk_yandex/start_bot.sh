#!/bin/bash
set -e

echo "========================================"
echo "  VK + Yandex RAG Bot startup script"
echo "========================================"
echo ""

cd "$(dirname "$0")"

# Проверка наличия Python3
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 не установлен"
    echo "Установите Python 3.10+: sudo apt install python3 python3-venv python3-pip"
    exit 1
fi

echo "[INFO] Python: $(python3 --version)"

# Создание виртуального окружения
if [ ! -d "venv" ]; then
    echo "[1/4] Создание виртуального окружения..."
    python3 -m venv venv
else
    echo "[1/4] Виртуальное окружение уже существует"
fi

# Активация
source venv/bin/activate

# Установка зависимостей
echo "[2/4] Установка зависимостей..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

# Проверка .env
if [ ! -f ".env" ]; then
    echo "[3/4] .env не найден. Создаю из .env.example..."
    cp .env.example .env
    echo ""
    echo "[WARNING] Файл .env создан из шаблона."
    echo "[WARNING] Заполните реальные ключи в .env и запустите скрипт снова."
    echo ""
    echo "  Редактировать: nano .env"
    echo ""
    exit 1
else
    echo "[3/4] .env найден"
fi

# Запуск бота
echo "[4/4] Запуск бота..."
echo ""
python bot.py