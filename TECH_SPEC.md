
# Технічне завдання  
## «PDF → Markdown‑Chunks»  
**Версія 1.0 – 24 червня 2025**

### 1. Мета
Створити CLI‑утиліту на Python, яка:
1. Приймає PDF‑книгу (або набір PDF’ів).
2. Розбиває вміст на блоки ≈ **1500 токенів** (hard‑ліміт — **3200**).
3. Зберігає кожен блок у Markdown‑файл + окремі зображення.
4. Додає метадані для однозначного зв’язку *книга ↔ частина*.
5. Формат та структура відповідають вимогам NotebookLM.

### 2. Технологічний стек
| Етап | Бібліотека / інструмент | Причина |
|------|-------------------------|---------|
|Витяг PDF|`unstructured` (fallback → `pdfplumber`)|Текст, координати, зображення|
|Конвертація сторінок|`pdf2image`|PNG / JPEG без втрати якості|
|NLP заголовків|spaCy (`en`, `uk`)|Мовна агностика|
|Токензатор|`tiktoken` `cl100k_base`|Підрахунок токенів|
|Chunking|Власний `Chunker`|Алгоритм нижче|
|Дедуплікація|`rapidfuzz`|>=90 % схожості|
|CLI|`Typer`|Зручна обгортка|
|Управління|`Poetry`, `pyenv`, `Poe the Poet`|Депенденсі, ізоляція, таски|

### 3. Алгоритм розбивки
```text
PDF
 ├─ Витяг тексту+зображень
 ├─ Очистка (headers/footers)
 ├─ Виявлення заголовків
 │    └─ hard‑break якщо знайдено
 ├─ Якщо ні — sliding window 1500±150 ток
 ├─ Перевірка hard‑ліміту 3200 ток
 ├─ Дедуплікація rapidfuzz (90 %)
 ├─ Прив’язка зображень (bbox ⊂ page‑range)
 └─ Збереження (Markdown + PNG + meta)
```

### 4. Структура виходу
```
<slug_book>/
├── book_manifest.json
├── README.md
├── part-0001_<slug>/
│   ├── <slug>_part-0001_text.md
│   ├── <slug>_part-0001_img-0001.png
│   └── meta.json
├── part-0002_<slug>/
│   └── ...
└── ...
```
*Slug* — ASCII‑lowercase, пробіли→«-».

### 4.1 `book_manifest.json`
```json
{
  "book_id": "designing-llm-apps",
  "title": "Designing Large Language Model Applications",
  "author": "Suhas Pai",
  "isbn": "9781098150501",
  "language": "en",
  "parts": 42,
  "chunk_token_target": 1500,
  "chunk_token_max": 3200,
  "generated": "2025-06-24T12:00:00Z"
}
```

### 4.2 `meta.json` (для блоку)
```json
{
  "part_id": "designing-llm-apps_part-0001",
  "page_start": 1,
  "page_end": 3,
  "tokens": 1490,
  "images": ["designing-llm-apps_part-0001_img-0001.png"],
  "source_pdf": "Designing_Large_Language_Model_Applications_A_Holistic.pdf",
  "checksum": "sha256:…",
  "created": "2025-06-24T12:01:00Z"
}
```

### 5. CLI‑інтерфейс
```bash
python -m cli split <book.pdf>        --book-slug designing-llm-apps        --out-dir ./exports
python -m cli validate ./exports/designing-llm-apps
```
Всі таски продубльовані в `pyproject.toml` через **Poe the Poet**.

### 6. Параметри
| Параметр | Default | Коментар |
|----------|---------|----------|
|`--chunk-tokens`|1500|бажана довжина|
|`--chunk-max`|3200|жорсткий ліміт|
|`--lang`|auto|`en` / `uk` / auto|
|`--quality-threshold`|0.9|rapidfuzz ratio|

### 7. Definition of Done
1. Жоден Markdown >3200 токенів; 95 % сторінок покрито.  
2. Дублі (≥90 %) видалено.  
3. Усі `meta.json` валідні (`jsonschema`).  
4. `pytest` + `ruff ‑‑fix` зелений у CI.  
5. README пояснює імпорт до NotebookLM.

### 8. Ліцензія
Код — MIT; PDF‑контент — лише для особистого використання.
