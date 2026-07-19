# E007 - HTML-таблицы в extraction-цепочке

## 1. Approach

Замена **представления таблиц** в extraction-пайплайне: с кастомного pipe-markdown на **HTML** (свой сериализатор cell grid → `<table>`/`<tr>`/`<td>` с нативными `rowspan`/`colspan`; штатного `Table.to_html` в установленном dedoc нет). OCR для УКДИМ выравниваем с прогоном [E003](E003-ukidim-dense-gt.md) / ориентиром [E006b](E006-ukidim-unit-matching-eval.md): `pdf_with_text_layer=tabby` и те же scalar-параметры, что на commit `b5a71f4`. Относительно **текущего** дефолта кода (`auto_tabby` + `each_page_textual_layer_detection=True`) это откат к параметрам ориентира — не смена reader’а относительно E006b. Остальная LLM-цепочка (grouping / rerank / extraction) и модели — как в E006b / E003.

В ходе реализации HTML-цепочки всплыли **сопутствующие дефекты/ограничения** (не часть исходной «только формат»-гипотезы). Они вошли в тот же прогон; при анализе метрик и ошибок их нужно отделять от чистого эффекта HTML:

1. **Потеря таблиц на линии с несколькими table-аннотациями** (OCR post-process). При split `rule_part` дефолтный `_select_annotations` пересобирал `TableAnnotation` / `AttachAnnotation` в generic `Annotation` (`is_mergeable=True`); `AnnotationMerger` оставлял только один overlapping `name="table"` span → часть таблиц исчезала из дерева/placeholder’ов. Исправление: сохранять concrete `TableAnnotation` / `AttachAnnotation` при нарезке сегмента. Это может поднять recall табличного контекста **независимо** от pipe→HTML.
2. **Oversized table atoms / mid-cut seams** (chunk + merge). Исходный план: rowspan-safe split + **fail-fast**, если закрывающий атом не влезает в `max_chunk_tokens`. На реальных УКДИМ-таблицах (в т.ч. «титульные» / одна жирная ячейка) fail ломал прогон. Заменено на каскад **row → mid-span → mid-cell → mid-cols** с `seam_to_next` в metadata и seam-aware стыковкой соседних `table_chunk_index` в merge (без смены retrieval/expansion); для oversized header-row — demotion в data под пустым synthetic header, затем mid-cell / mid-cols. Fail остаётся только если одна ячейка-обёртка всё ещё не укладывается. На НСИ всплыл edge case: `empty_wrap == max_chunk_tokens` (нет бюджета даже на 1 символ longest cell) — mid-cell не уходил в mid-cols и падал; исправлено fallthrough в mid-cols.

### Сверка OCR params (MLflow + git)

Extraction-runs E003 (`1202f168e07141b5bded7aba8829e7c1`) и E006b (`f6591fabe01d4fa1bfafe66419c05ffd`) **не логируют** dedoc-скаляры в MLflow (только chunking/merge/LLM params). Источник истины для OCR:

1. **Git на commit E003** (`b5a71f4`, tag `mlflow.source.git.commit` у run `1202f168…`): в `converter.py` явно заданы скаляры ниже; `each_page_textual_layer_detection` **не передавался** → дефолт dedoc `false`.
2. **MLflow experiment `2`** (document-parsing), run с тем же reader mode `tabby`: `228e6364a091441b9c2a1d926d15ff09` — подтверждает тот же набор logged `dedoc.*` **без** `dedoc.each_page_textual_layer_detection`.

| Параметр | Значение для E007 (как E003) | Источник |
| -------- | ---------------------------- | -------- |
| `pdf_with_text_layer` | `tabby` | git `b5a71f4`; MLflow `228e6364…` |
| `each_page_textual_layer_detection` | **не задавать** (dedoc default `false`) | отсутствует в git E003 и в params `228e6364…` |
| `document_type` | `other` | git / MLflow |
| `structure_type` | `tree` | git / MLflow |
| `need_pdf_table_analysis` | `True` | git / MLflow |
| `need_gost_frame_analysis` | `True` | git / MLflow |
| `need_header_footer_analysis` | `True` | git / MLflow |
| `with_attachments` | `True` | git / MLflow |

