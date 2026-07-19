# E007 - VLM page→Markdown baseline (self-hosted Qwen)

## 1. Approach

На полном `ocr_benchmark` (24 кейса, тот же scoring contract) — **тонкий
self-hosted VLM reader** без чужой OCR-оболочки: page image → vision → Markdown
→ склейка в pred. Ось — модель; схема вызова общая.

| Вариант | Модель / отличие |
| --- | --- |
| A | `Qwen/Qwen3.6-35B-A3B-FP8`, `enable_thinking: false` |
| B | `Qwen/Qwen3.6-27B-FP8`, `enable_thinking: false` |
| C | та же 35B, что A, но `enable_thinking: true` (trade-off скорость/качество) |

```mermaid
flowchart LR
  PDF[PDF кейса] --> R["рендер PNG<br/>DPI"]
  V --> J["склейка страниц<br/>без cross-page контекста"]
  R --> V["VLM / страница<br/>prompt · pipe-MD"]
  J --> P[pred Markdown]
  P --> S[scoring vs GT]
```

Рычаги качества в этой схеме: **DPI** (читаемость vs OOM), **модель**,
**prompt** (pipe-таблицы, reading order, пробелы; v2 — игнор ГОСТ-рамки/штампа,
рукописи, текста внутри рисунков), **page-only** (нет контекста соседних страниц /
across-pages таблиц). Без routing — VLM на всех кейсах ради срезов. Comparator:
dedoc `auto_tabby` + `each_page` (E006 digest).

## 2. Expected effect / hypothesis

**Гипотеза:** на полном корпусе VLM не обязан выигрывать macro у dedoc, но на
уже известных дырах классических parser’ов даст локальный выигрыш, а на
born-digital с хорошим text layer — риск регрессии или паритета.

| Ожидание | Механизм | Критерий / якорь |
| --- | --- | --- |
| Mixed: меньше space-collapse / лучше OCR-часть | Vision читает страницу целиком, не Tabby/txtlayer path | `tu-mixed-text-scan-…`: `token_f1` ≫ ~0.26 у dedoc |
| Catalog: появляется таблица | Multi-column layout → pipe table в Markdown | `catalog-belimo`: `teds` > 0, pred tables ≈ GT |
| Scan / sparse / broken layer | Сильнее Tesseract-ветки dedoc на трудных листах | рост `token_f1`/`teds` на соответствующих `doc_type` / tags |
| Born-digital guardrail | Лишний OCR-like путь портит уже чистый слой | slice `born_digital_good` / `spec-kur0130`: без существенной регрессии vs dedoc |

Вариант A (35B MoE) vs B (27B): ожидается близкий качественный профиль с
возможным преимуществом A на сложных таблицах/layout; если дельта мала —
для routing достаточно более дешёвой B.

Вариант C vs A: thinking может чуть подтянуть сложный layout / снизить
катастрофические срывы, ценой latency и токенов на страницу. Критерий
adopt для gate: заметный выигрыш на hard-кейсах без неприемлемого
замедления относительно A (иначе default остаётся thinking off).

**Adopt-сигнал (для дальнейшей работы, не для немедленной замены pipeline):**
есть устойчивые срезы, где VLM заметно лучше dedoc при приемлемой регрессии
guardrail — тогда имеет смысл проектировать page/doc gate. Если VLM везде
хуже или выигрыш только ценой born-digital — reject тонкого VLM-reader как
универсального пути; ceiling через чужие VLM-оболочки — отдельный эксперимент.

## 3. Runs and metrics

Все run’ы на digest
`a481aa528c94abc34e7298d0b1e26243bbc97600ff7cf3782c6e267caef6750c`,
`case_count=24`. VLM: `eval_mode=reuse`, `prompt_version=e007-page-md-v2`,
`dpi=96`. Snapshots: `vlm_bench_{35b|27b}-dpi96-e007-page-md-v2`,
`vlm_bench_35b-dpi96-e007-page-md-v2-thinking`. Comparator — E006-B.

