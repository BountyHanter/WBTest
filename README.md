# API documentation

## 1. Базовая информация

Базовый префикс всех ручек: `/api/v1/`.
Пользовательские ручки находятся под `/api/v1/users/` и `/api/v1/auth/`, ручки приложения `stats` — прямо под `/api/v1/`. Также есть служебный healthcheck `/api/v1/health/` и админка `/api/v1/admin/`.

API использует JWT-аутентификацию. В заголовке нужно передавать:

```http
Authorization: Bearer <access_token>
```

Формат даты и времени в ответах:

```text
YYYY-MM-DDTHH:MM:SS.ffffff+ZZZZ
```

Пример:

```text
2026-04-15T17:30:00.000000+0500
```

`access` живёт 30 минут, `refresh` — 30 дней. Для refresh предусмотрена отдельная ручка `POST /api/v1/auth/token/refresh/`.

---

## 2. Формат ошибок

Единого строго одинакового формата ошибок во всех ручках нет. В зависимости от места можно получить:

```json
{"detail": "Текст ошибки"}
```

или

```json
{"field_name": ["Текст ошибки"]}
```

или

```json
{"field_name": "Текст ошибки"}
```

Это связано с тем, что часть ошибок приходит из DRF serializer validation, часть — из `ValidationError` моделей, часть — из ручных проверок во view.

---

## 3. Аутентификация и пользователь

### 3.1 Регистрация

`POST /api/v1/users/register/`

Без авторизации.

#### Request

```json
{
  "email": "user@example.com",
  "password": "123456"
}
```

#### Правила

* `email` обязателен
* `email` должен быть уникальным
* `password` минимум 6 символов

#### Response 201

```json
{
  "detail": "Письмо для подтверждения отправлено на email"
}
```

После регистрации пользователь не получает JWT-токены, пока не подтвердит email.

#### Возможные ошибки

```json
{
  "email": ["Пользователь уже существует"]
}
```

---

### 3.2 Подтверждение email

`GET /api/v1/users/verify-email/?user_id={id}&token={token}`

Без авторизации.

#### Query params

* `user_id` — id пользователя
* `token` — токен подтверждения из письма

#### Response 200

```json
{
  "detail": "Email подтверждён"
}
```

#### Возможные ошибки

Отсутствуют параметры:

```json
{
  "detail": "user_id и token обязательны"
}
```

Пользователь не найден:

```json
{
  "detail": "Пользователь не найден"
}
```

Невалидный/просроченный токен:

```json
{
  "detail": "Неверный или устаревший токен"
}
```

---

### 3.3 Логин

`POST /api/v1/auth/login/`

Без авторизации.

#### Request

```json
{
  "email": "user@example.com",
  "password": "123456"
}
```

#### Response 200

```json
{
  "refresh": "jwt_refresh_token",
  "access": "jwt_access_token"
}
```

#### Возможные ошибки

Неверные креды:

```json
{
  "detail": "No active account found with the given credentials"
}
```

Email не подтверждён:

```json
{
  "detail": "Email не подтверждён"
}
```

---

### 3.4 Обновление access-токена

`POST /api/v1/auth/token/refresh/`

Без авторизации.

#### Request

```json
{
  "refresh": "jwt_refresh_token"
}
```

#### Response 200

```json
{
  "access": "new_jwt_access_token"
}
```

---

### 3.5 Выход (logout)

`POST /api/v1/users/logout/`

Требует JWT в заголовке (`Authorization: Bearer <access_token>`).

#### Request

```json
{
  "refresh": "jwt_refresh_token"
}
```

#### Response 204

Тело отсутствует. Переданный refresh-токен попадает в blacklist.

#### Возможные ошибки

```json
{
  "detail": "Refresh token обязателен"
}
```

или

```json
{
  "detail": "Неверный или просроченный токен"
}
```

---

### 3.6 Текущий пользователь

`GET /api/v1/users/me/`

Требует JWT.

#### Response 200

```json
{
  "email": "user@example.com"
}
```

---

## 4. WB Tokens

WB токен — отдельная сущность, привязанная к пользователю. Тест ссылается на WB токен через поле `wb_token`.

Модель ответа токена:

```json
{
  "id": 1,
  "token": "wb_secret_token",
  "created_at": "2026-04-15T17:30:00.000000+0500",
  "updated_at": "2026-04-15T17:30:00.000000+0500"
}
```

Поля `id`, `created_at`, `updated_at` read-only. 