Текущий код-дефолт для сравнения: `auto_tabby` + `each_page_textual_layer_detection=True` (document-parsing E006-B `c9758f22…`) — **не** использовать в этом прогоне.

### Что меняется

| Компонент | Было (E006b / E003) | Стало |
| --------- | ------------------- | ----- |
| Сериализация таблиц | pipe-markdown из cell grid | HTML (`<table>` / `<tr>` / `<td>` с `rowspan`/`colspan`) |
| Якорь таблицы в structure | `<table uid>` | `<table_ref uid="…"/>` (self-closing; без конфликта с реальным `<table>`) |
| OCR | `tabby` + скаляры выше | **те же** OCR-параметры; не брать текущий код-дефолт `auto_tabby` / `each_page=true` |
| Индекс table-чанков | текст pipe-таблицы | только тексты ячеек по порядку (без тегов и span-атрибутов) |
| Placeholder в structure при embedding | вырезается | без изменений (вырезается целиком) |
| Split большой таблицы | pipe-эвристики (header-dedup / gap) | HTML: rowspan-safe по `<tr>` → mid-span / mid-cell / mid-cols + `seam_to_next`; header demotion для oversized row-0; fail только если одна ячейка-обёртка не влезает |
| Merge sidecar → structure | подстановка pipe + header-dedup | подстановка HTML; seam-aware стыковка соседних сплитов (`row`/`span`/`cell`/`cols`); между кластерами — HTML gap-маркер |
| OCR: multi-table на одной линии | дефолт dedoc → merger ронял лишние table spans | concrete `TableAnnotation`/`AttachAnnotation` сохраняются при split сегмента |
| Промпты / `raw_quote` | под pipe | инструкции под HTML; quote может включать теги, если охватывает >1 ячейки; одна ячейка — достаточно текста ячейки |

### Scope и порядок оценки

1. **УКДИМ** (`bak`, `heat_exchanger`, `strainer`) — полный перегон OCR (`tabby`, параметры как E003) → formatting → chunk → vectorize → merge → extract → eval.
2. Comparator на УКДИМ: [E006b](E006-ukidim-unit-matching-eval.md) (`f6591fabe01d4fa1bfafe66419c05ffd`, `accuracy` 70.32%) — тот же режим eval: **unit matching + normalize + LLM unit judge**.
3. Затем **processed НСИ** — прогон + метрики; ориентир [E005](E005-nsi-processed-dense-grouping.md) (value-only; unit matching на НСИ не обязателен).

Один headline-прогон на УКДИМ: `tabby` + HTML vs E006b (`tabby` + pipe). Основная ось — **формат таблиц**; OCR reader относительно ориентира не меняется. Сопутствующие confounds (multi-table annotation fix, mid-cut seams) — учитывать при интерпретации, не смешивать с «чистым» HTML-эффектом.

### Вне scope

- document-parsing benchmark (TEDS и т.п.) и VLM как источник таблиц — после успешного extraction eval;
- тюнинг chunk/merge char budgets под HTML token inflation;
- multipage table merge / сегментация таблиц внутри dedoc (HTML лишь честнее рисует уже полученный grid);
- смена моделей grouping/rerank/extraction;
- переписывание eval matching (кроме уже выбранного режима E006b).

HTML становится **единственным** table format в extraction chain (жёсткая замена; реализация в отдельной ветке).

## 2. Expected effect / hypothesis

**H1 — рост или плато `accuracy` на УКДИМ относительно E006b за счёт таблиц со spans.** HTML сохраняет `rowspan`/`colspan`, которые pipe-markdown искажает или теряет. На слотах, где GT лежит в merged-ячейках или в структуре «атрибут / значение через span», ожидается меньше промахов retrieval→extraction → рост `TP` / снижение `FN`/`FP_2` на table-heavy slice. Aggregate `accuracy` может вырасти умеренно; доминирующий драйвер — не все слоты, а табличный поднабор.