| Вариант | MLflow run_id | Key difference | `cer` | `token_f1` | `teds` | `teds_s` | `ast` | `table_parse_error_count` | Notes |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| A 35B | `a985e9052fd74f6bb86ff4bb81a16034` | thinking off | 0.844944 | 0.882720 | 0.637929 | 0.668315 | 0.597393 | 6 | `E007-vlm-35b-dpi96-v2` |
| B 27B | `abe17b7e29df4e69b2eb72f9cf80647b` | 27B, thinking off | 0.842805 | 0.887527 | 0.611148 | 0.633080 | 0.573041 | 5 | `E007-vlm-27b-dpi96-v2` |
| C 35B thinking | `c185a000b6864bce9817c58e054a863a` | 35B, `enable_thinking: true` | 0.855260 | 0.892131 | 0.667791 | 0.726672 | 0.707421 | 2 | `E007-vlm-35b-dpi96-v2-thinking` |
| dedoc E006-B | `c9758f22ded345e69e8bcb168fba4b52` | `auto_tabby` + each_page | 0.711665 | 0.812833 | 0.729071 | 0.797980 | 0.614975 | — | comparator |

Δ macro качества:

| | `token_f1` | `teds` | `cer` | `ast` |
| --- | ---: | ---: | ---: | ---: |
| A − dedoc | +0.0699 | −0.0911 | +0.1333 | −0.0176 |
| C − A | +0.0094 | +0.0299 | +0.0103 | +0.1100 |
| C − dedoc | +0.0793 | −0.0613 | +0.1436 | +0.0924 |

Latency (из lab `intermediates/ocr.json` → `pages[].elapsed_seconds`; в MLflow
не залогировано; 32 страницы):

| | sum s | mean s/page | median s/page |
| --- | ---: | ---: | ---: |
| A | 497.3 | 15.54 | 6.37 |
| C | 747.3 | 23.35 | 18.66 |
| C / A | ×1.50 | ×1.50 | ×2.93 |
| C − A | +250.0 s (+50%) | +7.81 | +12.29 |

У A два outlier-page ~134–137 s (`standard-gost…`, `extract-completeness…`);
без страниц >100 s mean A ≈ 7.5 s/page — ближе к median. У C таких
outliers нет (max ≈ 86 s на `appendix-tech`).

Якоря C vs A (`cases.jsonl`):

| Кейс | | `token_f1` | `teds` | `ast` | tables | case time s |
| --- | --- | ---: | ---: | ---: | --- | ---: |
| `tu-mixed-text-scan…` | A | 0.909 | 0 | 0.396 | 4/0 | 12.9 |
| | C | 0.987 | 1.000 | 0.905 | 0/0 | 43.5 |
| `catalog-belimo-p020` | A | 0.869 | 0.735 | 0.651 | 1/1 | 10.3 |
| | C | 0.884 | 0.012 | 0.723 | 2/1 | 24.6 |
| `spec-kur0130…` | A | 0.964 | 0 | 0.013 | 0/1 | 31.1 |
| | C | 0.961 | 0.115 | 0.834 | 3/1 | 91.7 |
| `standard-gost…` | A | 0.108 | 0 | 0.005 | 0/1 | 134.8 |
| | C | 0.423 | 0.260 | 0.868 | 1/1 | 62.6 |

## 4. Interpretation

Гипотеза C vs A: thinking даёт локальный выигрыш на hard layout ценой
latency. По macro это **частично подтверждается**: `token_f1`/`teds`/`cer`
чуть выше A (+0.01 / +0.03 / +0.01), `ast` заметно выше (+0.11),
`table_parse_error_count` 6→2. Одновременно latency: **+50%** суммарного
page-time, median **~×3** — критерий «без неприемлемого замедления»
на median **не выглядит выполненным**, даже если wall-sum лишь ×1.5 из‑за
двух медленных outlier’ов у A.

На якорях картина неоднородная:
- **mixed:** C убирает ложные table blocks (`4/0`→`0/0`, `teds` 0→1 по
  соглашению пустых таблиц) и поднимает `token_f1`/`ast` — согласуется с
  ожиданием «лучше на сложном layout», но за ~×3.4 времени кейса.
