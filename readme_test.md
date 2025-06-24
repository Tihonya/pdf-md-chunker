# Перевірки на поточному етапі (v0.1)

Цей файл описує, **що саме слід протестувати зараз** у CLI-утиліті *pdf-md-chunker*, та **які результати** вважаються успішними. У другій частині наведено список наступних кроків розробки, щоб легко продовжити роботу навіть після втрати контексту.

---

## 1. Підготовка середовища

1.1. Створіть або активуйте віртуальне середовище на **Python 3.12**:
```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

1.2. Встановіть/оновіть залежності:
```bash
pip install --upgrade pip setuptools wheel --break-system-packages
pip install -r requirements.txt --break-system-packages
```

> Для Arch/Manjaro додайте прапорець `--break-system-packages` згідно з PEP 668.

---

## 2. Тестові дані

У корені проєкту лежить **`LLM_Engineers_Handbook_Master_the_art_of_engineering_large_language.pdf`** (ігнорується Git'ом). Саме його використовуємо як приклад.

---

## 3. Команда `split`

```bash
python -m pdf_md_chunker split \
       LLM_Engineers_Handbook_Master_the_art_of_engineering_large_language.pdf \
       --book-slug llm-engineers-handbook \
       --out-dir ./exports
```

Очікуємо:

1. У `./exports/llm-engineers-handbook` з'являються:
   * `book_manifest.json`
   * `README.md` (автоматично згенерований)
   * підкаталоги `part-0001_llm-engineers-handbook`, `part-0002_…`, …
2. Всередині кожного `part-*`:
   * `llm-engineers-handbook_part-0001_text.md` — Markdown текст
   * `meta.json` — метадані блоку
   * `*_img-XXXX.png` — зображення сторінок, якщо встановлено `pdf2image`
3. У консоль виводяться кроки «👉 Витягаю…», «👉 Розбиваю…», «✅ Готово!».

---

### 3.1 Перевірка структури

```bash
find ./exports/llm-engineers-handbook | head -n 20
```
Переконуємось, що структура збігається зі схемою з `TECH_SPEC.md`.

---

## 4. Команда `validate`

```bash
python -m pdf_md_chunker validate ./exports/llm-engineers-handbook
```

Очікуємо у випадку успіху:
```
✅ Валідно
```

Можливі повідомлення:
* `⚠️ … tokens …` — розбіжність кількості токенів (warning).
* `❌ …` — критична помилка (відсутній файл, ліміт >3200 тощо) та `exit 1`.

---

## 5. Ручні перевірки

1. Відкрийте кілька `*_text.md` – немає сторінкових хедерів/футерів? (очікувано **ще є** → буде вилучено у наступних кроках).
2. Переконайтеся, що `tokens` у `meta.json` ≤ 3200.
3. SHA-256 у `meta.json` збігається з:
   ```bash
   sha256sum part-0001_llm-engineers-handbook/llm-engineers-handbook_part-0001_text.md
   ```
4. Відкрийте PNG: сторінки відповідають діапазону `page_start`/`page_end`.

---

## 6. Наступні кроки розробки

> Список, з якого зручно продовжити навіть після «чистого» перезапуску.

1. **Очищення headers/footers**
   * Додати функцію фільтрації в `extract.py` (regex + евристика положення).
2. **Виявлення заголовків spaCy**
   * Pipeline: `nlp = spacy.load(lang_model)`, тег `is_heading` для елементів.
   * Розрив chunk при зустрічі заголовка рівня H2+.
3. **Покращити алгоритм sliding window**
   * Дозволити overlap ±150 токенів навколо target.
4. **Прив'язка bounding-box зображень**
   * Використати `pdfplumber` coords → обрізати сторінку до bbox.
5. **JSON schema для `meta.json` і `book_manifest.json`**
   * Зберегти у `schemas/` та використати у `validate` (модуль `jsonschema`).
6. **CI workflow**
   * `pytest` з фіктивним PDF; `ruff --fix`.
7. **Документація NotebookLM-імпорту**
   * Розширити головний `README.md` прикладами.
8. **Оптимізація продуктивності**
   * Паралельна обробка сторінок (`concurrent.futures`).
9. **Packaging & Release**
   * `pyproject.toml` (Poetry), `poe the poet` tasks, GitHub Actions → PyPI.

---

Зафіксуйте зміни:
```bash
git add readme_test.md
git commit -m "docs: тестовий чек-ліст та roadmap"
git push origin main
``` 