### 4.1 Список токенов

`GET /api/v1/wb-tokens/`

Требует JWT.

#### Response 200

```json
[
  {
    "id": 2,
    "token": "wb_token_2",
    "created_at": "2026-04-15T17:30:00.000000+0500",
    "updated_at": "2026-04-15T17:30:00.000000+0500"
  },
  {
    "id": 1,
    "token": "wb_token_1",
    "created_at": "2026-04-15T16:00:00.000000+0500",
    "updated_at": "2026-04-15T16:00:00.000000+0500"
  }
]
```

Список возвращается в порядке от новых к старым. 

---

### 4.2 Создание токена

`POST /api/v1/wb-tokens/`

Требует JWT.

#### Request

```json
{
  "token": "wb_secret_token"
}
```

#### Response 201

```json
{
  "id": 1,
  "token": "wb_secret_token",
  "created_at": "2026-04-15T17:30:00.000000+0500",
  "updated_at": "2026-04-15T17:30:00.000000+0500"
}
```

---

### 4.3 Получение токена

`GET /api/v1/wb-tokens/{id}/`

Требует JWT.

#### Response 200

```json
{
  "id": 1,
  "token": "wb_secret_token",
  "created_at": "2026-04-15T17:30:00.000000+0500",
  "updated_at": "2026-04-15T17:30:00.000000+0500"
}
```

#### Ошибка 404

```json
{
  "detail": "Токен не найден"
}
```

---

### 4.4 Изменение токена

`PATCH /api/v1/wb-tokens/{id}/`

Требует JWT.

#### Request

```json
{
  "token": "new_wb_token"
}
```

#### Response 200

```json
{
  "id": 1,
  "token": "new_wb_token",
  "created_at": "2026-04-15T17:30:00.000000+0500",
  "updated_at": "2026-04-15T18:00:00.000000+0500"
}
```

---

### 4.5 Удаление токена

`DELETE /api/v1/wb-tokens/{id}/`

Требует JWT.

#### Response 204

Тело отсутствует.

#### Ограничение

Нельзя удалить токен, если он используется хотя бы в одном тесте.

#### Ошибка

```json
{
  "detail": "Нельзя удалить токен, который используется в тестах."
}
```

---

## 5. Тесты

Тест — основная сущность системы. Он принадлежит пользователю и содержит настройки ротации изображений. Поля, которые реально возвращаются наружу через serializer:

* `id`
* `name`
* `campaign_id`
* `product_id`
* `wb_token`
* `status`
* `impressions_per_cycle`
* `max_impressions_per_image`
* `time_per_cycle`
* `current_image`
* `created_at`
* `updated_at` 

Статусы теста:

* `draft`
* `active`
* `paused`
* `finished`
* `error` 

Модель ответа теста:

```json
{
  "id": 10,
  "name": "A/B test #1",
  "campaign_id": 123,
  "product_id": 456,
  "wb_token": 1,
  "status": "draft",
  "impressions_per_cycle": 100,
  "max_impressions_per_image": 1000,
  "time_per_cycle": 60,
  "current_image": null,
  "created_at": "2026-04-15T17:30:00.000000+0500",
  "updated_at": "2026-04-15T17:30:00.000000+0500"
}
```

`status`, `current_image`, `id`, `created_at`, `updated_at` изменять напрямую нельзя. После выхода теста из `draft` также запрещено менять `campaign_id`, `product_id`, `wb_token`, `impressions_per_cycle`, `max_impressions_per_image`, `time_per_cycle`. Удалять тест можно только в статусе `draft`.

---

### 5.1 Список тестов

`GET /api/v1/tests/`

Требует JWT.

#### Response 200

```json
[
  {
    "id": 11,
    "name": "Test 2",
    "campaign_id": 222,
    "product_id": 333,
    "wb_token": 2,
    "status": "active",
    "impressions_per_cycle": 100,
    "max_impressions_per_image": 1000,
    "time_per_cycle": 60,
    "current_image": 55,
    "created_at": "2026-04-15T18:00:00.000000+0500",
    "updated_at": "2026-04-15T18:10:00.000000+0500"
  },
  {
    "id": 10,
    "name": "Test 1",
    "campaign_id": 123,
    "product_id": 456,
    "wb_token": 1,
    "status": "draft",
    "impressions_per_cycle": 100,
    "max_impressions_per_image": 1000,
    "time_per_cycle": 60,
    "current_image": null,
    "created_at": "2026-04-15T17:30:00.000000+0500",
    "updated_at": "2026-04-15T17:30:00.000000+0500"
  }
]
```

