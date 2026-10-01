# Нотатник

Django-застосунок із нотатками та категоріями. Головна сторінка `/` читає
нотатки з PostgreSQL. CSS розміщено в `notes/static/notes/css/style.css`.

## База даних

- `Category`: `title`.
- `Note`: `title`, `text`, необов’язковий `reminder` (дата й час), `category` (зовнішній ключ).
- Категорію з нотатками не можна видалити, доки нотатки не перенесено або видалено.
- Час нагадувань на сторінці відображається в часовому поясі `Europe/Kyiv`.

## Локальне середовище

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
brew install postgresql@17
```

Для встановленого Homebrew PostgreSQL на Apple Silicon:

```sh
/opt/homebrew/opt/postgresql@17/bin/pg_ctl -D /opt/homebrew/var/postgresql@17 -l /opt/homebrew/var/postgresql@17/server.log start
/opt/homebrew/opt/postgresql@17/bin/createuser -h localhost --createdb notes_app
/opt/homebrew/opt/postgresql@17/bin/createdb -h localhost -O notes_app notes_app
```

На поточному комп’ютері PostgreSQL уже встановлено, роль і базу створено,
міграції застосовано. Повторно створювати роль і базу не потрібно.
Запуск через `pg_ctl` не налаштовує автозапуск після перезавантаження.

Налаштування підключення беруться зі змінних середовища:

| Змінна | Типове значення |
| --- | --- |
| `PGDATABASE` | `notes_app` |
| `PGUSER` | `notes_app` |
| `PGPASSWORD` | порожнє |
| `PGHOST` | `localhost` |
| `PGPORT` | `5432` |

Локальний кластер Homebrew використовує `trust` для локальних підключень,
тому пароль тут не потрібен. Для іншого сервера задайте його через `PGPASSWORD`.
Файл `.env` автоматично не завантажується. Старий `db.sqlite3` більше не використовується.

## Міграції й перевірки

```sh
.venv/bin/python manage.py migrate
.venv/bin/python manage.py check
.venv/bin/python manage.py test notes --noinput
```

Міграція `0002_sample_notes` додає три категорії та три тестові нотатки.
Повторний звичайний `migrate` не дублює записи. Відкат цієї міграції зберігає
дані, щоб не видалити записи, які користувач міг змінити.
Тести використовують окрему базу `test_notes_app`, яку Django створює та видаляє;
локальній ролі надано `CREATEDB` для цього.

За потреби зупинити PostgreSQL:

```sh
/opt/homebrew/opt/postgresql@17/bin/pg_ctl -D /opt/homebrew/var/postgresql@17 stop
```

Вебсервер під час налаштування та перевірок не запускався.