**H2 — основной эффект — формат, не reader.** Относительно E006b OCR reader тот же (`tabby`); confound «auto_tabby→tabby» для УКДИМ **не применим**. Риск остаточного confound — если при перегоне случайно подтянуть текущий код-дефолт (`auto_tabby` / `each_page`) или если re-OCR даст иной grid при тех же параметрах (недетерминизм / версии dedoc). При интерпретации отдельно смотреть error analysis на «сложные / merged ячейки» vs простые таблицы.

**H3 — индекс без тегов не ломает retrieval.** Embedding по cell text (без HTML) должен сохранить или улучшить lexical/dense match к GT-терминам относительно pipe; риск — потеря «структурных» сигналов (заголовки рядов), если они были полезны в pipe. Ожидание: нейтрально или слегка лучше на term match; регрессии retrieval из‑за сырых тегов быть не должно.

**H4 — mid-cut seams вместо fail-fast: прогон не рвётся на oversized atoms, но появляется confound retrieval/merge.** Каскад row/span/cell позволяет пройти документы с «толстыми» ячейками; при полной склейке соседних сплитов контекст LLM близок к исходному HTML. Риск регрессии: если expansion не подтянул соседа — в контексте остаётся обрывок ячейки/`span`-хвост без полного rowspan-смысла. В error analysis отдельно смотреть mid-cell / mid-span фрагменты vs целиком уложившиеся таблицы. Fail-fast почти не ожидается; появление fail — сигнал крайнего overhead (header+обёртка), не «просто большой rowspan-атом».

**H5 — фикс потери table-аннотаций может дать часть прироста вне HTML.** Документы, где на одной `rule_part`-линии было несколько таблиц, раньше теряли все кроме одной. Прирост TP / снижение FN на таких слотах нельзя автоматически списывать на HTML spans — нужна сверка с «пропавшими» uid / placeholder’ами относительно pipe-ориентира.

**H6 — НСИ: ориентир E005, не E006b.** На processed НСИ сравниваем с value-only E005; эффект HTML может быть слабее или маскироваться OCR/attachment-проблемами (см. E005 §5). Цель — зафиксировать метрики и не ждать обязательного паритета с УКДИМ-дельтой.

**Критерий принятия:** УКДИМ full extract + unit-matching eval как E006b; интерпретация vs E006b с учётом confounds (multi-table OCR fix, mid-cut seams); прогон НСИ; error analysis на slice сложных/merged ячеек **и** на mid-cut / multi-table документы; offline step tests на serialize / chunk / merge / index-prepare зелёные.

## 3. Runs and metrics

| Подход / вариант | MLflow run_id | Ключевое отличие | Релевантные метрики | Примечания |
| ---------------- | ------------- | ---------------- | ------------------- | ---------- |
| E006b (comparator УКДИМ) | `f6591fabe01d4fa1bfafe66419c05ffd` | pipe-markdown + `tabby`; unit matching + normalize + LLM unit judge | `accuracy` **70.32%**; `count` 6010; TP 1453 / TN 2773 / FP₁ 604 / FP₂ 363 / FN 817; `errors` 8 | run name `ukidim-unit-matching-eval-fixed`, GT digest `330b5a1a` |
| E007 УКДИМ HTML | `fa2c5a1754cc4ad79ad2e9afebf98059` | HTML tables + `tabby` (OCR как E003); тот же eval-режим, что E006b | `accuracy` **68.79%**; `count` 6010; TP 1407 / TN 2727 / FP₁ 650 / FP₂ 354 / FN 872; `hc_accuracy` 74.48%; `lc_accuracy` 64.89%; `errors` 59 | run name `e007-ukidim-html-tables`, commit `97c12e94`, GT digest `330b5a1a`; string judge 181 / unit judge 19 |
| E005 (comparator НСИ) | `486cfa11a5bb4104ba7332ed8f6ee329` | pipe + dense grouping; value-only | `accuracy` **61.79%**; `count` 2146; TP 169 / TN 1157 / FP₁ 282 / FP₂ 144 / FN 394; `errors` 34 | run name `new-nsi-dataset-on-baseline`, GT digest `2aeac57a` |
| E007 НСИ HTML (загрязнённый) | `79928720ba97439b8b0c3729735a4767` | HTML + `tabby`; value-only | `accuracy` 65.24%; TP 53 / FN 610; `errors` **1353** | **отбросить**: ~1147 attrs `Connection error.` после обрыва VPN |
| E007 НСИ HTML (чистый re-extract) | `6a8395a128284a1abc22336dc7a4c12f` | HTML + `tabby`; value-only; полный re-extract 41/41 без connection errors | `accuracy` **61.51%**; `count` 2146; TP 168 / TN 1152 / FP₁ 287 / FP₂ 144 / FN 395; `hc_accuracy` 72.74%; `lc_accuracy` 48.76%; `errors` 38 | run name `e007-nsi-html-tables-reextract`, GT digest `2aeac57a`; `conn_rows` = 0 |