Список отсортирован по `created_at` по убыванию. 

---

### 5.2 Создание теста

`POST /api/v1/tests/`

Требует JWT.

#### Request

```json
{
  "name": "A/B test #1",
  "campaign_id": 123,
  "product_id": 456,
  "wb_token": 1,
  "impressions_per_cycle": 100,
  "max_impressions_per_image": 1000,
  "time_per_cycle": 60
}
```

#### Response 201

```json
{
  "id": 10,
  "name": "A/B test #1",
  "campaign_id": 123,
  "product_id": 456,
  "wb_token": 1,
  "status": "draft",
  "impressions_per_cycle": 100,
  "max_impressions_per_image": 1000,
  "time_per_cycle": 60,
  "current_image": null,
  "created_at": "2026-04-15T17:30:00.000000+0500",
  "updated_at": "2026-04-15T17:30:00.000000+0500"
}
```

#### Валидация

Значения `impressions_per_cycle`, `max_impressions_per_image`, `time_per_cycle` должны быть больше 0. 

---

### 5.3 Получение теста

`GET /api/v1/tests/{id}/`

Требует JWT.

#### Response 200

```json
{
  "id": 10,
  "name": "A/B test #1",
  "campaign_id": 123,
  "product_id": 456,
  "wb_token": 1,
  "status": "draft",
  "impressions_per_cycle": 100,
  "max_impressions_per_image": 1000,
  "time_per_cycle": 60,
  "current_image": null,
  "created_at": "2026-04-15T17:30:00.000000+0500",
  "updated_at": "2026-04-15T17:30:00.000000+0500"
}
```

#### Ошибка 404

```json
{
  "detail": "Тест не найден"
}
```

---

### 5.4 Частичное изменение теста

`PATCH /api/v1/tests/{id}/`

Требует JWT.

Можно менять только разрешённые поля. После выхода из `draft` ключевые настройки теста менять нельзя.

#### Пример request

```json
{
  "name": "Новое название"
}
```

#### Response 200

```json
{
  "id": 10,
  "name": "Новое название",
  "campaign_id": 123,
  "product_id": 456,
  "wb_token": 1,
  "status": "draft",
  "impressions_per_cycle": 100,
  "max_impressions_per_image": 1000,
  "time_per_cycle": 60,
  "current_image": null,
  "created_at": "2026-04-15T17:30:00.000000+0500",
  "updated_at": "2026-04-15T18:00:00.000000+0500"
}
```

#### Пример ошибки

```json
{
  "campaign_id": ["Нельзя изменять после запуска теста"]
}
```

---

### 5.5 Удаление теста

`DELETE /api/v1/tests/{id}/`

Требует JWT.

#### Response 204

Тело отсутствует.

#### Ограничение

Удаление разрешено только для `draft`.

#### Пример ошибки

```json
{
  "detail": "Нельзя удалить тест если он не в режиме Черновик"
}
```

---

## 6. Действия над тестом

### 6.1 Запуск теста

`POST /api/v1/tests/{id}/start/`

Требует JWT.

Можно запустить только тест в статусе `draft`. При запуске тест переводится в `active`, а `started_at` выставляется на бэкенде.

#### Response 200

```json
{
  "detail": "Тест запущен"
}
```

#### Ошибка

```json
{
  "detail": "Можно запустить только тест в статусе draft"
}
```

---

### 6.2 Поставить тест на паузу

`POST /api/v1/tests/{id}/pause/`

Требует JWT.

Важно: эта ручка не переводит тест в `paused` мгновенно. Она только ставит внутренний флаг `set_pause = true`, а в ответе возвращает сообщение, что тест будет остановлен. Это важно для фронта: после вызова pause не надо ожидать, что в этом же ответе прилетит обновлённый объект теста со статусом `paused`.

#### Response 200

```json
{
  "detail": "Тест будет остановлен"
}
```

#### Ошибка

```json
{
  "detail": "Можно поставить на паузу только active тест"
}
```

---

### 6.3 Возобновить тест

`POST /api/v1/tests/{id}/resume/`

Требует JWT.

Можно вызвать только для теста в статусе `paused`. После вызова тест переводится обратно в `active`.

#### Response 200

```json
{
  "detail": "Тест возобновлён"
}
```

#### Ошибка

