# Telegram Web3 Advisor — Полное руководство

> Это руководство написано так, чтобы его мог выполнить человек, который впервые работает с Docker, Python и Telegram-ботами. Каждый шаг объяснён с нуля.

---

## Содержание

1. [Что такое этот проект и как он работает](#1-что-такое-этот-проект-и-как-он-работает)
2. [Что нужно установить на компьютер](#2-что-нужно-установить-на-компьютер)
3. [Создание Telegram-бота](#3-создание-telegram-бота)
4. [Деплой FA-токена в тестовой сети Sepolia](#4-деплой-fa-токена-в-тестовой-сети-sepolia)
5. [Настройка файла .env](#5-настройка-файла-env)
6. [Первый запуск через Docker (без HTTPS)](#6-первый-запуск-через-docker-без-https)
7. [Локальный HTTPS для тестирования](#7-локальный-https-для-тестирования)
8. [Деплой на сервер (продакшн)](#8-деплой-на-сервер-продакшн)
9. [Структура проекта](#9-структура-проекта)
10. [Список API-эндпоинтов](#10-список-api-эндпоинтов)
11. [Частые ошибки и их решения](#11-частые-ошибки-и-их-решения)
12. [Загрузка на GitHub](#12-загрузка-на-github)

---

## 1. Что такое этот проект и как он работает

**Telegram Web3 Advisor** — это веб-приложение, которое открывается прямо внутри Telegram как «мини-приложение» (Telegram WebApp).

Пользователь может:
- войти через свой аккаунт Telegram
- привязать MetaMask-кошелёк
- видеть баланс своих FA-токенов
- переводить FA-токены другому пользователю
- получать бейджи и уведомления
- (если он администратор) отправлять рассылки всем пользователям

**Из чего состоит проект:**

```
Браузер / Telegram Mini App
        ↓ HTTP запросы
FastAPI Backend (Python)  ←→  SQLite база данных
        ↓
Web3 / Ethereum RPC
        ↓
Смарт-контракт FA-токена в сети Sepolia
```

- **Backend** — это сервер на Python (FastAPI), он обрабатывает запросы, проверяет подписи кошельков, хранит данные пользователей.
- **Frontend** — это HTML/CSS/JS страница, которую открывает пользователь в Telegram.
- **SQLite** — простая база данных в виде одного файла, хранит пользователей, их кошельки, балансы, историю переводов.
- **Ethereum Sepolia** — тестовая блокчейн-сеть (бесплатная), там живёт смарт-контракт FA-токена.

---

## 2. Что нужно установить на компьютер

### 2.1 Docker Desktop (обязательно)

Docker — это программа, которая позволяет запускать приложения в изолированных контейнерах. Вам не нужно устанавливать Python или настраивать окружение вручную — Docker сделает всё сам.

1. Откройте [https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/)
2. Нажмите **Download for Windows** (или Mac)
3. Запустите скачанный установщик, следуйте инструкциям
4. После установки **перезагрузите компьютер**
5. Запустите Docker Desktop — в трее (правый нижний угол) должен появиться значок кита

**Проверка:**
Откройте PowerShell (Win+R → `powershell`) и введите:
```powershell
docker --version
docker compose version
```
Если видите версии — Docker установлен правильно.

### 2.2 Git (опционально, для клонирования)

Если вы получили проект в виде папки или ZIP-архива — Git не нужен. Если хотите скачать через `git clone`:

1. Откройте [https://git-scm.com/download/win](https://git-scm.com/download/win)
2. Скачайте и установите с настройками по умолчанию

### 2.3 Браузер Google Chrome или Firefox

Нужен для тестирования. Edge тоже подойдёт. Internet Explorer — нет.

---

## 3. Создание Telegram-бота

Telegram WebApp работает только через бота. Бот — это «посредник», который открывает ваше приложение пользователям.

### 3.1 Создать бота через BotFather

1. Откройте Telegram, найдите бота `@BotFather` (официальный, синяя галочка)
2. Напишите `/newbot`
3. BotFather спросит **имя бота** — это отображаемое имя, например: `FA Advisor`
4. Затем спросит **username бота** — должен заканчиваться на `bot`, например: `fa_advisor_bot`
5. BotFather выдаст **токен** вида: `7123456789:AAFxyz...`
   - **Сохраните этот токен!** Он нужен для `.env`
   - Никому не передавайте токен — через него можно управлять вашим ботом

### 3.2 Добавить WebApp к боту

Чтобы бот мог открывать ваше веб-приложение:

1. В BotFather отправьте `/mybots`
2. Выберите вашего бота
3. Нажмите **Bot Settings** → **Menu Button** → **Configure menu button**
4. BotFather спросит URL — введите адрес вашего приложения (когда получите домен):
   - Для продакшна: `https://ваш-домен.ru`
   - Для теста: `https://localhost` (когда настроите локальный HTTPS из раздела 7)

> **Важно:** Telegram требует HTTPS. URL вида `http://` или `http://localhost:8000` Telegram не примет.

### 3.3 Узнать свой Telegram ID (для роли администратора)

1. Найдите бота `@userinfobot` в Telegram
2. Напишите ему что угодно
3. Он ответит вашим числовым ID, например: `Your id: 123456789`
4. Этот ID нужен для `.env` (поле `ADMIN_TELEGRAM_IDS`)

---

## 4. Деплой FA-токена в тестовой сети Sepolia

FA-токен — это учебный ERC-20 токен в тестовой сети Ethereum Sepolia. Тестовая сеть — полная копия Ethereum, но деньги там ненастоящие и бесплатные.

> Если вам пока не нужен реальный блокчейн — пропустите этот раздел. Приложение будет работать в режиме «mock» (имитация баланса) без всяких токенов.

### 4.1 Установить MetaMask

1. Откройте [https://metamask.io](https://metamask.io) → **Download**
2. Установите расширение для Chrome/Firefox
3. Создайте кошелёк, **сохраните 12 слов seed-фразы в надёжном месте**
4. В MetaMask нажмите на список сетей (обычно показано «Ethereum Mainnet») → **Add network** → **Add a network manually**:
   - Network name: `Sepolia`
   - New RPC URL: `https://rpc.sepolia.org`
   - Chain ID: `11155111`
   - Currency symbol: `ETH`
5. Переключитесь на сеть Sepolia

### 4.2 Получить бесплатный тестовый ETH

ETH нужен для оплаты комиссии при деплое контракта. В Sepolia он бесплатный:

1. Зайдите на [https://sepoliafaucet.com](https://sepoliafaucet.com) или [https://faucet.sepolia.dev](https://faucet.sepolia.dev)
2. Вставьте адрес вашего MetaMask-кошелька
3. Нажмите «Send» — через 1-2 минуты на кошельке появится 0.1-0.5 тестового ETH
4. Если один кран не работает — попробуйте другой (ищите «Sepolia testnet faucet» в Google)

### 4.3 Задеплоить контракт через Remix

Remix — это онлайн-редактор для смарт-контрактов, ничего устанавливать не нужно.

1. Откройте [https://remix.ethereum.org](https://remix.ethereum.org)
2. В левой панели нажмите иконку **«файл»** → **Create new file** → назовите `FAToken.sol`
3. Вставьте туда содержимое файла `contracts/FAToken.sol` из этого проекта
4. Нажмите иконку **компилятора** (второй значок слева) → **Compile FAToken.sol**
5. Нажмите иконку **деплоя** (третий значок, похожий на Ethereum) → в поле **Environment** выберите **Injected Provider - MetaMask**
6. MetaMask попросит подключиться — разрешите
7. Убедитесь, что в MetaMask активна сеть **Sepolia**
8. Нажмите кнопку **Deploy** → MetaMask покажет запрос транзакции → подтвердите
9. Подождите 10-30 секунд — в нижней панели Remix появится адрес контракта вида `0xAbCd...`
10. Скопируйте этот адрес — он нужен для `.env`

### 4.4 Получить RPC URL для Sepolia

RPC URL — это адрес «узла», через который приложение читает данные из блокчейна.

**Вариант А: Infura (проще всего)**
1. Зарегистрируйтесь на [https://infura.io](https://infura.io)
2. Создайте проект: **Create new API key** → **Web3 API**
3. Перейдите в проект → **Endpoints** → выберите **Sepolia** → скопируйте URL вида: `https://sepolia.infura.io/v3/abc123...`

**Вариант Б: Alchemy**
1. Зарегистрируйтесь на [https://www.alchemy.com](https://www.alchemy.com)
2. **Create app** → Network: **Ethereum Sepolia**
3. Скопируйте HTTPS URL

**Вариант В: Публичный (без регистрации, нестабильный)**
Используйте `https://rpc.sepolia.org` — бесплатно, но может быть медленно.

---

## 5. Настройка файла .env

Файл `.env` — это файл с настройками и секретами. Его **нельзя публиковать** в интернете, передавать чужим людям или коммитить в Git.

### 5.1 Создать файл .env

Откройте папку проекта. Там есть файл `.env.example` — это шаблон. Создайте копию:

**В PowerShell:**
```powershell
cd "c:\Users\<ВАШ ПОЛЬЗОВАТЕЛЬ>\<ПУТЬ ДО ПАПКИ С ПРОЕКТОМ>
copy .env.example .env
```

Откройте `.env` в любом текстовом редакторе (Блокнот, VS Code, Notepad++).

### 5.2 Заполнить каждую переменную

```dotenv
TELEGRAM_BOT_TOKEN=7123456789:AAFxyz...
```
**Что это:** Токен бота от BotFather (раздел 3.1).
**Пример:** `7123456789:AAFxyzABCDEFGHIJKLMNOPQRSTUVWXYZ`

---

```dotenv
JWT_SECRET=replace_with_strong_random_secret
```
**Что это:** Секретный ключ для шифрования токенов авторизации. Придумайте длинную случайную строку (от 32 символов).
**Как сгенерировать:** В PowerShell:
```powershell
-join ((1..48) | ForEach-Object { [char](Get-Random -Min 33 -Max 127) })
```
**Пример:** `k7Qm#nP2xW!9vR$hT6jLcB3sY0eU5dN1`

---

```dotenv
JWT_EXP_MINUTES=720
```
**Что это:** Через сколько минут истекает сессия пользователя. 720 = 12 часов. Можно оставить как есть.

---

```dotenv
WEB3_RPC_URL=https://sepolia.infura.io/v3/YOUR_INFURA_KEY
```
**Что это:** Адрес RPC-узла для чтения баланса токенов из блокчейна (раздел 4.4).
**Если не нужен блокчейн:** Оставьте пустым `WEB3_RPC_URL=` — приложение будет показывать фиктивный баланс.

---

```dotenv
FA_TOKEN_CONTRACT=0x0000000000000000000000000000000000000000
```
**Что это:** Адрес смарт-контракта FA-токена в сети Sepolia (раздел 4.3).
**Если не нужен блокчейн:** Оставьте нули.

---

```dotenv
FA_TOKEN_DECIMALS=18
```
**Что это:** Количество знаков после запятой токена. ERC-20 стандарт использует 18. Не меняйте.

---

```dotenv
FA_TOKEN_SYMBOL=FA
```
**Что это:** Символ (тикер) токена. Отображается в интерфейсе.

---

```dotenv
ADMIN_TELEGRAM_IDS=123456789
```
**Что это:** Числовые Telegram ID пользователей, которым даётся роль администратора. Несколько — через запятую: `123456789,987654321`
**Как узнать свой ID:** см. раздел 3.3.

---

**Готовый .env выглядит примерно так:**
```dotenv
TELEGRAM_BOT_TOKEN=7123456789:AAFxyzABCDEFGHIJKLMNOP
JWT_SECRET=k7Qm#nP2xW!9vR$hT6jLcB3sY0eU5dN1gF8aZ4p
JWT_EXP_MINUTES=720
WEB3_RPC_URL=https://sepolia.infura.io/v3/abc123def456
FA_TOKEN_CONTRACT=0xAbCdEf1234567890AbCdEf1234567890AbCdEf12
FA_TOKEN_DECIMALS=18
FA_TOKEN_SYMBOL=FA
ADMIN_TELEGRAM_IDS=123456789
```

---

## 6. Первый запуск через Docker (без HTTPS)

Этот режим — для первоначальной проверки, что всё работает. HTTPS здесь нет, поэтому Telegram WebApp полноценно не заработает, но сам сервер и API можно протестировать в браузере.

### 6.1 Запуск

Откройте PowerShell, перейдите в папку проекта:
```powershell
cd "c:\Users\<ВАШ ПОЛЬЗОВАТЕЛЬ>\<ПУТЬ ДО ПРОЕКТА>
```

Запустите сборку и старт:
```powershell
docker compose up -d --build
```

Что происходит:
- `--build` — Docker читает `Dockerfile` и собирает образ приложения (устанавливает Python, зависимости)
- `-d` — запускает в фоне (detached mode), не блокирует терминал
- Первый раз может занять 2-5 минут

### 6.2 Проверка статуса

```powershell
docker compose ps
```
В столбце `Status` должно быть `running`. Если `exited` — смотрите логи.

### 6.3 Просмотр логов

```powershell
docker compose logs -f web3-advisor
```
`-f` означает «следить в реальном времени». Нажмите Ctrl+C чтобы выйти.

Нормальный старт выглядит так:
```
web3-advisor  | INFO:     Started server process
web3-advisor  | INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 6.4 Открыть в браузере

Запросы принимает Caddy на порту 80, поэтому адрес **без номера порта**:

- Приложение: [http://localhost](http://localhost)
- API healthcheck: [http://localhost/api/health](http://localhost/api/health) — должен ответить `{"status":"ok"}`
- Документация API: [http://localhost/docs](http://localhost/docs) — интерактивный Swagger

> Порт 8000 доступен только внутри Docker-сети (между контейнерами). Снаружи работает только порт 80 (Caddy).

### 6.5 Остановка

```powershell
docker compose down
```

### 6.6 Пересборка после изменений кода

Если вы изменили какой-то файл проекта:
```powershell
docker compose up -d --build
```

---

## 7. Локальный HTTPS для тестирования

### Почему нужен HTTPS

Telegram Mini Apps работают **только** по HTTPS. Если открыть Mini App по адресу `http://`, Telegram покажет ошибку или просто не откроет страницу.

Для локального тестирования нужно создать «самоподписанный» SSL-сертификат, которому доверяет ваш браузер. Для этого используется инструмент **mkcert**.

Схема работы:
```
Браузер → HTTPS :443 → Caddy (reverse proxy) → HTTP :8000 → FastAPI
```

**Caddy** — это лёгкий веб-сервер, который принимает HTTPS-соединения, расшифровывает их и передаёт дальше на ваш FastAPI-сервер.

### 7.1 Установить mkcert (Windows)

mkcert — это программа, которая создаёт SSL-сертификаты, которым доверяет ваш браузер.

**Способ 1 — через Chocolatey (пакетный менеджер):**

Если у вас не установлен Chocolatey, откройте PowerShell **от имени администратора** (правая кнопка на PowerShell → «Запуск от имени администратора»):
```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
```

Закройте PowerShell и откройте новый (от администратора), затем:
```powershell
choco install mkcert -y
```

**Способ 2 — скачать вручную:**

1. Откройте страницу [https://github.com/FiloSottile/mkcert/releases/latest](https://github.com/FiloSottile/mkcert/releases/latest)
2. Скачайте файл `mkcert-v1.x.x-windows-amd64.exe`
3. Переименуйте его в `mkcert.exe`
4. Скопируйте в папку `C:\Windows\System32\` (нужны права администратора)

**Проверка:**
```powershell
mkcert --version
```

### 7.2 Установить корневой сертификат mkcert

Эта команда добавляет mkcert в список доверенных центров сертификации вашего компьютера. После этого все сертификаты, выданные mkcert, браузер будет считать доверенными.

Откройте PowerShell **от имени администратора**:
```powershell
mkcert -install
```

Появится диалог — подтвердите установку.

> **Это нужно сделать только один раз** на данном компьютере.

### 7.3 Сгенерировать сертификат для localhost

В папке проекта создайте подпапку для сертификатов:
```powershell
cd "c:\Users\<ВАШ ПОЛЬЗОВАТЕЛЬ>\<ПУТЬ ДО ПРОЕКТА>
mkdir certs
cd certs
mkcert localhost 127.0.0.1 ::1
```

Команда создаст два файла:
- `localhost+2.pem` — сам сертификат (публичный ключ)
- `localhost+2-key.pem` — приватный ключ

> Держите приватный ключ в тайне. Добавьте `certs/` в `.gitignore` если используете Git.

Переименуйте файлы для удобства:
```powershell
rename-item "localhost+2.pem" "localhost.pem"
rename-item "localhost+2-key.pem" "localhost-key.pem"
cd ..
```

### 7.4 Конфигурация Caddy (Caddyfile.local)

Файл `Caddyfile.local` уже есть в корне проекта. Он настроен на **HTTP** (порт 80) — это самый простой и надёжный вариант для локальной разработки:

```
:80 {
    reverse_proxy web3-advisor:8000
}
```

> **Важно:** между `:80` и `{` должен быть пробел. Без пробела Caddy выдаёт ошибку `Site addresses cannot end with a curly brace`.

**Если нужен HTTPS локально** (например, для тестирования cookie с флагом Secure), обновите `Caddyfile.local` до:

```
https://localhost {
    tls /certs/localhost.pem /certs/localhost-key.pem
    reverse_proxy web3-advisor:8000
}
```

…и предварительно создайте сертификаты (шаги 7.1–7.3).

**Объяснение текущего варианта:**
- `:80` — Caddy слушает HTTP на порту 80
- `reverse_proxy web3-advisor:8000` — пересылает запросы на FastAPI-сервер внутри Docker-сети
- Для работы через ngrok HTTPS внутри не нужен — ngrok сам шифрует трафик снаружи

### 7.5 Текущий docker-compose.yml

Файл `docker-compose.yml` уже настроен правильно. Для справки — его актуальное содержимое:

```yaml
name: web3-advisor

services:
  web3-advisor:
    build:
      context: .
      dockerfile: backend/Dockerfile
    container_name: web3-advisor
    expose:
      - "8000"
    restart: unless-stopped
    environment:
      - DATABASE_URL=sqlite:////data/advisor.db
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - JWT_SECRET=${JWT_SECRET}
      - JWT_EXP_MINUTES=${JWT_EXP_MINUTES:-720}
      - WEB3_RPC_URL=${WEB3_RPC_URL}
      - FA_TOKEN_CONTRACT=${FA_TOKEN_CONTRACT}
      - FA_TOKEN_DECIMALS=${FA_TOKEN_DECIMALS:-18}
      - FA_TOKEN_SYMBOL=${FA_TOKEN_SYMBOL:-FA}
      - ADMIN_TELEGRAM_IDS=${ADMIN_TELEGRAM_IDS}
    volumes:
      - advisor_data:/data

  caddy:
    image: caddy:2-alpine
    container_name: web3-caddy
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile.local:/etc/caddy/Caddyfile:ro
      - ./certs:/certs:ro
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - web3-advisor
    restart: unless-stopped

volumes:
  advisor_data:
  caddy_data:
  caddy_config:
```

**Ключевые моменты:**
- `name: web3-advisor` — обязательное поле; без него Docker Compose выдаёт ошибку `project name must not be empty`
- `web3-advisor` не публикует порт 8000 напрямую — только внутри Docker-сети (через `expose`)
- `caddy` слушает порты 80 и 443 и проксирует запросы на `web3-advisor:8000`
- Том `./certs:/certs:ro` монтируется даже при HTTP-конфигурации — просто не используется; если папки `certs/` нет, создайте её: `mkdir certs`

### 7.6 Запустить с HTTPS

```powershell
cd "c:\Users\<ВАШ ПОЛЬЗОВАТЕЛЬ>\<ПУТЬ ДО ПРОЕКТА>
docker compose up -d --build
```

Проверка:
- Откройте [https://localhost](https://localhost) в браузере
- Браузер должен показать приложение **без предупреждения о небезопасном соединении** (замочек в адресной строке)

Если браузер показывает предупреждение — значит сертификат не установлен. Повторите шаги 7.2-7.3.

### 7.7 Прокинуть локальный HTTPS в интернет для теста с Telegram

Telegram требует, чтобы WebApp-URL был доступен из интернета. Для временного теста можно использовать **ngrok** или **Cloudflare Tunnel**.

**Способ с ngrok (самый простой):**

1. Зарегистрируйтесь на [https://ngrok.com](https://ngrok.com) (бесплатно)
2. Скачайте ngrok для Windows, распакуйте, добавьте в PATH
3. Авторизуйте ngrok (токен из личного кабинета):
   ```powershell
   ngrok config add-authtoken ВАШ_ТОКЕН
   ```
4. Запустите туннель (пока `docker compose up` работает):
   ```powershell
   ngrok http 80
   ```
   Если используете HTTPS локально (mkcert + Caddyfile с `https://localhost`), тогда `ngrok http 443`.
5. ngrok выдаст URL вида `https://abc123.ngrok-free.app` — это и есть ваш временный HTTPS-адрес
6. Этот URL вставьте в BotFather как URL кнопки меню бота

> Бесплатный ngrok меняет URL при каждом перезапуске. Для постоянной работы нужен продакшн-сервер (раздел 8).

---

## 8. Деплой на сервер (продакшн)

В продакшне приложение работает на удалённом Linux-сервере 24/7. Пользователи открывают его через постоянный URL с настоящим SSL-сертификатом.

### 8.1 Что потребуется

- **VPS** (виртуальный сервер) — арендованный у хостинг-провайдера
  - Минимальные требования: 1 CPU, 1 GB RAM, 10 GB SSD
  - Операционная система: **Ubuntu 22.04 LTS** (рекомендуется)
  - Популярные провайдеры: DigitalOcean, Hetzner, Timeweb, REG.RU
- **Домен** — например `fa-advisor.ru` или `fa.example.com`
  - Купить на reg.ru, timeweb.ru, namecheap.com и т.д.
  - Стоимость от 100-200 руб./год для `.ru`

### 8.2 Настройка домена

Когда купите VPS, провайдер выдаст вам **IP-адрес сервера**, например `5.10.20.30`.

Нужно привязать ваш домен к этому IP:

1. Войдите в панель управления доменом у вашего регистратора
2. Найдите раздел **DNS-записи** (DNS Management, Name Server Records)
3. Создайте запись типа **A**:
   - Имя (Host): `@` (означает корневой домен) или `fa` (для поддомена `fa.example.com`)
   - Значение (Value/Points to): `5.10.20.30` (ваш IP сервера)
   - TTL: 3600
4. Если хотите и `www.fa-advisor.ru` — создайте ещё одну A-запись с именем `www`
5. Подождите 5-30 минут, пока DNS распространится

**Проверка:** В PowerShell на вашем компьютере:
```powershell
nslookup fa-advisor.ru
```
Должен вернуть ваш IP сервера.

### 8.3 Подключение к серверу

Для управления сервером используется **SSH** — защищённое соединение с командной строкой сервера.

**На Windows:**
1. Откройте PowerShell
2. Подключитесь (замените IP и имя пользователя):
   ```powershell
   ssh root@5.10.20.30
   ```
3. При первом подключении спросит подтвердить — напишите `yes`
4. Введите пароль (его дал провайдер при создании сервера)

Теперь вы внутри сервера. Все команды ниже выполняются там.

### 8.4 Установка Docker на сервер (Ubuntu 22.04)

```bash
# Обновить список пакетов
apt update

# Установить зависимости
apt install -y ca-certificates curl gnupg

# Добавить официальный GPG-ключ Docker
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

# Добавить репозиторий Docker
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Установить Docker
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Проверка
docker --version
docker compose version
```

### 8.5 Скопировать проект на сервер

**Способ 1 — через Git (если проект на GitHub/GitLab):**
```bash
cd /opt
git clone https://github.com/ВАШ_АККАУНТ/ВАШ_РЕПОЗИТОРИЙ.git advisor
cd advisor
```

**Способ 2 — через SCP (загрузить с вашего компьютера):**

В PowerShell **на вашем компьютере** (не на сервере):
```powershell
# Создать архив проекта (исключая .venv и базу данных)
cd "c:\Users\<ВАШ ПОЛЬЗОВАТЕЛЬ>\<ПУТЬ ДО ПРОЕКТА>
Compress-Archive -Path ".\CT_project\*" -DestinationPath "advisor.zip" -Force

# Загрузить на сервер
scp advisor.zip root@5.10.20.30:/opt/
```

Затем на сервере:
```bash
cd /opt
apt install -y unzip
unzip advisor.zip -d advisor
cd advisor
```

### 8.6 Создать .env на сервере

На сервере создайте файл `.env`:
```bash
nano .env
```

Вставьте содержимое (Ctrl+Shift+V для вставки в PuTTY/PowerShell SSH):
```dotenv
TELEGRAM_BOT_TOKEN=ВАШ_ТОКЕН
JWT_SECRET=ДЛИННЫЙ_СЛУЧАЙНЫЙ_СЕКРЕТ
JWT_EXP_MINUTES=720
WEB3_RPC_URL=https://sepolia.infura.io/v3/ВАШ_КЛЮЧ
FA_TOKEN_CONTRACT=0xАДРЕС_КОНТРАКТА
FA_TOKEN_DECIMALS=18
FA_TOKEN_SYMBOL=FA
ADMIN_TELEGRAM_IDS=ВАШ_TELEGRAM_ID
```

Сохраните: Ctrl+O → Enter → Ctrl+X

### 8.7 Настроить автоматический HTTPS через Caddy

В продакшне Caddy сам получает и обновляет SSL-сертификаты от **Let's Encrypt** (бесплатный центр сертификации). Вам ничего делать не нужно — только указать домен.

Создайте файл `Caddyfile` в папке проекта:
```bash
nano Caddyfile
```

Вставьте (замените `fa-advisor.ru` на ваш домен):
```
fa-advisor.ru {
    reverse_proxy web3-advisor:8000
}
```

Сохраните: Ctrl+O → Enter → Ctrl+X.

**Что происходит автоматически:**
- Caddy при первом старте обращается к Let's Encrypt
- Let's Encrypt проверяет, что домен `fa-advisor.ru` указывает на этот сервер
- Let's Encrypt выдаёт бесплатный SSL-сертификат на 90 дней
- Caddy автоматически продлевает его до истечения

> **Важно:** Домен должен уже указывать на IP сервера (раздел 8.2). Иначе Let's Encrypt не сможет проверить домен и откажет в сертификате.

### 8.8 Обновить docker-compose.yml для продакшна

Откройте файл:
```bash
nano docker-compose.yml
```

Замените содержимое на:
```yaml
name: web3-advisor

services:
  web3-advisor:
    build:
      context: .
      dockerfile: backend/Dockerfile
    container_name: web3-advisor
    expose:
      - "8000"
    restart: unless-stopped
    environment:
      - DATABASE_URL=sqlite:////data/advisor.db
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - JWT_SECRET=${JWT_SECRET}
      - JWT_EXP_MINUTES=${JWT_EXP_MINUTES:-720}
      - WEB3_RPC_URL=${WEB3_RPC_URL}
      - FA_TOKEN_CONTRACT=${FA_TOKEN_CONTRACT}
      - FA_TOKEN_DECIMALS=${FA_TOKEN_DECIMALS:-18}
      - FA_TOKEN_SYMBOL=${FA_TOKEN_SYMBOL:-FA}
      - ADMIN_TELEGRAM_IDS=${ADMIN_TELEGRAM_IDS}
    volumes:
      - advisor_data:/data

  caddy:
    image: caddy:2-alpine
    container_name: web3-caddy
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - web3-advisor
    restart: unless-stopped

volumes:
  advisor_data:
  caddy_data:
  caddy_config:
```

Сохраните: Ctrl+O → Enter → Ctrl+X.

> Строка `name: web3-advisor` обязательна — без неё Docker Compose выдаёт ошибку `project name must not be empty`.

### 8.9 Открыть порты в файрволе

Ubuntu по умолчанию может блокировать входящие соединения. Разрешим порты 80 (HTTP) и 443 (HTTPS):

```bash
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 22/tcp
ufw enable
```

Команда `ufw status` покажет правила.

### 8.10 Запустить приложение

```bash
cd /opt/advisor
docker compose up -d --build
```

Первый запуск займёт 3-7 минут (скачивание образов, сборка).

**Проверка:**
```bash
docker compose ps
```
Оба сервиса — `web3-advisor` и `web3-caddy` — должны иметь статус `running`.

```bash
docker compose logs -f
```
В логах Caddy должно появиться что-то вроде:
```
caddy  | {"msg":"certificate obtained successfully","domain":"fa-advisor.ru"}
```

Откройте в браузере `https://fa-advisor.ru` — должно работать с зелёным замочком.

### 8.11 Настроить WebApp URL в BotFather

Теперь нужно сказать Telegram, где находится ваше приложение:

1. Откройте BotFather в Telegram
2. `/mybots` → выберите бота → **Bot Settings** → **Menu Button** → **Configure menu button**
3. Введите `https://fa-advisor.ru` (ваш домен)
4. Готово. Теперь кнопка в боте открывает ваше приложение.

### 8.12 Настроить автозапуск Docker при перезагрузке сервера

Docker-сервис должен стартовать автоматически при перезагрузке:
```bash
systemctl enable docker
```

Контейнеры с параметром `restart: unless-stopped` (он уже есть в docker-compose.yml) также стартуют автоматически вместе с Docker.

### 8.13 Мониторинг и обслуживание

**Просмотр логов в реальном времени:**
```bash
docker compose logs -f
```

**Перезапустить только один сервис:**
```bash
docker compose restart web3-advisor
```

**Обновить приложение (после изменений кода):**
```bash
cd /opt/advisor
git pull  # если используете Git
docker compose up -d --build
```

**Резервная копия базы данных:**
```bash
docker compose exec web3-advisor cp /data/advisor.db /data/advisor_backup_$(date +%Y%m%d).db
# Скачать на компьютер:
docker cp web3-advisor:/data/advisor.db ./advisor_backup.db
```

**Сколько места занимает Docker:**
```bash
docker system df
```

**Очистить неиспользуемые образы (осторожно):**
```bash
docker system prune -f
```

---

## 9. Структура проекта

```
CT_project/
│
├── backend/                     ← Python-сервер
│   ├── app/
│   │   ├── main.py              ← Все API-маршруты
│   │   ├── auth.py              ← Авторизация (Telegram + JWT)
│   │   ├── database.py          ← Модели базы данных (SQLite)
│   │   ├── schemas.py           ← Описание форматов запросов/ответов
│   │   ├── services.py          ← Бизнес-логика (nonce, подписи, рассылки)
│   │   ├── web3_client.py       ← Чтение баланса из блокчейна
│   │   └── config.py            ← Чтение настроек из .env
│   ├── Dockerfile               ← Инструкция по сборке контейнера
│   └── requirements.txt         ← Список Python-зависимостей
│
├── frontend/                    ← Веб-интерфейс (HTML/CSS/JS)
│   ├── index.html               ← Разметка страницы
│   ├── style.css                ← Стили (тёмная тема, бордовые акценты)
│   └── app.js                   ← Логика интерфейса
│
├── contracts/
│   └── FAToken.sol              ← Смарт-контракт ERC-20 токена (Solidity)
│
├── certs/                       ← Локальные SSL-сертификаты (не в Git)
│   ├── localhost.pem
│   └── localhost-key.pem
│
├── docker-compose.yml           ← Конфигурация Docker-сервисов
├── Caddyfile                    ← Конфигурация веб-сервера Caddy (продакшн)
├── Caddyfile.local              ← Конфигурация Caddy для локального теста
├── .env                         ← Секреты и настройки (не в Git!)
├── .env.example                 ← Шаблон .env
└── README.md                    ← Это руководство
```

---

## 10. Список API-эндпоинтов

Все эндпоинты доступны по адресу `https://ваш-домен/api/...`

| Метод | Путь | Описание | Авторизация |
|-------|------|----------|-------------|
| `GET` | `/api/health` | Проверка работоспособности сервера | Нет |
| `POST` | `/api/auth/telegram` | Вход через Telegram (проверка initData) | Нет |
| `GET` | `/api/auth/me` | Профиль текущего пользователя | JWT |
| `POST` | `/api/auth/nonce` | Шаг 1 привязки кошелька: получить сообщение для подписи | JWT |
| `POST` | `/api/auth/verify` | Шаг 2 привязки кошелька: проверить подпись | JWT |
| `GET` | `/api/dashboard/me` | Баланс FA, бейджи, уведомления | JWT |
| `POST` | `/api/transfer` | Перевести FA-токены на другой кошелёк | JWT |
| `POST` | `/api/admin/broadcast` | Отправить рассылку (только admin) | JWT + Admin |
| `GET` | `/api/admin/broadcast/logs` | История рассылок (только admin) | JWT + Admin |

Интерактивная документация (Swagger): `https://ваш-домен/docs`

---

## 11. Частые ошибки и их решения

### «project name must not be empty»
В файле `docker-compose.yml` нет поля `name`. Добавьте первой строкой:
```yaml
name: web3-advisor
```
Это происходит, когда имя папки проекта содержит кириллицу или специальные символы и Docker Compose не может вывести имя автоматически.

---

### «Site addresses cannot end with a curly brace: ':80{'»
Синтаксическая ошибка в `Caddyfile.local` — нет пробела между адресом и открывающей скобкой.

Неправильно:
```
:80{
```
Правильно:
```
:80 {
```

---

### «open /certs/localhost.pem: no such file or directory»
Caddy ищет TLS-сертификат, которого нет. Два варианта решения:

**Вариант А (рекомендуется для локала):** Переключитесь на HTTP в `Caddyfile.local`:
```
:80 {
    reverse_proxy web3-advisor:8000
}
```

**Вариант Б:** Создайте сертификаты через mkcert (см. раздел 7.1–7.3) и убедитесь, что папка `certs/` смонтирована в docker-compose.yml.

---

### ngrok: ERR_NGROK_8012 «No connection could be made»
ngrok не может подключиться к локальному сервису. Причины:
1. Контейнеры не запущены — проверьте `docker compose ps`
2. Caddy упал из-за ошибки в конфигурации — проверьте `docker compose logs caddy`
3. ngrok указывает не на тот порт — используйте `ngrok http 80` (а не 8000, т.к. Caddy на порту 80)

---

### «docker: command not found» или «docker compose: command not found»
Docker не установлен или не добавлен в PATH. Перезапустите PowerShell после установки Docker Desktop.

---

### «Error: .env file not found» или пустые переменные
Убедитесь, что файл `.env` существует в корне проекта (рядом с `docker-compose.yml`). Проверьте:
```powershell
ls .env
```

---

### Браузер показывает «Ваше подключение не защищено» на localhost
- Убедитесь, что выполнили `mkcert -install` от имени администратора
- Убедитесь, что сертификаты лежат в папке `certs/` и названы `localhost.pem` / `localhost-key.pem`
- Попробуйте очистить кэш браузера (Ctrl+Shift+Delete)
- В Chrome: попробуйте набрать `thisisunsafe` прямо на странице с предупреждением

---

### Caddy не получает сертификат (продакшн)
Проверьте:
1. Домен действительно указывает на IP сервера: `nslookup ваш-домен.ru`
2. Порты 80 и 443 открыты в файрволе: `ufw status`
3. Нет другого процесса на портах 80/443: `ss -tlnp | grep -E ':80|:443'`
4. Логи Caddy: `docker compose logs caddy`

---

### «Telegram auth error» / «Invalid hash»
- Проверьте `TELEGRAM_BOT_TOKEN` в `.env` — он должен совпадать с токеном от BotFather
- Убедитесь, что нет пробелов в начале/конце токена

---

### «Получатель с таким адресом не зарегистрирован» при переводе токенов
Получатель должен быть зарегистрирован в системе: войти через Telegram и привязать кошелёк. Только после этого его адрес появится в базе данных.

---

### Контейнер постоянно перезапускается
Смотрите логи:
```bash
docker compose logs --tail=50 web3-advisor
```
Чаще всего причина — ошибка в `.env` (неправильный токен, пустое обязательное поле).

---

### База данных потеряна после `docker compose down`
Данные хранятся в Docker-томе `advisor_data`. Команда `docker compose down` тома не удаляет. Но `docker compose down -v` удаляет всё — **не используйте** `-v` если не хотите потерять данные.

---

### Как посмотреть содержимое базы данных

```bash
docker compose exec web3-advisor python3 -c "
import sqlite3
conn = sqlite3.connect('/data/advisor.db')
for row in conn.execute('SELECT telegram_id, wallet_address, balance_fa, role FROM users'):
    print(row)
"
```

---

*Если что-то не работает и здесь нет ответа — посмотрите логи (`docker compose logs -f`) и найдите строку с `ERROR`. Она обычно объясняет причину проблемы.*

---

## 12. Загрузка на GitHub

GitHub — это платформа для хранения кода. Туда загружают проект, чтобы:
- работать с него на любом компьютере
- делиться кодом с командой
- деплоить на сервер через `git clone`

### 12.1 Что загружать на GitHub

| Загружать | Почему |
|-----------|--------|
| `backend/` (без `advisor.db`) | Весь серверный код |
| `frontend/` | HTML/CSS/JS |
| `contracts/` | Смарт-контракт |
| `docker-compose.yml` | Конфигурация сервисов |
| `Caddyfile.local` | Конфиг Caddy для локала |
| `.env.example` | Шаблон настроек (без секретов) |
| `README.md` | Документация |
| `.gitignore` | Правила игнорирования |

### 12.2 Что НЕ загружать (скрыть)

| Файл / папка | Почему нельзя |
|--------------|---------------|
| `.env` | Содержит реальные секреты: токен бота, JWT-ключ, Infura API key, адреса |
| `certs/` | Локальные TLS-сертификаты — бесполезны другим, лучше пересоздать |
| `.venv/` | Виртуальное окружение Python — пересоздаётся через `pip install` |
| `backend/advisor.db` | База данных с реальными данными пользователей |
| `__pycache__/`, `*.pyc` | Временные скомпилированные файлы |

Все эти пути уже прописаны в `.gitignore` — Git их автоматически игнорирует.

> **Если `.env` случайно попал на GitHub:** немедленно отзовите токен у `@BotFather` (`/revoke`), сгенерируйте новый `JWT_SECRET` и замените ключ Infura в личном кабинете. Публичный репозиторий сканируют боты за секунды.

### 12.3 Первая загрузка (новый репозиторий)

**Шаг 1 — Создать репозиторий на GitHub**

1. Зайдите на [github.com](https://github.com) → кнопка **New** (или **+** → New repository)
2. Название: `web3-advisor`
3. Видимость: **Private** (рекомендуется) или Public
4. Нажмите **Create repository** — не ставьте галочки Initialize, .gitignore, license

**Шаг 2 — Инициализировать Git локально**

```powershell
cd "c:\Users\<ВАШ ПОЛЬЗОВАТЕЛЬ>\<ПУТЬ ДО ПРОЕКТА>
git init
git add .
```

**Шаг 3 — Проверить, что секреты не попадут**

```powershell
git status
```

Файл `.env` должен отсутствовать в списке (он серый — игнорируется). Папки `.venv/` и `certs/` тоже не должны быть в списке.

**Шаг 4 — Сделать первый коммит**

```powershell
git commit -m "Initial commit"
```

**Шаг 5 — Привязать к GitHub и отправить**

На странице созданного репозитория скопируйте URL вида `https://github.com/ВАШ_ЛОГИН/web3-advisor.git`, затем:

```powershell
git remote add origin https://github.com/ВАШ_ЛОГИН/web3-advisor.git
git branch -M main
git push -u origin main
```

GitHub попросит войти — введите логин и пароль (или Personal Access Token если включена двухфакторная аутентификация).

### 12.4 Отправка изменений после правок кода

```powershell
git add .
git commit -m "Краткое описание изменений"
git push
```

### 12.5 Скачать проект на другом компьютере или сервере

```bash
git clone https://github.com/ВАШ_ЛОГИН/web3-advisor.git
cd web3-advisor
cp .env.example .env
# Откройте .env и заполните реальными значениями
docker compose up -d --build
```

### 12.6 Что показывать в README на GitHub

GitHub автоматически отображает `README.md` на главной странице репозитория. Если репозиторий публичный — убедитесь, что в README нет реальных токенов, адресов кошельков или API-ключей. Используйте только примеры вида `YOUR_TOKEN_HERE`.