Дельты УКДИМ (E007 − E006b), формула: разность скаляров MLflow:

- `accuracy`: 68.79 − 70.32 = **−1.53 pp**
- TP: 1407 − 1453 = **−46**; FN: 872 − 817 = **+55**; FP₁: 650 − 604 = **+46**; FP₂: 354 − 363 = **−9**; TN: 2727 − 2773 = **−46**
- `errors`: 59 − 8 = **+51**

Дельты НСИ (чистый E007 − E005):

- `accuracy`: 61.51 − 61.79 = **−0.28 pp**
- TP: 168 − 169 = **−1**; FN: 395 − 394 = **+1**; FP₁: 287 − 282 = **+5**; FP₂: 144 − 144 = **0**; TN: 1152 − 1157 = **−5**
- `errors`: 38 − 34 = **+4**

## 4. Interpretation

**УКДИМ.** Headline `accuracy` слегка ниже E006b (−1.53 pp) при том же `count` и том же unit-matching eval. Сдвиг label-ов не выглядит как «чистый выигрыш spans»: net −46 TP и +55 FN при росте FP₁. Это **не подтверждает** H1 (рост/плато за счёт merged-ячеек) на aggregate уровне — скорее умеренная регрессия. Причины на уровне метрик неразличимы: возможны confounds из подхода (multi-table OCR fix, mid-cut seams, re-OCR grid drift) и обычная LLM-вариативность; нужен error analysis по переходам TP→FN / FN→TP.

HC/LC: `hc_accuracy` почти на уровне E006b (74.48% vs 74.73%), `lc_accuracy` ниже (64.89% vs 67.33%) — ухудшение сильнее на low-confidence слотах.

**НСИ (чистый re-extract).** Headline почти совпал с E005: **61.51% vs 61.79% (−0.28 pp)**; TP/FN отличаются на ±1. Это **плато** относительно value-only ориентира (H6), без заметного HTML-выигрыша и без крупной регрессии. Первый загрязнённый eval (`79928720…`) из интерпретации исключён.

**Статус интерпретации.** УКДИМ: небольшая регрессия vs E006b (−1.53 pp), H1 на aggregate не подтверждён. НСИ: нейтрально vs E005. HTML как primary win не выглядит; mid-cut / multi-table OCR fixes остаются полезными побочными артефактами прогона.

## 5. Error analysis

Источник: `rows.jsonl` E007 vs E006b (УКДИМ) и E007 vs E005 (НСИ) + текущие `context_rebuild/output` / `extraction/output` (HTML-прогон). УКДИМ: 6010 строк / 4410 уникальных `(eos_id, attr_id)` — дубли раздувают MLflow `errors` (59 vs 30 уникальных). НСИ: 2146 / 1922 уникальных (errors 38 vs 26). Ниже уникальные слоты, где важно, и row-level там, где совпадает с метриками `count`/`accuracy`.

### УКДИМ: рост `errors` — не шум, но и не весь −1.53 pp

E006b: 8 row-level / 8 уникальных, все `structured output parsing returned None`. E007: 59 / **30** уникальных; пересечение с E006b **пустое** (старые ошибки ушли, пришёл новый набор).