```json
{
  "detail": "Можно возобновить только paused тест"
}
```

---

## 7. Изображения теста

Изображения принадлежат тесту. Наружу отдаются такие поля:

* `id`
* `test`
* `position`
* `image`
* `status`
* `total_views`
* `total_clicks`
* `rounds_passed`
* `wins_count`
* `started_at`
* `created_at`
* `updated_at` 

Статусы изображения:

* `pending`
* `done` 

Изменять вручную можно только:

* `position`
* `image`

Все остальные поля read-only. Изображения можно добавлять, менять и удалять только пока тест находится в `draft`. У позиции есть ограничение уникальности в рамках теста. Позиция должна быть больше 0.

### Формат объекта изображения

```json
{
  "id": 101,
  "test": 10,
  "position": 1,
  "image": "/media/tests/images/example.jpg",
  "status": "pending",
  "total_views": 0,
  "total_clicks": 0,
  "rounds_passed": 0,
  "wins_count": 0,
  "started_at": null,
  "created_at": "2026-04-15T18:10:00.000000+0500",
  "updated_at": "2026-04-15T18:10:00.000000+0500"
}
```

---

### 7.1 Список изображений теста

`GET /api/v1/tests/{test_id}/images/`

Требует JWT.

#### Response 200

```json
[
  {
    "id": 101,
    "test": 10,
    "position": 1,
    "image": "/media/tests/images/img1.jpg",
    "status": "pending",
    "total_views": 0,
    "total_clicks": 0,
    "rounds_passed": 0,
    "wins_count": 0,
    "started_at": null,
    "created_at": "2026-04-15T18:10:00.000000+0500",
    "updated_at": "2026-04-15T18:10:00.000000+0500"
  },
  {
    "id": 102,
    "test": 10,
    "position": 2,
    "image": "/media/tests/images/img2.jpg",
    "status": "pending",
    "total_views": 0,
    "total_clicks": 0,
    "rounds_passed": 0,
    "wins_count": 0,
    "started_at": null,
    "created_at": "2026-04-15T18:11:00.000000+0500",
    "updated_at": "2026-04-15T18:11:00.000000+0500"
  }
]
```

#### Ошибка 404

```json
{
  "detail": "Тест не найден"
}
```

---

### 7.2 Добавление изображения

`POST /api/v1/tests/{test_id}/images/`

Требует JWT.

Формат запроса: `multipart/form-data`.

#### Fields

* `position` — number
* `image` — file

Поле `test` передавать не нужно, оно подставляется бэкендом по URL. Несмотря на то что поле `test` есть в serializer output, оно read-only.

#### Пример form-data

```text
position = 1
image = <file>
```

#### Response 201

```json
{
  "id": 101,
  "test": 10,
  "position": 1,
  "image": "/media/tests/images/example.jpg",
  "status": "pending",
  "total_views": 0,
  "total_clicks": 0,
  "rounds_passed": 0,
  "wins_count": 0,
  "started_at": null,
  "created_at": "2026-04-15T18:10:00.000000+0500",
  "updated_at": "2026-04-15T18:10:00.000000+0500"
}
```

#### Возможные ошибки

Если тест не `draft`:

```json
{
  "detail": "Можно изменять только draft тест"
}
```

Если позиция занята:

```json
{
  "position": "Позиция уже занята"
}
```

Если позиция меньше 1:

```json
{
  "position": "Позиция должна быть больше 0"
}
```

Если тест уже запущен и в него пытаются добавить изображение:

```json
{
  "detail": "Нельзя добавлять изображения после запуска теста"
}
```

---

### 7.3 Изменение изображения

`PATCH /api/v1/tests/{test_id}/images/{image_id}/`

Требует JWT.

Формат запроса: `multipart/form-data`.

Можно менять только `position` и `image`, и только пока тест в `draft`.

#### Пример form-data

```text
position = 2
```

или

```text
image = <new_file>
```

#### Response 200

```json
{
  "id": 101,
  "test": 10,
  "position": 2,
  "image": "/media/tests/images/new_example.jpg",
  "status": "pending",
  "total_views": 0,
  "total_clicks": 0,
  "rounds_passed": 0,
  "wins_count": 0,
  "started_at": null,
  "created_at": "2026-04-15T18:10:00.000000+0500",
  "updated_at": "2026-04-15T18:20:00.000000+0500"
}
```

#### Возможные ошибки

Изображение не найдено:

```json
{
  "detail": "Изображение не найдено"
}
```

