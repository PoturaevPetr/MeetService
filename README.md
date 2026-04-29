# MeetService

Сервис **сигналинга WebRTC** для аудио/видеозвонков 1:1. Медиа идёт напрямую между клиентами (peer-to-peer); сервер хранит состояние звонка и пересылает SDP / ICE.

## Совместимость с ChatService

Используйте тот же **`JWT_SECRET_KEY`**, что и в ChatService: клиентский **access**-токен (`Authorization: Bearer …`, `type=access`, `sub=user_uuid`) принимается без отдельной выдачи токенов MeetService.

## Запуск локально

```bash
cd MeetService
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# задайте JWT_SECRET_KEY (как в ChatService)
export USE_SQLITE=true
uvicorn server.main:app --reload --port 8480
```

- Здоровье: `GET http://127.0.0.1:8480/health`
- Документация: `http://127.0.0.1:8480/docs`

## HTTP API (префикс `/api/v1`)

| Метод | Путь | Описание |
|--------|------|-----------|
| GET | `/config/ice-servers` | Список ICE-серверов для `RTCPeerConnection` (нужен Bearer) |
| POST | `/calls` | Создать звонок: тело `{"peer_user_id":"<uuid>","room_id":null}` |
| GET | `/calls/{call_id}` | Статус звонка |

## WebSocket

`GET /ws/signaling?token=<JWT access token>`

После подключения сервер шлёт:

- `connected` — ваш `user_id`
- `signal.ice_servers` — ICE из настроек

Клиентские сообщения (JSON):

| type | Назначение |
|------|------------|
| `ping` | проверка связи → `pong` |
| `call.invite` | начать звонок (альтернатива POST `/calls`) |
| `call.accept` / `call.reject` / `call.cancel` / `call.end` | управление сессией |
| `webrtc.offer` / `webrtc.answer` / `webrtc.ice_candidate` | обмен SDP и ICE с собеседником |

События входящего звонка у получателя: `call.incoming` (если онлайн по WS).

## Переменные окружения

| Переменная | Описание |
|-------------|-----------|
| `JWT_SECRET_KEY` | Общий с ChatService секрет HS256 |
| `DATABASE_URL` | Postgres URL, если не SQLite |
| `USE_SQLITE` | `true` — файл `SQLITE_PATH` |
| `ICE_SERVERS_JSON` | JSON-массив объектов `urls` / `username` / `credential` для TURN |

## Дальше

- В **ChatService** задайте **`MEET_SERVICE_PUBLIC_URL`** (тот же origin, без слэша в конце) — клиент **ChatApp** после входа запрашивает `GET /api/v1/client/meet-service` и подставляет URL **без пересборки** приложения.
- Локально можно по-прежнему задать **`NEXT_PUBLIC_MEET_SERVICE_URL`** в ChatApp — он перекрывает ответ API.
- Прод: выделенный **coturn**, мониторинг, ограничение частоты создания звонков.