| Тип (уникальные слоты) | N | Что происходит |
| ---------------------- | - | -------------- |
| `structured output parsing returned None` | 20 | 4 группы по 5 атрибутов целиком → pred null |
| `unit is required when value is set` | 7 | новое относительно E006b: value без unit → validation fail |
| `Request timed out.` | 3 | одна группа на одном eos |

Все 30 ошибочных слотов сидят в extraction-группах с **HTML-таблицами** в контексте. Медиана размера этих failed-групп ~14.3k символов (vs ~9.8k по всем группам прогона); timeout-группа — 17 `<table>` / ~15k символов. Parse/timeout бьют **группой**: один сбой LLM на oversized HTML-контексте обнуляет все attrs группы (отсюда кластеры по 5 FN/TN).

Вклад в headline (row-level, как MLflow `accuracy`): из net **−92** к числителю `(TP+TN)` слоты с `extraction_error` в E007 дают **−22** (~**−0.37 pp**), остальные **−75** (~**−1.25 pp**). На уникальных: errors **−10**, non-error **−49**. Итого: рост errors **реально тянет метрику вниз** (часто TP→FN: 14 уникальных), но **большинство** регрессии — вне technical errors. Списывать −1.53 pp на «шум errors» нельзя; игнорировать errors тоже нельзя — это побочный эффект HTML-раздувания контекста (parse/timeout), плюс отдельный unit-validation режим.

### УКДИМ: где метрики из‑за errors, где нет

На слотах E007-error переходы почти только в пустой pred: TP→FN (14), FP₂→FN (2), FP₁→TN (4), остальное FN/TN без смены correctness. Это **не** «модель хуже прочитала ячейку», а **срыв structured output / timeout / schema** на группе.

Очищенный от errors срез (уникальные, оба run без `extraction_error`) — основные смены label:

| Было → стало | N |
| ------------ | - |
| TN → FP₁ | 82 |
| TP → FN | 55 |
| FP₁ → TN | 51 |
| FP₂ → TP | 32 |
| FN → TP | 31 |
| FP₂ → FN | 28 |
| TP → FP₂ | 26 |
| FN → FP₂ | 25 |

Сырая таблица переходов из §5 раньше (с errors) **смешивала** технический обвал групп с качеством извлечения; для вывода про HTML её использовать нельзя. Даже очищенная таблица сама по себе ещё не говорит «виноват формат таблиц» — нужен срез по табличному происхождению слота (ниже).

### УКДИМ: перетекание меток и таблицы (как проверяли)

Эвристика «слот был табличным в E006b»: в E006b `raw_quote` похож на pipe-строку (`| … |`). HTML в quote E007 почти не встречается (модель чаще цитирует текст ячейки без тегов) — поэтому смотреть «есть ли `<td>` в quote» почти бесполезно. Для регрессий TP→FN дополнительно: есть ли GT во **входном** HTML-контексте группы (`context_rebuild`).

**Слоты с pipe-quote в E006b** (434 уникальных): net correctness **+5** (не регрессия). Среди смен: TP→FN 10, TP→FP₂ 6, FP₂→TP 5, FP₁→TN 16, FP₂→FN 7. То есть на явно «раньше из таблицы» срезе HTML **не объясняет** aggregate −1.5 pp — там скорее небольшой плюс/перетасовка.

Из 10 non-error TP→FN с pipe-quote у E006b: у **9/10** GT всё ещё находится в HTML-контексте группы (exact/`comma`), pred пустой. Это похоже на **промах чтения HTML-таблицы** (значение доставлено, extraction не вытащил), а не на retrieval miss. Пример противоположного полюса TP→FP₂: температуры теплоносителя на eos `2370076919022147` — E006b цитировал нужную pipe-строку, E007 цитирует соседний `<tr>` / другую колонку → перепутанные 33/40/60/90. Есть и обратные FP₂→TP по объёму/вместимости на табличных слотах.

