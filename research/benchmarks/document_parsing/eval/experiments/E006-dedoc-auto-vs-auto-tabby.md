# E006 - dedoc: `auto` vs `auto_tabby` (оба + each_page)

## 1. Approach

На одном и том же `ocr_benchmark` (24 кейса) сравниваются два бэкенда
хорошего text layer при уже включённой постраничной детекции
`each_page_textual_layer_detection=true`. Ось эксперимента — только
`pdf_with_text_layer`; маршрутизация incorrect → OCR общая.

| Вариант | Correct pages | Incorrect / scan pages |
| --- | --- | --- |
| A `auto` + each_page | native PDF text layer (`PdfTxtlayerReader`) | Tesseract OCR |
| B `auto_tabby` + each_page | Java Tabby | Tesseract OCR |

`each_page…=true` фиксирован в обоих вариантах: в реальных PDF часто бывают
точечные scan-листы внутри born-digital; без постраничной маршрутизации
сравнение reader’ов на mixed смешивается с doc-level false negative.

Остальное без изменений: table-aware linker на всех PDF-ветках (включая
txtlayer), markdown formatting, тот же scoring contract.

**Зачем:** follow-up E003/E004 — гипотеза, что склейка пробелов на mixed и
пропуск catalog-таблицы (`catalog-belimo`) — слабость Tabby, а не маршрутизации.
После фикса GT `spec-kur0130` dataset digest сменился; оба варианта гоняются
на **новом** digest, чтобы сравнение было чистым (E003-A на старом digest —
только исторический ориентир).

**Якоря:** `tu-mixed-text-scan-2236444-p028-p030`, `catalog-belimo-p020`;
guardrail — `born_digital_good` и dense tables вроде `spec-kur0130`.

## 2. Expected effect / hypothesis

**Гипотеза:** native text-layer reader (A) на correct pages даёт чище пробелы и
лучше ловит multi-column catalog layout, чем Tabby (B), при том же OCR на
scan pages. Macro на born-digital не должен заметно просесть у A относительно B;
выигрыш — локально в mixed space-collapse и catalog tables.

| Ожидание | Механизм | Критерий |
| --- | --- | --- |
| Mixed: меньше склеек на digital-страницах | Txtlayer вместо Tabby на correct pages | A: `tu-mixed` `token_f1` ≫ B; визуально пробелы на месте |
| Catalog: появляется ожидаемая таблица | Иной table path у txtlayer | A: `catalog-belimo` `teds` > 0 / pred tables = GT |
| Born-digital без регрессии | Тот же good layer, другой extractor | slice `born_digital_good` A ≈ B |
| Across-pages / dense Tabby tables | Tabby сильнее на части layout | `spec-kur0130` у A не хуже заметно, чем у B |

**Риски:** txtlayer хуже Tabby на сложных born-digital таблицах → падение
`teds`/`ast` у A; reading order на multi-column может отличаться в обе стороны.

**Adopt:** A лучше B на якорях без существенной регрессии guardrail → default
`auto` + each_page; иначе reject смены reader’а, оставить `auto_tabby` + each_page.

## 3. Runs and metrics

Оба rebuild, `eval_mode=rebuild`, `case_count=24`, один digest
`a481aa528c94abc34e7298d0b1e26243bbc97600ff7cf3782c6e267caef6750c`
(после фикса GT `spec-kur0130`). Единственный отличающийся logged param —
`dedoc.pdf_with_text_layer` (`auto` vs `auto_tabby`); у обоих
`each_page_textual_layer_detection=True`.

| Вариант | MLflow run_id | Key difference | `cer` | `token_f1` | `teds` | `teds_s` | `ast` | Notes |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| A `auto` + each_page | `606f9d56380d4276b482d14bf0eb5643` | txtlayer на correct pages | 0.711665 | 0.812833 | 0.729071 | 0.797980 | 0.614975 | run name `dedoc-auto+each_page`, `FINISHED` |
| B `auto_tabby` + each_page | `c9758f22ded345e69e8bcb168fba4b52` | Tabby на correct pages | 0.711665 | 0.812833 | 0.729071 | 0.797980 | 0.614975 | run name `dedoc-auto_tabby+each_page`, `FINISHED` |
| Δ A − B | — | — | 0 | 0 | 0 | 0 | 0 | также `wer`, `counts`, `heading_f1` без дельты |

`cases.jsonl` A и B побайтово совпадают
(`sha256=db7357ffafe6ff1f316302ce9981ecfbc4a04a2d4955191570f59ddaaa71791a`).
По всем 24 кейсам `pred.raw.md` / `pred.canonical.md` идентичны; `ocr.json`
различается (в т.ч. metadata timestamps), но извлечённый текст/таблицы для
якорей совпадают.

Якоря гипотезы (одинаковы у A и B):

| Кейс | `token_f1` | `teds` | `ast` | tables pred/gt |
| --- | ---: | ---: | ---: | --- |
| `tu-mixed-text-scan-2236444-p028-p030` | 0.259 | 1.0 | 0.405 | 0/0 |
| `catalog-belimo-p020` | 0.845 | 0 | 0.024 | 0/1 |
| `spec-kur0130-p005-p007` | 0.991 | 0.999 | 0.994 | 1/1 |

