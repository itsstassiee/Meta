# Stock Metadata Editor — EPS + Getty ESP CSV

## Що змінилося
- EPS зберігають **оригінальні назви** (без префіксів та `_metadata`).
- Підтримка Title, Description, Keywords, Author, Copyright (XMP-dc).
- CSV `getty_esp_metadata.csv` із сімома полями `file name,created date,description,country,brief code,title,keywords`.
- Два режими: оновити EPS + CSV або створити CSV з існуючих XMP без зміни EPS.
- CSV UTF-8 без BOM, закінчується новим рядком. Імена файлів в CSV збігаються з іменами в папці EPS.
- Якщо у файлів однакові назви, другий пропускається, щоб не перезаписати перший.

## Розгортання Render
1. Розпакуй архів. Завантаж в корінь GitHub-репозиторію `Dockerfile`, `requirements.txt`, `app.py`, папку `templates` з `index.html`.
2. У Render під'єднай репозиторій як Web Service, Environment: Docker.
3. Після деплою відкрий адресу Render у Safari на iPad.
4. Вибери до 20 EPS, заповни метадані, натисни «Створити ZIP».
5. У Getty ESP спочатку завантаж EPS із папки `EPS/`, потім імпортуй `getty_esp_metadata.csv` через Templates → Apply from CSV.

## Важливо
- Порядок колонок Getty може відрізнятися в окремих інструментах. Перед масовим імпортом завантаж офіційний CSV-шаблон зі свого ESP та перевір порядок колонок; цей експорт використовує `file name,created date,description,country,brief code,title,keywords`.
- Getty використовує контрольований словник ключових слів. CSV не перевіряє відповідність цьому словнику.
- Для подання можуть знадобитися дата й країна; за відсутності залишені порожніми, а не вигаданими.
- EPS перевіряється на збереження BoundingBox, але це не доводить повної візуальної тотожності.
- Зміни в EPS відбуваються на копіях; оригінали користувача не змінюються.
- Публічний сервер Render не має авторизації; не завантажуй конфіденційні роботи.
- Ліміт 60 МБ сумарно на запит, до 20 файлів.


## Нове у версії з копіюванням
- Після вибору EPS редактор читає наявні XMP поля через /inspect.
- Вибір копіювання: всі інші файли або вибрані галочками.
- Вибір полів: Title, Description, Keywords, Author, Copyright, Country, Color.
- Заповнені поля не перезаписуються, якщо не увімкнути відповідний прапорець.
- Обидва режими експорту оригінального редактора збережені.
- Під час імпорту не зчитуються Country/Color з EPS: це поля Getty CSV.

## New UI features
- Read-only metadata view toggle for selected EPS.
- Remove selected EPS from current batch without deleting the original device file.
- The selected files and per-file metadata remain aligned after removing any entry.


## EPS preview (new)
The selected EPS is rendered to a temporary PNG by `/preview` using Ghostscript. The original EPS is not modified. Dockerfile installs Ghostscript. If Render uses the Dockerfile, commit all changed files and redeploy. Preview may fail for invalid or unsupported EPS; other metadata features remain available.

## Нове: додавання до відкритої групи
Повторне вибирання EPS у полі завантаження додає їх до поточного списку без скидання раніше введених метаданих. Максимум 20 файлів, назви мають бути унікальні без урахування регістру. Видалення прибирає лише файл зі списку, не з пристрою.

Нові функції: видалення повторюваних Keywords, перевірка метаданих усіх EPS, галерея з мініатюрами відкритих файлів. Для оновлення достатньо замінити templates/index.html.