- **gost:** сильный отскок `token_f1` (0.11→0.42) и валидная таблица;
  время даже ниже A (у A был похож на hang/loop). Здесь thinking
  окупается.
- **kur0130:** как у B — pipes/page-split (`teds≈0.12`, `ast` восстановлен);
  текст почти как A, время ~×3. Across-pages page-only лимит не снят.
- **catalog:** `token_f1` чуть выше, но `teds` обваливается (0.74→0.01) при
  `pred_count=2` — метрический штраф за лишний table block / порядок
  pairing; без разбора pred нельзя сказать, что ТД «пропали».

Относительно dedoc C всё ещё выше по тексту/`ast`, ниже по `teds`
(разрыв уже меньше, чем у A). A vs B на macro по-прежнему близки; для
сравнения thinking релевантен только C−A на одной 35B.

Статус: quality-выигрыш C vs A **есть, но скромный на macro** и **дорогой
по median latency**; часть case-level сдвигов (mixed stamps, gost loop,
catalog `teds`) требует §5. Для adopt thinking как default gate метрик
latency недостаточно благоприятны без доказанного выигрыша на
extraction-критичных кейсах.

## 5. Error analysis

### C vs A (thinking) — что двигает метрики

**Цена времени.** На типичной странице C ~×3 медленнее (median 18.7 vs
6.4 s). Суммарно +250 s на 32 pages. Выигрыши качества точечные; для soft
gate это прямой удар по throughput.

**mixed — stamps подавлены.** A всё ещё клеил pipe-блоки штампа
(Изм./Подп.); C даёт чистый body без таблиц (`0/0`) → `teds=1` и выше
`token_f1`. Для экстракции это улучшение контекста (меньше шума), не
«появилась GT-таблица». Thinking здесь помогает следовать prompt v2.

**gost — меньше катастрофы.** A: loop (~462 одинаковых строк),
`token_f1≈0.11`, ~135 s. C: конечная pipe-таблица с числами,
`token_f1≈0.42`, ~63 s. Всё ещё слабо vs dedoc/полноты GT, но как
анти-режим «hang» thinking полезен. Gate на rotated dense всё равно
нужен.

**kur0130 — формат как у B, не «починка across-pages».** C снова даёт
page-split pipes (3/1, `teds≈0.12`) вместо flat A; ячейки читаемые, склейки
нет. +60 s на кейс без решения корневой проблемы — скорее аргумент за
page-window / dedoc на этом теге, чем за thinking default.

**catalog — `teds` врёт относительно пользы.** C ставит **две** pipe-таблицы
(схема/подписи + блок ТД); positional TEDS сравнивает первую с GT ТД →
~0.01, вторая штрафуется как лишняя. Сам KV ТД (напряжение, IP54, вес…)
на месте и для экстракции полезен. Не трактовать как отказ от VLM на
catalog; метрика здесь наказывает порядок/лишний block.

**Остальное кратко.** `table_parse_error` снят на kur0130 / gost /
appendix-params / completeness; остаются ragged `appendix-tech` и
`bilingual-kv` (контент KV у обоих вариантов всё ещё usable). Регрессии
C: `appendix-variants` `token_f1` −0.10; `handwritten` −0.07 — не
драматично для gate-решения.

### A/B vs dedoc (кратко; без повтора полного разбора)

Сигналы для роутера из сравнения с dedoc **держатся**: VLM лучше на
mixed / catalog / bilingual KV / части scan; не слать born-digital
across-pages и rotated dense без препроцесса. Thinking **не отменяет**
эти критерии: на mixed чуть чище chrome, на gost мягче fail, на catalog
метрический `teds` хуже при живом KV, across-pages не решён.

Если §4 казался однозначно «C лучше по качеству» — §5 уточняет: macro/`ast`
рост частично от mixed/gost/kur0130-формата; catalog `teds` — pairing
artifact; главный trade-off — **latency ×~3 на median**.

## 6. Conclusion

