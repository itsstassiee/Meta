# Stock Metadata Editor — Render Free / iPad

## Розгортання
1. Створи приватний GitHub репозиторій.
2. Завантаж в корінь репозиторію `Dockerfile`, `requirements.txt`, `app.py`, папку `templates` з `index.html`.
3. У https://dashboard.render.com натисни New → Web Service → GitHub repository.
4. Language: Docker; Instance: Free; Root directory: порожньо.
5. Deploy. Відкрий адресу `https://<назва>.onrender.com` у Safari на iPad.
6. Обери EPS, заповни поля, завантаж ZIP та збережи через меню Safari у «Файли».

## Обмеження
- Безкоштовний Render засинає після 15 хвилин неактивності.
- Файли обробляються у тимчасовій папці та не зберігаються навмисно. Однак це публічно доступний сервер: перед реальним використанням варто додати авторизацію.
- ExifTool записує XMP-dc Title/Description/Subject. Це **не гарантує**, що Shutterstock імпортує ключові слова EPS.
- Перевірка BoundingBox не доводить повної візуальної тотожності; перевіряй EPS перед публікацією.
- Якщо EPS має нестандартний формат або ExifTool не підтримує запис, файл пропускається з повідомленням у processing_notes.txt.
- Усі файли в пакеті мають обмеження сумарного розміру запиту 60 МБ.