**Остальные non-error слоты** (без pipe/html-сигнала в quote): net correctness **−54** — здесь основной минус. TP→FN (45): часто пустой pred; у части GT нет в контексте группы (retrieval/grouping), у части GT есть при HTML в группе, но quote E006b был не pipe (проза / составные строки вроде `88,9х4`) — однозначно на «pipe→HTML» не повесить. TN→FP₁ остаётся крупным churn вне табличной эвристики.

**Уточнение к §4:** умеренная регрессия УКДИМ — **смесь** (1) HTML-связанных technical errors на толстых table-группах (~¼ row-level дельты), (2) точечных HTML-read/column-slip на бывших pipe-слотах (важны для H1, но net на этом срезе не отрицательный), (3) более широкого non-table churn (пустые pred / FP₁), который доминирует в −1.25 pp вне errors. Causal claim «HTML spans помог» по-прежнему не подтверждён; claim «регрессия = HTML испортил таблицы» тоже слишком груб.

### НСИ: рост `errors` — слабый и не тянет −0.28 pp вниз

E005: 34 row-level / **24** уникальных (`structured output parsing returned None` 22, `Error code: 500` 2). E007: 38 / **26**; пересечение с E005 **13** (часть старых ошибок осталась, плюс новый набор).

| Тип (уникальные слоты) | N | Что происходит |
| ---------------------- | - | -------------- |
| `structured output parsing returned None` | 20 | кластеры на `2202460` / `2220650` / `2109335` → pred null |
| `unit is required when value is set` | 3 | новое относительно E005: value без unit → validation fail |
| `Error code: 500` | 3 | LLM 500 (не HTML-специфика) |

**25/26** ошибочных слотов сидят в extraction-группах с **HTML-таблицами** в контексте (исключение — один 500 без `<table>`). Медиана размера этих failed-групп ~11.8k символов (vs ~8.2k по всем группам прогона); parse-группы ещё крупнее (~13.3k). Как на УКДИМ: parse/unit бьют **группой** на толстом HTML-контексте.

Вклад в headline (row-level): из net **−6** к числителю `(TP+TN)` слоты с `extraction_error` в E007 дают **+5** (~**+0.23 pp**), non-error **−11** (~**−0.51 pp**). На уникальных: errors **+4**, non-error **−8**. Итого: рост errors на НСИ **не объясняет** −0.28 pp — наоборот, обнуление pred на error-слотах чаще снимает `FP₁` (`FP₁→TN` 4), чем роняет TP. Регрессия целиком в non-error churn. Загрязнённый run `79928720…` (VPN) в разбор не входит.

### НСИ: где метрики из‑за errors, где нет

На слотах E007-error переходы: `TN→TN` 16, `FN→FN` 5, `FP₁→TN` 4, `FP₂→FN` 1 — почти нет TP→FN. Это **технический срыв** (parse / unit / 500), не «хуже прочитали ячейку»; на accuracy он даже слегка плюсует за счёт FP₁→TN.

Очищенный от errors срез (уникальные, оба run без `extraction_error`, n=1885) — основные смены label:

| Было → стало | N |
| ------------ | - |
| TN → FP₁ | 61 |
| FP₁ → TN | 55 |
| FN → FP₂ | 23 |
| FP₂ → FN | 21 |
| FP₂ → TP | 11 |
| TP → FN | 10 |
| TP → FP₂ | 9 |
| FN → TP | 7 |

Net correctness на clean-срезе **−7**. Картина churn похожа на УКДИМ (крупный TN↔FP₁), но амплитуда мала относительно объёма; сырая таблица с errors здесь тоже смешивала бы технический обвал с качеством — для вывода про HTML использовать нельзя.

### НСИ: перетекание меток и таблицы (те же проверки, что на УКДИМ)

Эвристика «слот был табличным в E005»: в E005 `raw_quote` похож на pipe-строку (`| … |`). HTML в quote E007 редок (8 уникальных слотов с `<td>`/`<tr>`); модель чаще цитирует текст ячейки. Для регрессий TP→FN дополнительно: есть ли GT во **входном** HTML-контексте группы (`context_rebuild`).