Исторический ориентир E003-A (`dae2558bc7bf4625ba70f6789170287c`, старый
digest `8be794cc…`): `token_f1=0.812057`, `teds=0.692270`, `ast=0.609294`.
Рост `teds` у E006 vs E003-A (~+0.037) нельзя относить к смене reader’а — другой
dataset digest.

## 4. Interpretation

Ожидаемый metric-level эффект A над B **не появился**: все logged macro-метрики
и per-case scores совпадают. На этом корпусе смена `auto` ↔ `auto_tabby` при
фиксированном `each_page…=true` не меняет scored Markdown.

По якорям гипотеза тоже не подтверждается на уровне метрик:

- mixed: `token_f1≈0.259` — тот же порядок, что у E003-A; критерий «≫ B / ≫ 0.26»
  не выполнен (A≡B);
- catalog: `teds=0`, таблица не найдена (`pred_count=0`, `gt_count=1`);
- guardrail `spec-kur0130` высокий у обоих (`teds≈0.999`) — риска регрессии A vs B
  нет, потому что выходы совпали.

Прямое наблюдение: scored outputs A и B идентичны. Правдоподобное объяснение,
требующее артефактов: txtlayer и Tabby на correct pages этого набора сходятся в
один и тот же markdown_formatting результат (различия в `ocr.json` не доходят до
pred). Это не доказывает, что reader’ы эквивалентны вообще — только что на
`ocr_benchmark` их отличие невидимо для текущего scoring contract.

Сравнение с E003-A по `teds` на macro **недостаточно** для вывода о reader mode:
digest сменился из‑за GT `spec-kur0130`. Для reader-оси релевантен только A vs B
на `a481aa52…`.

Статус интерпретации: гипотеза «`auto` лучше Tabby на mixed/catalog» на метриках
отклоняется (нулевой эффект). Неясно без разбора артефактов, *почему* pred
совпал и что именно ломает якоря — это предмет §5; решение adopt/reject reader
смены уже поддерживается метриками, но формулировка причин — после error analysis.

## 5. Error analysis

**A vs B: нет changed cases.** `cases.jsonl` идентичен; все `pred.raw.md`
совпали. `ocr.json` отличается на всех 24 кейсах, но на якорях это шум metadata
(timestamps вложений и т.п.): число text nodes, joined text hash и `n_tables`
совпадают. Reader mode в параметрах реально разный (`auto` / `auto_tabby` в
MLflow params и в runtime-логах), но до scored Markdown различие не доходит.
Следовательно, отсутствие дельты — не ошибка логирования одного и того же run,
а сходимость двух бэкендов на этом датасете после formatting.

**`tu-mixed-text-scan-2236444-p028-p030` — склейка пробелов на correct pages.**
Warnings: correct layer на `[1:2]`, incorrect/OCR на `[3:3]` — постраничная
маршрутизация сработала. Pred всё ещё содержит длинные «склеенные» токены
(`Установочноеположениеклапановнатрубопроводе`, …; ≥39 таких ≥25 символов), тогда
как GT с пробелами (`6 Указания по эксплуатации`, …). Это тот же дефект, что в
E003 списывали на Tabby: смена на txtlayer (`auto`) его **не сняла**. Значит,
либо оба reader’а одинаково теряют пробелы на этом PDF, либо дефект ниже по
цепочке (paragraph / markdown formatting) общий для обеих веток.

**`catalog-belimo-p020` — таблица не детектится.** Layer: correct `[1:1]` (весь
док на text-layer ветке). GT содержит pipe-таблицу (`gt_count=1`, десятки
pipe-строк); pred — сплошной текст без table blocks (`pred_count=0`, `teds=0`).
И A, и B дают один и тот же pred: multi-column catalog layout не превращается в
таблицу ни Tabby, ни txtlayer. PP-StructureV3 в E004 находил таблицу — это другой
pipeline, не закрываемый сменой `pdf_with_text_layer`.

**`spec-kur0130`:** после фикса GT (одна across-pages таблица) оба варианта дают
`1/1`, `teds≈0.999`. Не аргумент за/против `auto`; только подтверждение, что на
новом digest guardrail-таблица не просела из‑за reader’а (и не могла, при A≡B).

Итог для error analysis: целевые дыры E003/E004 (mixed spaces, catalog table)
остаются и **не разделяются** между `auto` и `auto_tabby`. Смена reader’а на
этом бенчмарке — no-op для качества; искать фикс якорей нужно вне оси
`pdf_with_text_layer` (OCR/VLM fallback, иной table path, пост-обработка пробелов).

## 6. Conclusion

**Статус: закрыт.** Ожидаемый эффект не наблюдался: на digest `a481aa52…` при
`each_page…=true` варианты `auto` и `auto_tabby` дают идентичный scored
Markdown (нулевая дельта по macro; `cases.jsonl` и `pred.*` совпадают). Якоря
гипотезы не улучшились — склейка пробелов на mixed и пропуск catalog-таблицы
остаются у обоих reader’ов. Главное объяснение: на этом корпусе txtlayer и
Tabby сходятся в один markdown после formatting, поэтому ось
`pdf_with_text_layer` здесь не рычаг качества.

## 7. Decision

Отклонить смену на `auto`. Рабочий default — `auto_tabby` +
`each_page_textual_layer_detection=true` (уже в параметрах). Дальше не
варьировать reader mode на `ocr_benchmark`; mixed/catalog закрывать вне
`pdf_with_text_layer` (узкий OCR/VLM fallback, иной table path или починка
пробелов ниже по цепочке).
