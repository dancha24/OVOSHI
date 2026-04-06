# OVOSHI — сайт клана

Веб-приложение клана OVOSHI: лендинг, регистрация через OAuth (ВК, Яндекс, Mail.ru), профиль, админка для лидера (настройки, таблица участников).

## Стек

- **Frontend:** React (Vite). Шаблон — [Wingo](https://docs.pixelstrap.com/wingo/document/getting-started-react.html) (в папке `Wingo/react/template`); при желании можно перенести Layout/компоненты оттуда в `frontend/`.
- **Backend:** Django + DRF, PostgreSQL, django-allauth (OAuth).
- **Инфра:** Docker (backend + PostgreSQL).

## Быстрый старт

### 1. Бэкенд (Django)

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
cp .env.example .env      # при необходимости отредактировать
```

PostgreSQL должен быть запущен (локально или через Docker). Затем:

```bash
python manage.py migrate
python manage.py createsuperuser   # опционально, для /admin/
python manage.py runserver
```

Первого пользователя с ролью «Лидер» можно задать в Django Admin: `/admin/` → Пользователи → выбрать пользователя → Role = Лидер (или создать суперпользователя и выставить роль в БД).

### 2. Фронтенд (React)

```bash
cd frontend
npm install
npm run dev
```

Откроется http://localhost:3000. Запросы к `/api` и `/accounts` проксируются на http://localhost:8000. Если после OAuth сессия не подхватывается, создайте `frontend/.env` с `VITE_API_URL=http://localhost:8000` и перезапустите `npm run dev` — тогда запросы пойдут напрямую на бэкенд и cookie сессии будут отправляться.

### 3. OAuth

Чтобы работал вход через ВК/Яндекс/Mail.ru:

1. Создать приложения в соответствующих сервисах.
2. В настройках приложений указать callback URL: `http://localhost:8000/accounts/vk/login/callback/` (и аналогично для yandex, mailru).
3. В `backend/.env` прописать `VK_CLIENT_ID`, `VK_CLIENT_SECRET` и т.д.

### 4. Запуск через Docker (всё в контейнерах)

```bash
docker compose -f docker/docker-compose.yml up -d --build
```

- **Фронт:** http://localhost:3050  
- **Бэкенд (API, админка):** http://localhost:59722  
- **PostgreSQL:** порт 5432  

Миграции применяются автоматически при старте backend. Фронт при открытии в браузере ходит за API на `http://localhost:59722` (задано через `VITE_API_URL` в docker-compose).

**Режим разработки** (код монтируется, бэкенд — runserver, фронт — hot-reload):

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up --build
```

Порты те же: фронт 3050, бэкенд 59722. Меняешь файлы в `backend/` и `frontend/` — изменения подхватываются без пересборки образа. Для бота ВК в Callback API сообщества укажи свой HTTPS-URL вида `https://домен/vk/callback/` (прокси на этот backend).

## Структура

- `backend/` — Django (DRF, allauth, модели User, Profile, SiteSettings).
- `frontend/` — React (Vite): лендинг, вход, профиль, админка (настройки, участники).
- `Wingo/` — шаблон Wingo (React); при интеграции можно копировать компоненты в `frontend/src`.
- `OVOSHI Docs/` — документация и контент (инструкции по ролям — см. план).
- `docker/` — docker-compose для backend + PostgreSQL и оверлей `docker-compose.dev.yml`.

## Полезные URL

- Паблик клана ВКонтакте: https://vk.com/ovoshi_pubg
- Фронт: http://localhost:3000
- API: http://localhost:8000/api/
- Текущий пользователь: GET /api/auth/me/
- Настройки (лендинг): GET /api/settings/ ; PATCH (лидер) /api/settings/
- Участники (лидер): GET/PATCH /api/participants/, /api/participants/:id/
- Вход: /login на фронте → ссылки на /accounts/vk/login/, /accounts/yandex/login/, /accounts/mailru/login/