Тест не `draft`:

```json
{
  "detail": "Можно изменять только draft тест"
}
```

Позиция занята:

```json
{
  "position": "Позиция уже занята"
}
```

После запуска теста менять `position` и `image` нельзя:

```json
{
  "position": "Нельзя изменять после запуска теста",
  "image": "Нельзя изменять после запуска теста"
}
```

---

### 7.4 Удаление изображения

`DELETE /api/v1/tests/{test_id}/images/{image_id}/`

Требует JWT.

#### Response 204

Тело отсутствует.

#### Ограничение

Удаление возможно только если тест в `draft`.

#### Возможные ошибки

```json
{
  "detail": "Изображение не найдено"
}
```

или

```json
{
  "detail": "Можно изменять только draft тест"
}
```

или

```json
{
  "detail": "Нельзя удалять изображение после запуска теста"
}
```

---

### 7.5 Изменение порядка изображений

`POST /api/v1/tests/{test_id}/images/reorder/`

Требует JWT.

Используется для массовой перестановки позиций. Работает только для `draft` теста. Бэкенд делает перестановку атомарно.

#### Request

```json
{
  "items": [
    {
      "id": 101,
      "position": 1
    },
    {
      "id": 102,
      "position": 2
    },
    {
      "id": 103,
      "position": 3
    }
  ]
}
```

#### Response 200

```json
{
  "detail": "Порядок обновлён"
}
```

#### Ограничения

* `items` должен быть непустым списком
* `id` не должны повторяться
* `position` не должны повторяться
* все `id` должны принадлежать этому тесту

#### Возможные ошибки

```json
{
  "items": "Должен быть список"
}
```

или

```json
{
  "detail": "Дубликаты id"
}
```

или

```json
{
  "detail": "Дубликаты position"
}
```

или

```json
{
  "detail": "Некоторые изображения не найдены"
}
```

---

## 8. Healthcheck

`GET /api/v1/health/`

Без авторизации.

Используется для проверки доступности приложения и базы данных.

### Response 200

```json
{
  "status": "ok"
}
```

### Response 503

```json
{
  "status": "db_error"
}
```

---

## 9. Что важно учесть фронту

1. Все ручки `stats` и `GET /users/me/` требуют JWT. Без токена доступны только:

   * `POST /api/v1/users/register/`
   * `GET /api/v1/users/verify-email/`
   * `POST /api/v1/auth/login/`
   * `POST /api/v1/auth/token/refresh/`
   * `GET /api/v1/health/`
2. После `register` пользователь не считается залогиненным: API не возвращает токены до подтверждения email.
3. `logout` требует и `access` в заголовке, и `refresh` в body. Refresh-токен после logout инвалидируется через blacklist.
4. `pause` не ставит тест в `paused` мгновенно. Она только просит систему остановить тест. Для актуального статуса нужно потом перечитать сам тест.
5. Для изображений upload и patch идут через `multipart/form-data`, не через обычный JSON, если передаётся файл.
6. Как только тест ушёл из `draft`, фронт должен блокировать:

   * редактирование ключевых полей теста
   * добавление изображений
   * изменение изображений
   * удаление изображений
   * reorder изображений
   * удаление самого теста

---

## 10. Быстрый список всех endpoint

```text
GET    /api/v1/health/

POST   /api/v1/users/register/
GET    /api/v1/users/verify-email/
POST   /api/v1/auth/login/
POST   /api/v1/auth/token/refresh/
POST   /api/v1/users/logout/
GET    /api/v1/users/me/

GET    /api/v1/wb-tokens/
POST   /api/v1/wb-tokens/
GET    /api/v1/wb-tokens/{id}/
PATCH  /api/v1/wb-tokens/{id}/
DELETE /api/v1/wb-tokens/{id}/

GET    /api/v1/tests/
POST   /api/v1/tests/
GET    /api/v1/tests/{id}/
PATCH  /api/v1/tests/{id}/
DELETE /api/v1/tests/{id}/

POST   /api/v1/tests/{id}/start/
POST   /api/v1/tests/{id}/pause/
POST   /api/v1/tests/{id}/resume/

GET    /api/v1/tests/{test_id}/images/
POST   /api/v1/tests/{test_id}/images/
PATCH  /api/v1/tests/{test_id}/images/{image_id}/
DELETE /api/v1/tests/{test_id}/images/{image_id}/
POST   /api/v1/tests/{test_id}/images/reorder/
