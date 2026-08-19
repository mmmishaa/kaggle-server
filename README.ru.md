# Kaggle Server Template

[English](README.md) | Русский

Шаблон для запуска удаленного FastAPI-сервера в среде Kaggle (с поддержкой GPU) с автоматическим пробросом бесплатного HTTPS-туннеля через Cloudflare и регистрацией адреса в GitHub Gist.

Проект спроектирован как шаблонный репозиторий для быстрого и бесплатного развертывания и использования AI моделей.

## Возможности

* Автоматический запуск на Kaggle: локальный скрипт упаковывает и загружает код на Kaggle через официальный Kaggle CLI.
* Бесплатный публичный HTTPS: автоматическая загрузка бинарного файла cloudflared и создание туннеля trycloudflare.com без белого IP и проброса портов.
* Обнаружение сервиса через GitHub Gist: удаленный сервер записывает динамический URL и статус в приватный Gist, а клиент автоматически считывает его.
* Прогрев туннеля (Healthcheck): механизм ожидания инициализации TLS-сертификатов Cloudflare перед отправкой рабочих запросов.
* Graceful Shutdown: безопасная остановка сервера через эндпоинт /shutdown с кодом завершения 0 (статус Complete) для сохранения квот Kaggle GPU.

## Архитектура работы

```text
[ Локальный ПК (main.py) ] 
       │
       ├─► 1. Kaggle CLI: Загружает и запускает server/service.py
       │
[ Kaggle Kernel (GPU) ]
       ├─► 2. Поднимает FastAPI + скачивает Cloudflared
       ├─► 3. Создает HTTPS туннель -> https://*.trycloudflare.com
       └─► 4. Записывает URL в GitHub Gist
       │
[ Локальный ПК (client) ]
       ├─► 5. Считывает URL из Gist
       ├─► 6. Выполняет прогрев (GET /health)
       ├─► 7. Отправляет рабочие запросы (POST /echo)
       └─► 8. Завершает работу сервера (POST /shutdown)
```

## Требования

* Python 3.10+
* Аккаунт Kaggle и API-токен (Kaggle API Key).
* Аккаунт GitHub.

## Установка и настройка

1. Клонируйте репозиторий:

```bash
git clone https://github.com/mmmishaa/kaggle-server.git
cd kaggle-server
```

2. Установите зависимости:

```bash
pip install -r requirements.txt
```

3. Создайте токен доступа GitHub:
   Перейдите в GitHub: Settings -> Developer Settings -> Personal access tokens -> Tokens (classic). Сгенерируйте новый токен и обязательно отметьте галочкой право доступа `gist`.

4. Создайте файл `config.env` в корневой папке проекта со следующими полями:

```env
GITHUB_TOKEN=ghp_your_github_token_here
GIST_ID=
KAGGLE_USERNAME=your_kaggle_username
KAGGLE_API_TOKEN=your_kaggle_api_token
```

Если оставить параметр `GIST_ID=` пустым, скрипт автоматически создаст новый приватный Gist при первом запуске и сам запишет его идентификатор в этот файл.

## Запуск

Запустите точку входа:

```bash
python main.py
```

Последовательность выполнения:
1. Инициализация и сброс состояния в GitHub Gist.
2. Сборка метаданных и запуск ядра Kaggle.
3. Ожидание генерации адреса Cloudflare.
4. Проверка доступности через эндпоинт /health.
5. Отправка тестового запроса на /echo.
6. Вызов штатного завершения работы через /shutdown.

## Структура проекта

```text
├── client/
│   ├── client.py        # Синхронизация с Gist, опрос healthcheck, остановка сервера
│   └── gist_init.py     # Автоматическое создание приватного Gist
├── server/
│   └── service.py       # FastAPI-приложение и управление процессом Cloudflare
├── .gitignore           # Исключение секретов и временных файлов сборки
├── config.env.example   # Пример конфигурационного файла
├── main.py              # Клиентский сценарий запуска и оркестрации
└── requirements.txt     # Зависимости Python
```