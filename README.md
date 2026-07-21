# Oxygen Fitness — Telegram AI-агент

AI-консультант для клиентов зала: отвечает на вопросы о ценах, графике, записи
на бесплатную тренировку. Понимает узбекский и русский, отвечает на языке клиента.

## Что внутри

- `bot.py` — весь код бота (Python, ~150 строк)
- `.env` — твои токены (НИКОМУ не показывать, в git не попадает)
- `requirements.txt` — зависимости
- `Dockerfile`, `Procfile` — для хостинга

## Запуск на своём компьютере (для проверки)

Открой Терминал на Mac и выполни:

```bash
cd ~/Desktop/"Новая папка"/oxygen-bot
pip3 install -r requirements.txt
python3 bot.py
```

Бот заработает через несколько секунд — напиши ему в Telegram `/start`.
Работает, пока запущен терминал и Mac не спит. Для круглосуточной работы — хостинг (ниже).

## Круглосуточный хостинг (рекомендую Railway)

1. Зайди на https://railway.app и войди через GitHub.
2. Загрузи проект на GitHub (команды ниже) или выбери «Deploy from local» через их CLI.
3. В Railway: New Project → Deploy from GitHub repo → выбери репозиторий.
4. В настройках сервиса добавь переменные (Variables):
   - `TELEGRAM_TOKEN` = токен бота
   - `ANTHROPIC_API_KEY` = ключ API
5. Railway сам увидит `Procfile` и запустит `worker: python bot.py`. Готово.

Альтернативы: Render.com (Background Worker), любой VPS (`docker build -t oxygen-bot . && docker run -d --env-file .env oxygen-bot`).

## Загрузка на GitHub

Создай пустой ПРИВАТНЫЙ репозиторий на github.com (кнопка New), затем в Терминале:

```bash
cd ~/Desktop/"Новая папка"/oxygen-bot
git init
git add .
git commit -m "Oxygen Fitness AI bot"
git branch -M main
git remote add origin https://github.com/ТВОЙ_ЛОГИН/oxygen-bot.git
git push -u origin main
```

`.env` с токенами в репозиторий не попадёт — он в `.gitignore`. Это важно.

## Как изменить информацию (цены, график и т.д.)

Открой `bot.py`, найди `SYSTEM_PROMPT` — там все факты о зале обычным текстом.
Поменяй, сохрани, перезапусти бота.

## Команды бота

- `/start` — приветствие и меню
- `/new` — очистить историю диалога

## Сколько стоит

Модель — Claude Haiku 4.5: один ответ клиенту ≈ $0.001–0.003.
Даже при 1000 сообщений в месяц — около $2–3.

## Безопасность

- Токены живут только в `.env` и в переменных хостинга.
- Если токен засветился — перевыпусти: бота через @BotFather (/revoke),
  ключ API в console.anthropic.com, GitHub-токен в Settings → Developer settings.