**Слоты с pipe-quote в E005** (24 уникальных clean): net correctness **+3** (не регрессия). Среди смен: FP₂→FN 2, FP₁→TN 2, FP₂→TP 1; **TP→FN = 0**. На явно «раньше из таблицы» срезе HTML **не объясняет** −0.28 pp — там небольшой плюс/перетасовка. Пример выигрыша: `(2211836, attr7738)` FP₂→TP, quote E007 — `<td>Сталь 20</td>` (ячейка прочитана).

**Остальные non-error слоты** (без pipe в quote E005): net correctness **−10** — здесь весь минус. TP→FN (10): у всех pred пустой; у **7/10** GT всё ещё находится в контексте группы (exact/`comma`), у **8/10** в группе есть HTML-таблица. Это ближе к **промаху чтения / пустому pred при доставленном контексте**, чем к retrieval miss; однозначно на «pipe→HTML» не повесить — pipe-quote у этих TP→FN не было. TN→FP₁ остаётся основным churn вне табличной эвристики.

HC/LC (row-level): `hc_accuracy` почти как E005 (72.74% vs 72.59%); `lc_accuracy` чуть ниже (47.57% vs 48.38%) — слабый LC-сдвиг, без аналога укдимовского −2.4 pp на LC.

**Уточнение к §4:** плато НСИ (−0.28 pp) после тех же разрезов, что на УКДИМ, выглядит устойчивым: (1) HTML-связанные technical errors на толстых table-группах есть, но **не тянут** aggregate вниз (даже слегка плюсуют через FP₁→TN); (2) table/pipe-срез маленький и с net **+**; (3) крошечный минус — non-table churn (пустые pred / TN↔FP₁), сопоставимый с LLM-шумом на 2146 слотах. Causal claim «HTML помог НСИ» не подтверждён; claim «HTML испортил НСИ» тоже нет — решение «нейтрально vs E005» из §4 error analysis не меняет.

## 6. Conclusion

H1 как **мгновенный** рост `accuracy` за счёт spans **не подтвердился**: УКДИМ −1.53 pp vs E006b, НСИ −0.28 pp vs E005 (плато). Table/pipe-срезы на обоих датасетах не показывают net-регрессии от формата; основной минус УКДИМ — смесь oversized HTML-групп (parse/timeout ~¼ дельты) и non-table churn. При этом прогон показал, что HTML + mid-cut seams + multi-table OCR fix — **рабочая цепочка** на реальных толстых таблицах, а не только «другая сериализация».

Ограничение эксперимента важно: budgets (`max_chunk_tokens` и смежные лимиты) **не перенастраивались** под HTML token inflation (это было вне scope). Гипотезы на следующий круг: (1) поднять chunk/merge budgets и/или сузить expansion, чтобы реже собирать 12–15k+ HTML-группы → меньше parse/timeout; (2) на новых НСИ с более сложными таблицами выигрыш spans проявится сильнее, чем на текущих ориентирах; (3) VLM→HTML как канонический table target может стыковаться с этой цепочкой чище, чем VLM→pipe. Отдельно: рост `errors` на УКДИМ (8→59) **коррелирует** с толстыми HTML-группами, но это ещё не доказанная причинность — часть сбоев может быть от LLM/infra (timeout, 500, schema `unit required`), другой grouping/context или недетерминизма прогона, а не от самого pipe→HTML. Разобрать errors точечно (какие группы, какие промпты/размеры, воспроизводится ли на pipe при том же контексте) нужно до сильного вывода «HTML раздул и сломал structured output». Итого: quality-win «здесь и сейчас» нет, но формат как **инфраструктурный задел** под сложные таблицы / VLM экспериментом не опровергнут.

## 7. Decision

**Оставить HTML** как рабочий table format в extraction chain (не откатывать на pipe ради −1.5 pp), вместе с mid-cut seams и multi-table OCR fix. **Не считать** E007 доказательством quality-uplift — следующий шаг не «stop HTML», а: (1) точечный разбор `errors` на УКДИМ (не списывать автоматически на HTML), (2) подкрутка token/chunk budgets под HTML + re-eval при необходимости; параллельно держать HTML как целевой формат для VLM-таблиц.