Тонкий page→Markdown VLM на полном бенче **не универсальная замена**
dedoc, но даёт устойчивые локальные выигрыши там, где классика ломает
контекст для экстракции: mixed/space-collapse, multi-column catalog,
битый bilingual KV, часть image-only scan. Macro `token_f1`/`cer` выше
dedoc, `teds` ниже — часть «табличных» штрафов при разборе pred
оказывается форматом/ложными штампами, а не пустыми ячейками.

A и B близки по качеству; дальше работаем с **35B (A)** как единственной
VLM-моделью ветки (throughput → мягче page-gate). Guardrail: не слать
в VLM born-digital across-pages с хорошим text layer и rotated dense
без препроцесса. Chrome (рамка/штамп/шапка) prompt’ом не закрыт —
нужен crop/препроцесс. Wide/A3 — кандидаты на стандартный tiling, не на
точечные кастыли.

До закрытия E007 **C измерен** (§3–§5): скромный quality-plus vs A при
median latency ~×3. Остальные идеи (HTML-таблицы, few-shot, SO,
multi-page) — см. §7.

## 7. Decision

**Сейчас в E007:** C прогнан (§3–§5). По метрикам thinking даёт небольшой
quality-plus (особенно `ast`, меньше ragged) ценой median ~×3 page-time —
для default gate скорее **thinking off (A)**; thinking как опция на
hard/rotated имеет смысл обсудить отдельно, не как default. Formal
decision — при желании через conclusion pass.

**После C / параллельно к gate (не полный «выбор модели» заново):**

1. **HTML-таблицы (привлекательно, узкий VLM-тест).** Downstream и
   chunking завязаны на Markdown-таблицах; полный прогон экстракции на
   HTML — большая отдельная задача. Сейчас достаточно VLM-среза: просить
   HTML-таблицы → для scoring канонизировать в pipe (как сейчас TEDS
   ест pipe→HTML). Цель — либо «добавить очков» идее (меньше ragged /
   лучше ячейки), либо отказаться при ухудшении качества или куче
   подводных камней адаптера. Не блокер дизайна gate.

2. **Few-shot / one-shot — отложить.** Для visual/VLM задач few-shot
   встречается (демо формата, иногда CoT-примеры), но на
   гетерогенных страницах дорог по контексту и плохо обобщается; то, что
   ломается у нас (штамп, rotate, wide), shot почти не чинит. Не full-bench.

3. **Structured output / раздельная структура+таблицы — не блокер
   gate.** Даже при Markdown-выходе дальше всё равно нужен разбор в
   дерево (body vs tables) под текущий chunking; MD→tree выглядит
   реалистично без обязательного JSON-schema с VLM. SO/dual-pass —
   архитектурный трек после/рядом с gate, не обязательный full-bench до
   него.

4. **Gate:** можно проектировать критерии по уже известным срезам
   (§5), не дожидаясь HTML/SO. Препроцесс (crop chrome, rotate, tiling
   policy) — бэклог VLM-пайплайна с точечными проверками, не новым
   «выбором модели на 24 кейсах».

5. **Multi-page / page-window (обсуждение, не текущий C).** Сейчас
   `unit_of_call=page`: модель не видит соседей — главный механизм
   провала `spec-kur0130` (таблица across pages). Имеет смысл позже
   проверить подачу **нескольких страниц в один вызов**, но по
   стандартному правилу, не «всем по N»:

   | Когда пачка / окно | Когда оставить 1 page |
   | --- | --- |
   | across-pages сигнал (продолжение таблицы, общий header, tag `table_across_pages`) | обычный single-page текст, sparse, catalog-лист |
   | короткий кейс целиком (2–3 стр.), если картинки влезают в контекст | dense A3 / wide — скорее tile **внутри** страницы |
   | скользящее окно `i` + `i±1` только если эвристика/gate сказала «таблица режется» | born-digital с хорошим text layer — multi-page VLM не нужен (dedoc) |

   Ограничения: больше PNG → latency/VRAM и риск truncate; нужен prompt
   на склейку одной логической таблицы. Для бенча — отдельный
   `unit_of_call` (иначе несравнимо с A/C). Follow-up после C: smoke на
   `kur0130` + 1–2 multi-page, не замена page-only baseline в том же
   run-id.
