(() => {
  const STATUS_LABEL = {
    draft: "Черновик",
    ready: "К обработке",
    processing: "В обработке",
    done: "Готово",
    error: "Ошибка",
  };

  const STATUS_ORDER = { draft: 0, ready: 1, processing: 2, done: 3, error: 4 };

  const PIPELINE = [
    { id: "validate", title: "Проверка комплекта", hint: "Файлы и метаданные записи МТР", seconds: 4 },
    { id: "ocr", title: "Чтение PDF", hint: "OCR и распознавание текста", seconds: 12 },
    { id: "normalize", title: "Нормализация текста", hint: "Очистка и унификация единиц", seconds: 5 },
    { id: "chunk", title: "Разбиение на фрагменты", hint: "Подготовка к поиску", seconds: 6 },
    { id: "index", title: "Индексация", hint: "Построение поискового индекса", seconds: 5 },
    { id: "retrieve", title: "Поиск фрагментов", hint: "Кандидаты по атрибутам класса", seconds: 8 },
    { id: "rerank", title: "Ранжирование", hint: "Отбор наиболее релевантных мест", seconds: 6 },
    { id: "extract", title: "Извлечение атрибутов", hint: "Значения и оценка уверенности", seconds: 10 },
    { id: "report", title: "Формирование карточки", hint: "Сборка результата для сверки", seconds: 4 },
  ];

  const STEP_MS = 850;

  const WIZARD = [
    { id: "kit", title: "Комплект документов" },
    { id: "run", title: "Извлечение" },
    { id: "review", title: "Сверка атрибутов" },
    { id: "export", title: "Выгрузка карточки" },
  ];

  const OBJECT_TYPES = [
    { code: "demo-motor", title: "Электродвигатели", demo: true },
    { code: "demo-pump", title: "Насосы центробежные", demo: true },
    { code: "demo-valve", title: "Арматура трубопроводная", demo: true },
  ];

  const CLASS_ATTRS = {
    "demo-motor": {
      order: [
        "attr_name",
        "attr_power",
        "attr_voltage",
        "attr_current",
        "attr_speed",
        "attr_efficiency",
        "attr_ip",
        "attr_mounting",
        "attr_insulation",
        "attr_weight",
        "attr_ambient_temp",
      ],
      attributes: [
        {
          attr_id: "attr_name",
          attr_name: "Наименование",
          attr_type: "string",
          units: null,
          allowed_values: null,
        },
        {
          attr_id: "attr_power",
          attr_name: "Номинальная мощность",
          attr_type: "number",
          units: ["кВт"],
          allowed_values: null,
        },
        {
          attr_id: "attr_voltage",
          attr_name: "Номинальное напряжение",
          attr_type: "number",
          units: ["В"],
          allowed_values: null,
        },
        {
          attr_id: "attr_current",
          attr_name: "Номинальный ток",
          attr_type: "number",
          units: ["А"],
          allowed_values: null,
        },
        {
          attr_id: "attr_speed",
          attr_name: "Частота вращения",
          attr_type: "number",
          units: ["об/мин", "мин⁻¹"],
          allowed_values: null,
        },
        {
          attr_id: "attr_efficiency",
          attr_name: "КПД",
          attr_type: "number",
          units: ["%"],
          allowed_values: null,
        },
        {
          attr_id: "attr_ip",
          attr_name: "Степень защиты",
          attr_type: "enum",
          units: null,
          allowed_values: ["IP20", "IP40", "IP54", "IP55", "IP65"],
        },
        {
          attr_id: "attr_mounting",
          attr_name: "Способ монтажа",
          attr_type: "enum",
          units: null,
          allowed_values: ["на лапах", "фланцевый", "комбинированный"],
        },
        {
          attr_id: "attr_insulation",
          attr_name: "Класс изоляции",
          attr_type: "enum",
          units: null,
          allowed_values: ["B", "F", "H"],
        },
        {
          attr_id: "attr_weight",
          attr_name: "Масса",
          attr_type: "number",
          units: ["кг"],
          allowed_values: null,
        },
        {
          attr_id: "attr_ambient_temp",
          attr_name: "Температура окружающей среды",
          attr_type: "range",
          units: ["°C"],
          allowed_values: null,
        },
      ],
    },
    "demo-pump": {
      order: [
        "attr_name",
        "attr_flow",
        "attr_head",
        "attr_power",
        "attr_voltage",
        "attr_speed",
        "attr_efficiency",
        "attr_ip",
        "attr_mounting",
        "attr_material",
        "attr_weight",
      ],
      attributes: [
        {
          attr_id: "attr_name",
          attr_name: "Наименование",
          attr_type: "string",
          units: null,
          allowed_values: null,
        },
        {
          attr_id: "attr_flow",
          attr_name: "Подача",
          attr_type: "number",
          units: ["м³/ч"],
          allowed_values: null,
        },
        {
          attr_id: "attr_head",
          attr_name: "Напор",
          attr_type: "number",
          units: ["м"],
          allowed_values: null,
        },
        {
          attr_id: "attr_power",
          attr_name: "Мощность",
          attr_type: "number",
          units: ["кВт"],
          allowed_values: null,
        },
        {
          attr_id: "attr_voltage",
          attr_name: "Напряжение",
          attr_type: "number",
          units: ["В"],
          allowed_values: null,
        },
        {
          attr_id: "attr_speed",
          attr_name: "Частота вращения",
          attr_type: "number",
          units: ["об/мин"],
          allowed_values: null,
        },
        {
          attr_id: "attr_efficiency",
          attr_name: "КПД",
          attr_type: "number",
          units: ["%"],
          allowed_values: null,
        },
        {
          attr_id: "attr_ip",
          attr_name: "Степень защиты",
          attr_type: "enum",
          units: null,
          allowed_values: ["IP54", "IP55", "IP65"],
        },
        {
          attr_id: "attr_mounting",
          attr_name: "Способ монтажа",
          attr_type: "enum",
          units: null,
          allowed_values: ["на раме", "на лапах", "на плите"],
        },
        {
          attr_id: "attr_material",
          attr_name: "Материал корпуса",
          attr_type: "enum",
          units: null,
          allowed_values: ["чугун", "сталь", "бронза"],
        },
        {
          attr_id: "attr_weight",
          attr_name: "Масса",
          attr_type: "number",
          units: ["кг"],
          allowed_values: null,
        },
      ],
    },
    "demo-valve": {
      order: [
        "attr_name",
        "attr_dn",
        "attr_pn",
        "attr_temp",
        "attr_length",
        "attr_seal",
        "attr_connection",
        "attr_drive",
        "attr_weight",
        "attr_zeta",
      ],
      attributes: [
        {
          attr_id: "attr_name",
          attr_name: "Наименование",
          attr_type: "string",
          units: null,
          allowed_values: null,
        },
        {
          attr_id: "attr_dn",
          attr_name: "Условный диаметр",
          attr_type: "number",
          units: ["мм"],
          allowed_values: null,
        },
        {
          attr_id: "attr_pn",
          attr_name: "Номинальное давление",
          attr_type: "number",
          units: ["МПа"],
          allowed_values: null,
        },
        {
          attr_id: "attr_temp",
          attr_name: "Рабочая температура",
          attr_type: "range",
          units: ["°C"],
          allowed_values: null,
        },
        {
          attr_id: "attr_length",
          attr_name: "Строительная длина",
          attr_type: "number",
          units: ["мм"],
          allowed_values: null,
        },
        {
          attr_id: "attr_seal",
          attr_name: "Класс герметичности",
          attr_type: "enum",
          units: null,
          allowed_values: ["класс A", "класс B", "класс C"],
        },
        {
          attr_id: "attr_connection",
          attr_name: "Присоединение",
          attr_type: "enum",
          units: null,
          allowed_values: ["межфланцевое", "фланцевое", "под приварку"],
        },
        {
          attr_id: "attr_drive",
          attr_name: "Привод",
          attr_type: "enum",
          units: null,
          allowed_values: ["рукоятка", "редуктор", "электропривод"],
        },
        {
          attr_id: "attr_weight",
          attr_name: "Масса",
          attr_type: "number",
          units: ["кг"],
          allowed_values: null,
        },
        {
          attr_id: "attr_zeta",
          attr_name: "Коэффициент сопротивления",
          attr_type: "number",
          units: null,
          allowed_values: null,
        },
      ],
    },
  };

  Object.keys(CLASS_ATTRS).forEach((code) => {
    CLASS_ATTRS[code].byId = Object.fromEntries(
      CLASS_ATTRS[code].attributes.map((a) => [a.attr_id, a]),
    );
  });

  /** Seed from research/datasets/demo (JMLC-05).
   *  documents[] order = source priority (index 0 = highest). */
  const SEED = {
    cards: [
      {
        id: "card-pump-001",
        name: "Насос центробежный 50 м³/ч",
        eos_id: "demo-item-pump-001",
        status: "done",
        created_at: "2026-07-16",
        objectTypeCode: "demo-pump",
        suggestedClass: "demo-pump",
        documents: [{ file_name: "TU-DEMO-PUMP-001.pdf" }],
        variant: "",
        ground_truth: {
          attr_name: "Насос центробежный консольный",
          attr_flow: 50,
          attr_head: 32,
          attr_power: 7.5,
          attr_voltage: 380,
          attr_speed: 2900,
          attr_efficiency: 72,
          attr_ip: "IP54",
          attr_mounting: "на раме",
          attr_material: "чугун",
          attr_weight: 118,
        },
        confidence: {
          attr_name: "hc",
          attr_flow: "lc",
          attr_head: "lc",
          attr_power: "hc",
          attr_voltage: "hc",
          attr_speed: "hc",
          attr_efficiency: "hc",
          attr_ip: "lc",
          attr_mounting: "lc",
          attr_material: "lc",
          attr_weight: "hc",
        },
      },
      {
        id: "card-003",
        name: "Электродвигатель однофазный 7.5 кВт",
        eos_id: "demo-item-003",
        status: "ready",
        created_at: "2026-07-17",
        objectTypeCode: "demo-motor",
        suggestedClass: "demo-motor",
        documents: [
          { file_name: "PASSPORT-DEMO-003.pdf" },
          { file_name: "TU-DEMO-003.pdf" },
        ],
        variant: "",
        ground_truth: {
          attr_name: "Электродвигатель асинхронный однофазный",
          attr_power: 7.5,
          attr_voltage: 220,
          attr_current: 14.8,
          attr_speed: 1450,
          attr_efficiency: 89.8,
          attr_ip: "IP54",
          attr_mounting: "на лапах",
          attr_insulation: "H",
          attr_weight: 56,
          attr_ambient_temp: { min: -40, max: 40 },
        },
        confidence: {
          attr_name: "hc",
          attr_power: "hc",
          attr_voltage: "hc",
          attr_current: "hc",
          attr_speed: "hc",
          attr_efficiency: "lc",
          attr_ip: "hc",
          attr_mounting: "hc",
          attr_insulation: "hc",
          attr_weight: "hc",
          attr_ambient_temp: "lc",
        },
      },
      {
        id: "card-001",
        name: "Электродвигатель асинхронный 5.5 кВт",
        eos_id: "demo-item-001",
        status: "done",
        created_at: "2026-07-14",
        objectTypeCode: "demo-motor",
        suggestedClass: "demo-motor",
        documents: [{ file_name: "TU-DEMO-001.pdf" }],
        variant: "",
        ground_truth: {
          attr_name: "Электродвигатель асинхронный",
          attr_power: 5.5,
          attr_voltage: 380,
          attr_current: 11.2,
          attr_speed: 1450,
          attr_efficiency: 89.5,
          attr_ip: "IP55",
          attr_mounting: "на лапах",
          attr_insulation: "F",
          attr_weight: 48,
          attr_ambient_temp: { min: -40, max: 40 },
        },
        confidence: {
          attr_name: "hc",
          attr_power: "hc",
          attr_voltage: "hc",
          attr_current: "hc",
          attr_speed: "lc",
          attr_efficiency: "hc",
          attr_ip: "hc",
          attr_mounting: "hc",
          attr_insulation: "hc",
          attr_weight: "hc",
          attr_ambient_temp: "hc",
        },
      },
      {
        id: "card-valve-001",
        name: "Затвор дисковый DN100",
        eos_id: "demo-item-valve-001",
        status: "done",
        created_at: "2026-07-18",
        objectTypeCode: "demo-valve",
        suggestedClass: "demo-valve",
        documents: [{ file_name: "PASSPORT-DEMO-VALVE-001.pdf" }],
        variant: "",
        ground_truth: {
          attr_name: "Затвор дисковый поворотный",
          attr_dn: 100,
          attr_pn: 1.6,
          attr_temp: { min: -20, max: 120 },
          attr_length: 52,
          attr_seal: "класс A",
          attr_connection: "межфланцевое",
          attr_drive: "рукоятка",
          attr_weight: 9.8,
          attr_zeta: 0.35,
        },
        confidence: {
          attr_name: "hc",
          attr_dn: "hc",
          attr_pn: "hc",
          attr_temp: "lc",
          attr_length: "lc",
          attr_seal: "hc",
          attr_connection: "hc",
          attr_drive: "lc",
          attr_weight: "hc",
          attr_zeta: "lc",
        },
      },
      {
        id: "card-004",
        name: "Электродвигатель асинхронный 3.0 кВт",
        eos_id: "demo-item-004",
        status: "draft",
        created_at: "2026-07-15",
        objectTypeCode: "demo-motor",
        suggestedClass: "demo-motor",
        documents: [{ file_name: "SCAN-DEMO-004.pdf" }],
        variant: "",
        ground_truth: {
          attr_name: "Электродвигатель асинхронный",
          attr_power: 3.0,
          attr_voltage: 380,
          attr_current: 6.5,
          attr_speed: 950,
          attr_efficiency: 87.0,
          attr_ip: "IP54",
          attr_mounting: "на лапах",
          attr_insulation: "B",
          attr_weight: 32,
          attr_ambient_temp: { min: -40, max: 40 },
        },
        confidence: {
          attr_name: "hc",
          attr_power: "lc",
          attr_voltage: "hc",
          attr_current: "lc",
          attr_speed: "lc",
          attr_efficiency: "lc",
          attr_ip: "hc",
          attr_mounting: "hc",
          attr_insulation: "hc",
          attr_weight: "hc",
          attr_ambient_temp: "lc",
        },
      },
      {
        id: "card-002",
        name: "Электродвигатель асинхронный 11 кВт",
        eos_id: "demo-item-002",
        status: "done",
        created_at: "2026-07-13",
        objectTypeCode: "demo-motor",
        suggestedClass: "demo-motor",
        documents: [{ file_name: "TU-DEMO-002.pdf" }],
        variant: "Исп. B",
        ground_truth: {
          attr_name: "Электродвигатель асинхронный",
          attr_power: 11.0,
          attr_voltage: 380,
          attr_current: 21.5,
          attr_speed: 2900,
          attr_efficiency: 91.2,
          attr_ip: "IP65",
          attr_mounting: "комбинированный",
          attr_insulation: "F",
          attr_weight: 72,
          attr_ambient_temp: { min: -40, max: 40 },
        },
        confidence: {
          attr_name: "hc",
          attr_power: "hc",
          attr_voltage: "hc",
          attr_current: "hc",
          attr_speed: "hc",
          attr_efficiency: "hc",
          attr_ip: "lc",
          attr_mounting: "lc",
          attr_insulation: "hc",
          attr_weight: "hc",
          attr_ambient_temp: "lc",
        },
      },
    ],
  };

  /** Intentional system mistakes for LC attrs — expert must correct against evidence. */
  const PREDICTION_OVERRIDES = {
    "card-001": {
      attr_speed: { value: 1500, unit: "мин⁻¹" },
    },
    "card-002": {
      attr_ip: { value: "IP55" },
      attr_mounting: { value: "на лапах" },
      attr_ambient_temp: { value: null, unit: "°C" },
    },
    "card-003": {
      attr_efficiency: { value: 90.0, unit: "%" },
      attr_ambient_temp: { value: null, unit: "°C" },
    },
    "card-004": {
      attr_current: { value: null, unit: "А" },
      attr_speed: { value: 1000, unit: "об/мин" },
      attr_efficiency: { value: null, unit: "%" },
      attr_ambient_temp: { value: null, unit: "°C" },
    },
    "card-pump-001": {
      attr_flow: { value: 45, unit: "м³/ч" },
      attr_head: { value: 30, unit: "м" },
    },
    "card-valve-001": {
      attr_temp: { value: { min: -10, max: 100 }, unit: "°C" },
      attr_zeta: { value: 0.4 },
    },
  };

  /** Shared document fragments as markdown (tables render to HTML). */
  const DOC_CHUNKS = {
    tu001_title: {
      file_name: "TU-DEMO-001.pdf",
      section: "Титульный лист",
      format: "md",
      text: `### Технические условия

**Обозначение:** АИР-DEMO-80A4  
**Наименование:** Электродвигатель асинхронный

Документ распространяется на электродвигатели серии АИР-DEMO.`,
    },
    tu001_prose: {
      file_name: "TU-DEMO-001.pdf",
      section: "§1 · Общие сведения",
      format: "md",
      text: `### 1. Общие сведения

Электродвигатель предназначен для работы в условиях умеренного климата.
Допустимая температура окружающей среды: **−40…+40 °C**.
Способ монтажа: **на лапах** (исполнение IM 1001).

Остальные номинальные параметры приведены в сводной таблице §2.`,
    },
    tu001_table: {
      file_name: "TU-DEMO-001.pdf",
      section: "§2 · Технические характеристики (сводная таблица)",
      format: "md",
      text: `Сводная таблица технических данных (альбомный лист). Строки 1–11 — параметры карточки; 12–18 — дополнительные поля документа.

| № | Параметр | Обозн. | Значение | Ед. | Допуск | Метод | Примечание |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Наименование | — | Электродвигатель асинхронный | — | — | визуально | табличка |
| 2 | Обозначение | — | АИР-DEMO-80A4 | — | — | визуально | — |
| 3 | Номинальная мощность | Pном | 5.5 | кВт | ±5 % | стенд | режим S1 |
| 4 | Номинальное напряжение | Uном | 380 | В | ±5 % | вольтметр | сеть |
| 5 | Номинальный ток | Iном | 11.2 | А | ±8 % | амперметр | при Uном |
| 6 | Частота вращения | nном | 1450 об/мин | — | ±2 % | тахометр | также ≈1500 мин⁻¹ |
| 7 | КПД | η | 89.5 | % | −0.5 | калориметрия | номинал |
| 8 | Степень защиты | IP | IP55 | — | — | осмотр | оболочка |
| 9 | Способ монтажа | IM | на лапах | — | — | осмотр | — |
| 10 | Класс изоляции | — | F | — | — | док. | обмотка |
| 11 | Масса | m | 48 | кг | ±3 % | весы | нетто |
| 12 | Частота сети | f | 50 | Гц | ±2 % | — | питание |
| 13 | Число полюсов | 2p | 4 | — | — | — | расч. |
| 14 | Момент пусковой / ном. | Mп/Mн | 2.1 | — | ±10 % | стенд | не в GT |
| 15 | Уровень вибрации | — | 2.8 | мм/с | max | виброметр | не в GT |
| 16 | Температура окружающей среды | — | −40…+40 | °C | — | — | эксплуатация |
| 17 | Высота установки | — | до 1000 | м | — | — | н.у.м. |
| 18 | Срок службы подшипников | — | 40000 | ч | — | расчёт | L10h |`,
    },
    tu002_intro: {
      file_name: "TU-DEMO-002.pdf",
      section: "§1 · Область применения",
      format: "md",
      text: `### 1. Область применения

Настоящие ТУ распространяются на электродвигатели асинхронные серии АИР-DEMO
в исполнениях A, **Исп. B**, C и D.

Карточка соответствует варианту **Исп. B** (типоразмер 112M2).
Параметры по вариантам — в таблице §2.`,
    },
    tu002_table: {
      file_name: "TU-DEMO-002.pdf",
      section: "§2 · Параметры по вариантам исполнения",
      format: "md",
      text: `Сводная таблица параметров по вариантам исполнения. Карточка соответствует **Исп. B**.

| Параметр | Ед. | Исп. A | Исп. B | Исп. C | Исп. D | Примечание |
| --- | --- | --- | --- | --- | --- | --- |
| Типоразмер | — | 80A4 | 112M2 | 132S4 | 160M4 | габарит |
| Номинальная мощность | кВт | 5.5 | 11.0 | 15.0 | 18.5 | S1 |
| Номинальное напряжение | В | 380 | 380 | 380 | 380 | ±5 % |
| Номинальный ток | А | 11.2 | 21.5 | 28.0 | 35.2 | при 380 В |
| Частота вращения | об/мин | 1450 | 2900 | 2950 | 1470 | номинал |
| Скольжение | % | 4.2 | 3.8 | 3.5 | 2.9 | расч. |
| КПД | % | 89.5 | 91.2 | 92.0 | 92.5 | при ηном |
| cos φ | — | 0.82 | 0.87 | 0.86 | 0.88 | номинал |
| Степень защиты | — | IP55 | IP65 | IP65 | IP55 | ГОСТ-подобно |
| Способ монтажа | — | на лапах | комбинированный | фланцевый | на лапах | IM |
| Класс изоляции | — | F | F | H | F | нагревостойкость |
| Масса | кг | 48 | 72 | 95 | 128 | без шкива |
| Момент инерции ротора | кг·м² | 0.012 | 0.028 | 0.041 | 0.067 | J |
| Уровень шума | дБ(А) | 68 | 72 | 74 | 76 | 1м |
| Сервис-фактор | — | 1.15 | 1.15 | 1.0 | 1.15 | SF |`,
    },
    tu003_chars: {
      file_name: "TU-DEMO-003.pdf",
      section: "§2 · Основные характеристики",
      format: "md",
      text: `### 2. Основные характеристики

| Параметр | Значение |
| --- | --- |
| Наименование (в ТУ) | Электродвигатель асинхронный |
| Обозначение | АИР-DEMO-90L4-1f |
| Номинальная мощность | 7.5 кВт |
| Номинальное напряжение | 220 В |
| Номинальный ток | 14.8 А |
| Частота вращения | 1450 об/мин |
| КПД | 90.0 % |
| Степень защиты | IP54 |
| Способ монтажа | на лапах |

Примечание. В таблице указано округлённое значение КПД **90.0 %**. По результатам типовых испытаний КПД составляет **89.8 %** — именно его следует заносить в карточку изделия. Класс изоляции и масса — в паспорте.

Полное наименование и часть параметров уточняются в паспорте (\`PASSPORT-DEMO-003\`).`,
    },
    passport003: {
      file_name: "PASSPORT-DEMO-003.pdf",
      section: "§1–2 · Паспорт изделия",
      format: "md",
      text: `### ПАСПОРТ ИЗДЕЛИЯ

Электродвигатель асинхронный однофазный  
Обозначение: \`АИР-DEMO-90L4-1f\` · demo-item-003

#### 1. Сведения об изделии

| Поле | Значение |
| --- | --- |
| Наименование | Электродвигатель асинхронный однофазный |
| Обозначение | АИР-DEMO-90L4-1f |
| Класс демо | demo-motor |
| Заводской № (демо) | SN-DEMO-003-2024 |

#### 2. Технические данные паспорта

| Параметр | Значение |
| --- | --- |
| Класс изоляции | H |
| Масса | 56 кг |
| КПД (типовые испытания) | 89.8 % |
| Степень защиты | IP54 |
| Номинальная мощность | 7.5 кВт |
| Номинальное напряжение | 220 В |

Паспорт имеет приоритет над округлениями краткого ТУ при заполнении карточки.`,
    },
    scan004_table: {
      file_name: "SCAN-DEMO-004.pdf",
      section: "OCR · таблица параметров (скан без text layer)",
      format: "md",
      text: `OCR-фрагмент скана \`SCAN-DEMO-004.pdf\`

| Параметр | Значение (распознано) |
| --- | --- |
| Наименование | Электродвигатель асинхронный |
| Номинальная мощность | ~ 3.0 кВт |
| Номинальное напряжение | 380 В |
| Номинальный ток | 6.? А |
| Частота вращения | 1000 / 950 об/мин |
| КПД | 8?.0 % |
| Степень защиты | IP54 |
| Способ монтажа | на лапах |
| Класс изоляции | B |
| Масса | 32 кг |
| Температура окружающей среды | ? … ? |

Табличка на корпусе (OCR):

- Iном … **6,5 A** …
- ηном ≈ **87 %** при режиме S1`,
    },
    pump_title: {
      file_name: "TU-DEMO-PUMP-001.pdf",
      section: "Титульный лист",
      format: "md",
      text: `### Технические условия

**Наименование:** Насос центробежный консольный  
**Обозначение:** К-DEMO-50-32

Документ распространяется на центробежные консольные насосы серии К-DEMO.`,
    },
    pump_prose_duty: {
      file_name: "TU-DEMO-PUMP-001.pdf",
      section: "§1 · Рабочие параметры",
      format: "md",
      text: `### 1. Рабочие параметры

Номинальная подача насоса составляет **50 м³/ч**.
Номинальный напор — **32 м**.

Режим работы — непрерывный (S1). Перекачиваемая среда — вода и нейтральные жидкости.`,
    },
    pump_prose_env: {
      file_name: "TU-DEMO-PUMP-001.pdf",
      section: "§2 · Конструкция и исполнение",
      format: "md",
      text: `### 2. Конструкция и исполнение

Степень защиты электродвигателя привода: **IP54**.
Материал корпуса насоса: **чугун**.
Способ монтажа: **на раме**.

Корпус и рабочее колесо рассчитаны на чистые среды без абразива.`,
    },
    pump_table: {
      file_name: "TU-DEMO-PUMP-001.pdf",
      section: "§3 · Электрические и массогабаритные данные",
      format: "md",
      text: `### 3. Электрические и массогабаритные данные

Электрические параметры привода:

| Параметр | Значение |
| --- | --- |
| Мощность | 7.5 кВт |
| Напряжение | 380 В |
| Частота вращения | 2900 об/мин |

КПД и масса агрегата (отдельная таблица):

| Параметр | Значение |
| --- | --- |
| КПД | 72 % |
| Масса | 118 кг |`,
    },
    valve_title: {
      file_name: "PASSPORT-DEMO-VALVE-001.pdf",
      section: "Титульный лист",
      format: "md",
      text: `### Паспорт изделия

**Наименование:** Затвор дисковый поворотный  
**Обозначение:** ЗДП-DEMO-100

Паспорт распространяется на затворы дисковые поворотные серии ЗДП-DEMO.`,
    },
    valve_prose_main: {
      file_name: "PASSPORT-DEMO-VALVE-001.pdf",
      section: "§1 · Основные параметры",
      format: "md",
      text: `### 1. Основные параметры

Условный диаметр: **DN 100**.
Номинальное давление: **PN 1.6 МПа**.

Затвор предназначен для перекрытия потока в трубопроводах.`,
    },
    valve_prose_tech: {
      file_name: "PASSPORT-DEMO-VALVE-001.pdf",
      section: "§2 · Технические характеристики",
      format: "md",
      text: `### 2. Технические характеристики

Рабочая температура среды: **−20…+120 °C**.
Привод: **рукоятка**.
Строительная длина: **52 мм**.`,
    },
    valve_table: {
      file_name: "PASSPORT-DEMO-VALVE-001.pdf",
      section: "§3 · Конструкция",
      format: "md",
      text: `### 3. Конструкция

| Параметр | Значение |
| --- | --- |
| Масса | 9.8 кг |
| Класс герметичности | класс A |
| Присоединение | межфланцевое |`,
    },
    valve_prose_zeta: {
      file_name: "PASSPORT-DEMO-VALVE-001.pdf",
      section: "§4 · Гидравлические потери",
      format: "md",
      text: `### 4. Гидравлические потери

Коэффициент местного сопротивления в полностью открытом положении:
**ζ ≈ 0.35**.`,
    },
  };

  /** Evidence: chunk + raw_quote only (no pipeline commentary). One source per attr. */
  const EVIDENCE = {
    "card-001": {
      attr_name: { kind: "source", chunk_id: "tu001_title", raw_quote: "Электродвигатель асинхронный" },
      attr_power: { kind: "source", chunk_id: "tu001_table", raw_quote: "5.5" },
      attr_voltage: { kind: "source", chunk_id: "tu001_table", raw_quote: "380" },
      attr_current: { kind: "source", chunk_id: "tu001_table", raw_quote: "11.2" },
      attr_speed: { kind: "source", chunk_id: "tu001_table", raw_quote: "≈1500 мин⁻¹" },
      attr_efficiency: { kind: "source", chunk_id: "tu001_table", raw_quote: "89.5" },
      attr_ip: { kind: "source", chunk_id: "tu001_table", raw_quote: "IP55" },
      attr_mounting: { kind: "source", chunk_id: "tu001_prose", raw_quote: "на лапах" },
      attr_insulation: { kind: "source", chunk_id: "tu001_table", raw_quote: "F" },
      attr_weight: { kind: "source", chunk_id: "tu001_table", raw_quote: "48" },
      attr_ambient_temp: { kind: "source", chunk_id: "tu001_prose", raw_quote: "−40…+40" },
    },
    "card-002": {
      attr_name: { kind: "source", chunk_id: "tu002_intro", raw_quote: "электродвигатели асинхронные" },
      attr_power: { kind: "source", chunk_id: "tu002_table", raw_quote: "11.0" },
      attr_voltage: { kind: "source", chunk_id: "tu002_table", raw_quote: "380" },
      attr_current: { kind: "source", chunk_id: "tu002_table", raw_quote: "21.5" },
      attr_speed: { kind: "source", chunk_id: "tu002_table", raw_quote: "2900" },
      attr_efficiency: { kind: "source", chunk_id: "tu002_table", raw_quote: "91.2" },
      attr_ip: { kind: "source", chunk_id: "tu002_table", raw_quote: "IP55" },
      attr_mounting: { kind: "source", chunk_id: "tu002_table", raw_quote: "на лапах" },
      attr_insulation: { kind: "source", chunk_id: "tu002_table", raw_quote: "F" },
      attr_weight: { kind: "source", chunk_id: "tu002_table", raw_quote: "72" },
      attr_ambient_temp: {
        kind: "nearest",
        candidates: [{ chunk_id: "tu002_table", raw_quote: null }],
      },
    },
    "card-003": {
      attr_name: { kind: "source", chunk_id: "passport003", raw_quote: "Электродвигатель асинхронный однофазный" },
      attr_power: { kind: "source", chunk_id: "passport003", raw_quote: "7.5 кВт" },
      attr_voltage: { kind: "source", chunk_id: "passport003", raw_quote: "220 В" },
      attr_current: { kind: "source", chunk_id: "tu003_chars", raw_quote: "14.8 А" },
      attr_speed: { kind: "source", chunk_id: "tu003_chars", raw_quote: "1450 об/мин" },
      attr_efficiency: { kind: "source", chunk_id: "tu003_chars", raw_quote: "90.0 %" },
      attr_ip: { kind: "source", chunk_id: "passport003", raw_quote: "IP54" },
      attr_mounting: { kind: "source", chunk_id: "tu003_chars", raw_quote: "на лапах" },
      attr_insulation: { kind: "source", chunk_id: "passport003", raw_quote: "H" },
      attr_weight: { kind: "source", chunk_id: "passport003", raw_quote: "56 кг" },
      attr_ambient_temp: {
        kind: "nearest",
        candidates: [{ chunk_id: "tu003_chars", raw_quote: null }],
      },
    },
    "card-004": {
      attr_name: { kind: "source", chunk_id: "scan004_table", raw_quote: "Электродвигатель асинхронный" },
      attr_power: { kind: "source", chunk_id: "scan004_table", raw_quote: "~ 3.0 кВт" },
      attr_voltage: { kind: "source", chunk_id: "scan004_table", raw_quote: "380 В" },
      attr_current: {
        kind: "nearest",
        candidates: [{ chunk_id: "scan004_table", raw_quote: "6.? А" }],
      },
      attr_speed: { kind: "source", chunk_id: "scan004_table", raw_quote: "1000 / 950 об/мин" },
      attr_efficiency: {
        kind: "nearest",
        candidates: [{ chunk_id: "scan004_table", raw_quote: null }],
      },
      attr_ip: { kind: "source", chunk_id: "scan004_table", raw_quote: "IP54" },
      attr_mounting: { kind: "source", chunk_id: "scan004_table", raw_quote: "на лапах" },
      attr_insulation: { kind: "source", chunk_id: "scan004_table", raw_quote: "B" },
      attr_weight: { kind: "source", chunk_id: "scan004_table", raw_quote: "32 кг" },
      attr_ambient_temp: {
        kind: "nearest",
        candidates: [{ chunk_id: "scan004_table", raw_quote: null }],
      },
    },
    "card-pump-001": {
      attr_name: { kind: "source", chunk_id: "pump_title", raw_quote: "Насос центробежный консольный" },
      attr_flow: { kind: "source", chunk_id: "pump_prose_duty", raw_quote: "50 м³/ч" },
      attr_head: { kind: "source", chunk_id: "pump_prose_duty", raw_quote: "32 м" },
      attr_power: { kind: "source", chunk_id: "pump_table", raw_quote: "7.5 кВт" },
      attr_voltage: { kind: "source", chunk_id: "pump_table", raw_quote: "380 В" },
      attr_speed: { kind: "source", chunk_id: "pump_table", raw_quote: "2900 об/мин" },
      attr_efficiency: { kind: "source", chunk_id: "pump_table", raw_quote: "72 %" },
      attr_ip: { kind: "source", chunk_id: "pump_prose_env", raw_quote: "IP54" },
      attr_mounting: { kind: "source", chunk_id: "pump_prose_env", raw_quote: "на раме" },
      attr_material: { kind: "source", chunk_id: "pump_prose_env", raw_quote: "чугун" },
      attr_weight: { kind: "source", chunk_id: "pump_table", raw_quote: "118 кг" },
    },
    "card-valve-001": {
      attr_name: { kind: "source", chunk_id: "valve_title", raw_quote: "Затвор дисковый поворотный" },
      attr_dn: { kind: "source", chunk_id: "valve_prose_main", raw_quote: "DN 100" },
      attr_pn: { kind: "source", chunk_id: "valve_prose_main", raw_quote: "PN 1.6" },
      attr_temp: { kind: "source", chunk_id: "valve_prose_tech", raw_quote: "−20…+120" },
      attr_length: { kind: "source", chunk_id: "valve_prose_tech", raw_quote: "52 мм" },
      attr_seal: { kind: "source", chunk_id: "valve_table", raw_quote: "класс A" },
      attr_connection: { kind: "source", chunk_id: "valve_table", raw_quote: "межфланцевое" },
      attr_drive: { kind: "source", chunk_id: "valve_prose_tech", raw_quote: "рукоятка" },
      attr_weight: { kind: "source", chunk_id: "valve_table", raw_quote: "9.8 кг" },
      attr_zeta: { kind: "source", chunk_id: "valve_prose_zeta", raw_quote: "ζ ≈ 0.35" },
    },
  };

  const state = {
    view: "cards",
    cardId: null,
    wizardStep: "kit",
    statusFilter: "all",
    searchQuery: "",
    sortBy: "date-desc",
    reviewFilter: "attention",
    selectedAttrId: null,
    evidenceExpanded: {},
    processing: {
      active: false,
      stepIndex: -1,
      timer: null,
      startedAt: null,
    },
  };

  const main = document.getElementById("app-main");
  const toastEl = document.getElementById("toast");

  function displayEosId(eosId) {
    return eosId.replace(/^demo-/, "");
  }

  function displayFileName(fileName) {
    return fileName.replace(/-DEMO-/g, "-").replace(/^DEMO-/, "");
  }

  function formatDate(iso) {
    const [y, m, d] = iso.split("-");
    return `${d}.${m}.${y}`;
  }

  function formatValue(value, unit) {
    if (value === null || value === undefined || value === "") return "—";
    if (typeof value === "object" && value !== null && ("min" in value || "max" in value)) {
      const min = value.min === null || value.min === undefined ? "…" : String(value.min);
      const max = value.max === null || value.max === undefined ? "…" : String(value.max);
      const text = `${min}…${max}`;
      return unit ? `${text} ${unit}` : text;
    }
    const text = typeof value === "number" ? String(value) : String(value);
    return unit ? `${text} ${unit}` : text;
  }

  function formatDocCount(n) {
    if (n === 1) return "1 документ";
    if (n >= 2 && n <= 4) return `${n} документа`;
    return `${n} документов`;
  }

  function getAttrOrder(card) {
    return (CLASS_ATTRS[card.objectTypeCode] || CLASS_ATTRS["demo-motor"]).order;
  }

  function attrMeta(attrId, classCode) {
    const schema = CLASS_ATTRS[classCode] || CLASS_ATTRS["demo-motor"];
    return schema.byId[attrId];
  }

  function getCard(id) {
    return SEED.cards.find((c) => c.id === id);
  }

  function objectType(code) {
    return OBJECT_TYPES.find((t) => t.code === code) || OBJECT_TYPES[0];
  }

  function defaultUnit(meta) {
    if (!meta.units || !meta.units.length) return null;
    return meta.units[0];
  }

  function typeLabel(attrType) {
    if (attrType === "enum") return "справочник";
    if (attrType === "number") return "число";
    if (attrType === "range") return "диапазон";
    return "текст";
  }

  function formatSchemaUnits(meta) {
    if (!meta.units || !meta.units.length) return "—";
    return meta.units.join(" · ");
  }

  function formatSchemaAllowed(meta) {
    if (!meta.allowed_values || !meta.allowed_values.length) {
      return `<span class="class-schema__empty">—</span>`;
    }
    return `<div class="class-schema__chips">${meta.allowed_values
      .map((v) => `<span class="class-schema__chip">${escapeHtml(v)}</span>`)
      .join("")}</div>`;
  }

  function renderClassSchema(card) {
    const schema = CLASS_ATTRS[card.objectTypeCode];
    if (!schema) return "";
    const count = schema.attributes.length;
    const rows = schema.attributes
      .map(
        (attr) => `
      <tr>
        <td class="class-schema__col-name">
          <div class="class-schema__name">${escapeHtml(attr.attr_name)}</div>
          <div class="class-schema__id mono">${escapeHtml(attr.attr_id)}</div>
        </td>
        <td class="class-schema__col-type"><span class="class-schema__type">${escapeHtml(typeLabel(attr.attr_type))}</span></td>
        <td class="class-schema__col-unit">${escapeHtml(formatSchemaUnits(attr))}</td>
        <td class="class-schema__col-allowed">${formatSchemaAllowed(attr)}</td>
      </tr>`,
      )
      .join("");

    return `
      <div class="class-schema">
        <div class="class-schema__head">
          <h3 class="class-schema__title">Атрибуты класса</h3>
          <span class="class-schema__count">${count}</span>
        </div>
        <div class="class-schema__scroll">
          <table class="class-schema__table">
            <colgroup>
              <col class="class-schema__w-name" />
              <col class="class-schema__w-type" />
              <col class="class-schema__w-unit" />
              <col class="class-schema__w-allowed" />
            </colgroup>
            <thead>
              <tr>
                <th>Атрибут</th>
                <th>Тип</th>
                <th>Ед.</th>
                <th>Справочник</th>
              </tr>
            </thead>
            <tbody>${rows}</tbody>
          </table>
        </div>
      </div>`;
  }

  function cloneValue(value) {
    if (value && typeof value === "object") return { ...value };
    return value;
  }

  function valuesEqual(a, b) {
    if (a === null || a === undefined || a === "") {
      return b === null || b === undefined || b === "";
    }
    if (b === null || b === undefined || b === "") return false;
    if (typeof a === "object" || typeof b === "object") {
      if (!a || !b || typeof a !== "object" || typeof b !== "object") return false;
      return Number(a.min) === Number(b.min) && Number(a.max) === Number(b.max);
    }
    if (typeof a === "number" || typeof b === "number") {
      return Number(a) === Number(b);
    }
    return String(a) === String(b);
  }

  function slotsEqual(a, b) {
    if (!a && !b) return true;
    if (!a || !b) return false;
    return valuesEqual(a.value, b.value) && (a.unit || null) === (b.unit || null);
  }

  function makeSlot(meta, value, unit) {
    const resolvedUnit =
      unit !== undefined ? unit : meta.units && meta.units.length ? defaultUnit(meta) : null;
    return { value: cloneValue(value), unit: resolvedUnit };
  }

  function buildPredictions(card) {
    const overrides = PREDICTION_OVERRIDES[card.id] || {};
    const out = {};
    getAttrOrder(card).forEach((attrId) => {
      const meta = attrMeta(attrId, card.objectTypeCode);
      const gt = card.ground_truth[attrId];
      const over = overrides[attrId];
      if (over && Object.prototype.hasOwnProperty.call(over, "value")) {
        out[attrId] = makeSlot(
          meta,
          over.value,
          Object.prototype.hasOwnProperty.call(over, "unit") ? over.unit : defaultUnit(meta),
        );
      } else {
        out[attrId] = makeSlot(meta, gt, defaultUnit(meta));
      }
    });
    return out;
  }

  function resetReviewState(card) {
    card.predictions = buildPredictions(card);
    card.values = {};
    getAttrOrder(card).forEach((id) => {
      card.values[id] = {
        value: cloneValue(card.predictions[id].value),
        unit: card.predictions[id].unit,
      };
    });
    card.confirmed = {};
  }

  function ensureReviewState(card) {
    if (!card.predictions) card.predictions = buildPredictions(card);
    if (!card.values) {
      card.values = {};
      getAttrOrder(card).forEach((id) => {
        card.values[id] = {
          value: cloneValue(card.predictions[id].value),
          unit: card.predictions[id].unit,
        };
      });
    }
    if (!card.confirmed) card.confirmed = {};
  }

  function parseNumberInput(raw) {
    const text = String(raw ?? "").trim().replace(",", ".");
    if (!text) return null;
    const num = Number(text);
    return Number.isNaN(num) ? null : num;
  }

  function resolveChunk(entry) {
    if (entry.chunk_id && DOC_CHUNKS[entry.chunk_id]) {
      const base = DOC_CHUNKS[entry.chunk_id];
      return {
        file_name: base.file_name,
        section: base.section,
        chunk: base.text,
        format: base.format || "md",
        raw_quote: entry.raw_quote || null,
      };
    }
    return {
      file_name: entry.file_name || "document.pdf",
      section: entry.section || "Фрагмент документа",
      chunk: entry.chunk || "",
      format: entry.format || "md",
      raw_quote: entry.raw_quote || null,
    };
  }

  function getEvidence(card, attrId) {
    const meta = attrMeta(attrId, card.objectTypeCode);
    const custom = EVIDENCE[card.id]?.[attrId];
    if (custom) {
      if (custom.kind === "candidates" || custom.kind === "nearest") {
        return {
          kind: custom.kind,
          attr_name: meta.attr_name,
          candidates: (custom.candidates || []).map(resolveChunk),
        };
      }
      return { kind: "source", attr_name: meta.attr_name, ...resolveChunk(custom) };
    }

    const proposed = card.predictions?.[attrId]?.value;
    const fileName = card.documents[0]?.file_name || "document.pdf";
    if (isEmptyValue(proposed)) {
      return {
        kind: "nearest",
        attr_name: meta.attr_name,
        candidates: [
          {
            file_name: fileName,
            section: "Поиск по документу",
            format: "md",
            chunk: `Релевантный фрагмент для атрибута «${meta.attr_name}» не найден с достаточной уверенностью.`,
            raw_quote: null,
          },
        ],
      };
    }

    const valueText = formatValue(proposed, card.predictions[attrId].unit);
    return {
      kind: "source",
      attr_name: meta.attr_name,
      file_name: fileName,
      section: "Технические характеристики",
      format: "md",
      chunk: `| Параметр | Значение |\n| --- | --- |\n| ${meta.attr_name} | ${valueText} |`,
      raw_quote: valueText,
    };
  }

  function markFirst(html, needle) {
    if (!needle) return { html, found: false };
    const idx = html.indexOf(needle);
    if (idx < 0) return { html, found: false };
    return {
      html: `${html.slice(0, idx)}<mark>${needle}</mark>${html.slice(idx + needle.length)}`,
      found: true,
    };
  }

  function highlightInAttrRow(html, attrName, rawQuote) {
    if (!attrName || !html.includes("<tr")) return null;
    const nameNeedle = escapeHtml(attrName);
    const quoteNeedle = rawQuote ? escapeHtml(String(rawQuote)) : null;
    let changed = false;
    const next = html.replace(/<tr[\s\S]*?<\/tr>/gi, (row) => {
      if (!row.includes(nameNeedle)) return row;
      changed = true;
      if (quoteNeedle) {
        const marked = markFirst(row, quoteNeedle);
        if (marked.found) return marked.html;
      }
      const markedName = markFirst(row, nameNeedle);
      return markedName.found ? markedName.html : row;
    });
    return changed ? next : null;
  }

  function highlightInHtml(html, rawQuote, attrName) {
    const scoped = highlightInAttrRow(html, attrName, rawQuote);
    if (scoped) return scoped;

    if (rawQuote) {
      const marked = markFirst(html, escapeHtml(String(rawQuote)));
      if (marked.found) return marked.html;
      if (attrName) {
        const named = markFirst(html, escapeHtml(attrName));
        if (named.found) return named.html;
      }
      return `${html}<div class="evidence-quote-fallback">Цитата: <mark>${escapeHtml(
        String(rawQuote),
      )}</mark></div>`;
    }

    if (attrName) {
      const named = markFirst(html, escapeHtml(attrName));
      if (named.found) return named.html;
    }
    return html;
  }

  function inlineMarkdown(text) {
    let html = escapeHtml(text);
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
    html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/(^|[^\*])\*([^*]+)\*(?!\*)/g, "$1<em>$2</em>");
    return html;
  }

  function splitMdCells(line) {
    let body = line.trim();
    if (body.startsWith("|")) body = body.slice(1);
    if (body.endsWith("|")) body = body.slice(0, -1);
    return body.split("|").map((cell) => cell.trim());
  }

  function isMdSeparator(line) {
    const cells = splitMdCells(line);
    return cells.length > 0 && cells.every((cell) => /^:?-{3,}:?$/.test(cell));
  }

  function isMdTableLine(line) {
    const trimmed = line.trim();
    return trimmed.includes("|") && !isMdSeparator(trimmed);
  }

  function renderMdTable(lines) {
    const rows = lines.filter((line) => !isMdSeparator(line)).map(splitMdCells);
    if (!rows.length) return "";
    const header = rows[0];
    const body = rows.slice(1);
    const thead = `<thead><tr>${header
      .map((cell) => `<th>${inlineMarkdown(cell)}</th>`)
      .join("")}</tr></thead>`;
    const tbody = body.length
      ? `<tbody>${body
          .map(
            (row) =>
              `<tr>${row.map((cell) => `<td>${inlineMarkdown(cell)}</td>`).join("")}</tr>`,
          )
          .join("")}</tbody>`
      : "";
    return `<div class="evidence-table-wrap"><table class="evidence-table">${thead}${tbody}</table></div>`;
  }

  function renderMarkdown(md) {
    const lines = String(md || "").replace(/\r\n/g, "\n").split("\n");
    const parts = [];
    let i = 0;
    while (i < lines.length) {
      const line = lines[i];
      if (!line.trim()) {
        i += 1;
        continue;
      }
      if (isMdTableLine(line) || (line.trim().startsWith("|") && i + 1 < lines.length && isMdSeparator(lines[i + 1]))) {
        const tableLines = [];
        while (i < lines.length && (isMdTableLine(lines[i]) || isMdSeparator(lines[i]))) {
          tableLines.push(lines[i]);
          i += 1;
        }
        parts.push(renderMdTable(tableLines));
        continue;
      }
      if (/^###\s+/.test(line)) {
        parts.push(`<h5 class="evidence-h">${inlineMarkdown(line.replace(/^###\s+/, ""))}</h5>`);
        i += 1;
        continue;
      }
      if (/^####\s+/.test(line)) {
        parts.push(`<h6 class="evidence-h">${inlineMarkdown(line.replace(/^####\s+/, ""))}</h6>`);
        i += 1;
        continue;
      }
      if (/^[-*]\s+/.test(line.trim())) {
        const items = [];
        while (i < lines.length && /^[-*]\s+/.test(lines[i].trim())) {
          items.push(`<li>${inlineMarkdown(lines[i].trim().replace(/^[-*]\s+/, ""))}</li>`);
          i += 1;
        }
        parts.push(`<ul class="evidence-list-bullets">${items.join("")}</ul>`);
        continue;
      }
      const para = [];
      while (
        i < lines.length &&
        lines[i].trim() &&
        !isMdTableLine(lines[i]) &&
        !lines[i].trim().startsWith("|") &&
        !/^#{1,6}\s+/.test(lines[i]) &&
        !/^[-*]\s+/.test(lines[i].trim())
      ) {
        para.push(lines[i]);
        i += 1;
      }
      parts.push(
        `<p class="evidence-p">${para.map((row) => inlineMarkdown(row)).join("<br />")}</p>`,
      );
    }
    return `<div class="evidence-md">${parts.join("")}</div>`;
  }

  function looksLikeHtmlChunk(text) {
    return /<\s*table[\s>]/i.test(text) || /<\s*div[\s>]/i.test(text);
  }

  function renderChunkContent(chunk, rawQuote, format, attrName) {
    const text = String(chunk || "");
    if (format === "html" || looksLikeHtmlChunk(text)) {
      return highlightInHtml(text, rawQuote, attrName);
    }
    if (format === "md" || format === "markdown" || text.includes("|")) {
      return highlightInHtml(renderMarkdown(text), rawQuote, attrName);
    }
    const escaped = escapeHtml(text).replace(/\n/g, "<br />");
    return `<div class="evidence-pre">${highlightInHtml(escaped, rawQuote, attrName)}</div>`;
  }

  function renderEvidenceCard(item, badge, expandKey, attrName) {
    const contentHtml = renderChunkContent(
      item.chunk,
      item.raw_quote,
      item.format || "md",
      attrName || item.attr_name || null,
    );
    const plainLen = String(item.chunk || "").length;
    const long = plainLen > 520 || (item.chunk || "").split("\n").length > 14;
    const expanded = Boolean(state.evidenceExpanded[expandKey]);
    const bodyClass =
      long && !expanded ? "evidence-body is-collapsed" : "evidence-body";
    const toggle = long
      ? `<button type="button" class="btn btn--sm btn--secondary evidence-toggle" data-evidence-toggle="${escapeHtml(
          expandKey,
        )}">${expanded ? "Свернуть фрагмент" : "Показать весь фрагмент"}</button>`
      : "";
    return `
      <article class="evidence-card">
        <div class="evidence-card__meta">
          <span class="evidence-card__file">${escapeHtml(displayFileName(item.file_name))}</span>
          <span class="evidence-card__section">${escapeHtml(item.section)}</span>
          <span class="evidence-card__badge">${escapeHtml(badge)}</span>
        </div>
        <div class="${bodyClass}">${contentHtml}</div>
        ${toggle}
      </article>`;
  }

  function isEmptyValue(value) {
    if (value === null || value === undefined || value === "") return true;
    if (typeof value === "object") {
      return (
        (value.min === null || value.min === undefined || value.min === "") &&
        (value.max === null || value.max === undefined || value.max === "")
      );
    }
    return false;
  }

  function attrStatus(card, attrId) {
    ensureReviewState(card);
    const conf = card.confidence?.[attrId] || "hc";
    const confirmed = Boolean(card.confirmed[attrId]);
    const proposed = card.predictions[attrId];
    const current = card.values[attrId];
    const edited = !slotsEqual(current, proposed);
    const empty = isEmptyValue(current?.value);
    const needsAttention = conf === "lc" && !confirmed;
    return {
      conf,
      confirmed,
      proposed: proposed?.value,
      proposedUnit: proposed?.unit ?? null,
      value: current?.value,
      unit: current?.unit ?? null,
      edited,
      empty,
      needsAttention,
    };
  }

  function orderedReviewAttrs(card) {
    ensureReviewState(card);
    const order = getAttrOrder(card);
    const attrs = [...order];
    attrs.sort((a, b) => {
      const sa = attrStatus(card, a);
      const sb = attrStatus(card, b);
      if (sa.needsAttention !== sb.needsAttention) return sa.needsAttention ? -1 : 1;
      if (sa.conf !== sb.conf) return sa.conf === "lc" ? -1 : 1;
      return order.indexOf(a) - order.indexOf(b);
    });
    return attrs;
  }

  function filteredReviewAttrs(card) {
    const attrs = orderedReviewAttrs(card);
    if (state.reviewFilter === "attention") {
      return attrs.filter((id) => attrStatus(card, id).needsAttention);
    }
    if (state.reviewFilter === "edited") {
      return attrs.filter((id) => attrStatus(card, id).edited);
    }
    if (state.reviewFilter === "confirmed") {
      return attrs.filter((id) => attrStatus(card, id).confirmed);
    }
    return attrs;
  }

  function reviewCounts(card) {
    ensureReviewState(card);
    const order = getAttrOrder(card);
    let attention = 0;
    let confirmed = 0;
    let edited = 0;
    order.forEach((id) => {
      const s = attrStatus(card, id);
      if (s.needsAttention) attention += 1;
      if (s.confirmed) confirmed += 1;
      if (s.edited) edited += 1;
    });
    return { attention, confirmed, edited, total: order.length };
  }

  function selectDefaultAttr(card) {
    const order = getAttrOrder(card);
    const attentionFirst = orderedReviewAttrs(card).find((id) => attrStatus(card, id).needsAttention);
    state.selectedAttrId = attentionFirst || order[0];
  }

  function markAttrDirty(card, attrId) {
    ensureReviewState(card);
    card.confirmed[attrId] = false;
  }

  function showToast(message) {
    toastEl.textContent = message;
    toastEl.hidden = false;
    clearTimeout(showToast._t);
    showToast._t = setTimeout(() => {
      toastEl.hidden = true;
    }, 2800);
  }

  function pdfBytes(fileName) {
    const b64 = window.DEMO_PDF_BASE64 && window.DEMO_PDF_BASE64[fileName];
    if (!b64) return null;
    const binary = atob(b64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
    return bytes;
  }

  function downloadPdf(fileName) {
    const bytes = pdfBytes(fileName);
    const niceName = displayFileName(fileName);
    if (!bytes) {
      showToast("Документ недоступен в этой сборке.");
      return;
    }
    const blob = new Blob([bytes], { type: "application/pdf" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = niceName;
    a.click();
    URL.revokeObjectURL(url);
    showToast(`Документ «${niceName}» сохранён.`);
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function wizardIndex(stepId) {
    return WIZARD.findIndex((s) => s.id === stepId);
  }

  function defaultWizardStep(card) {
    if (card.status === "done") return "review";
    if (card.status === "processing") return "run";
    return "kit";
  }

  function canEnterStep(card, stepId) {
    if (stepId === "kit" || stepId === "run") return true;
    if (stepId === "review" || stepId === "export") return card.status === "done";
    return true;
  }

  function classReady(card) {
    return Boolean(objectType(card.objectTypeCode).demo);
  }

  function kitReady(card) {
    return classReady(card) && card.documents.length > 0;
  }

  function estimateTotalSeconds() {
    return PIPELINE.reduce((sum, step) => sum + step.seconds, 0);
  }

  function formatDuration(totalSeconds) {
    const s = Math.max(0, Math.round(totalSeconds));
    if (s < 60) return `~${s} с`;
    const m = Math.floor(s / 60);
    const rest = s % 60;
    return rest ? `~${m} мин ${rest} с` : `~${m} мин`;
  }

  function stopProcessingTimer() {
    if (state.processing.timer) {
      clearInterval(state.processing.timer);
      state.processing.timer = null;
    }
    state.processing.active = false;
  }

  function abortProcessing(card) {
    stopProcessingTimer();
    state.processing.stepIndex = -1;
    state.processing.startedAt = null;
    if (card && card.status === "processing") card.status = "ready";
    showToast("Обработка прервана.");
    render();
  }

  function processingProgress(card) {
    const isDone = card.status === "done";
    const isRunning = card.status === "processing" && state.processing.active;
    const activeIndex = isRunning ? state.processing.stepIndex : isDone ? PIPELINE.length : -1;
    const percent = isDone
      ? 100
      : isRunning
        ? Math.min(99, Math.round(((activeIndex + 0.35) / PIPELINE.length) * 100))
        : 0;
    const totalSec = estimateTotalSeconds();
    let etaText = formatDuration(totalSec);
    if (isRunning) {
      const remainingSteps = Math.max(0, PIPELINE.length - activeIndex);
      etaText = `осталось ${formatDuration(remainingSteps * (STEP_MS / 1000))}`;
    } else if (isDone) {
      etaText = "завершено";
    }
    const statusLine = isDone
      ? "Извлечение завершено. Перейдите к сверке атрибутов"
      : isRunning
        ? `Этап ${activeIndex + 1} из ${PIPELINE.length} · ${percent}% · ${etaText}`
        : `Оценка времени: ${formatDuration(totalSec)} · ${PIPELINE.length} этапов`;
    return { isDone, isRunning, activeIndex, percent, etaText, statusLine };
  }

  function patchProcessingUi(card) {
    const panel = main.querySelector("[data-run-panel]");
    if (!panel) {
      render();
      return;
    }

    const { isDone, isRunning, activeIndex, percent, etaText, statusLine } = processingProgress(card);

    const statusEl = panel.querySelector("[data-run-status]");
    if (statusEl) statusEl.textContent = statusLine;

    const fillEl = panel.querySelector("[data-run-fill]");
    if (fillEl) fillEl.style.width = `${percent}%`;

    const pctEl = panel.querySelector("[data-run-pct]");
    if (pctEl) pctEl.textContent = `${percent}%`;

    const etaEl = panel.querySelector("[data-run-eta]");
    if (etaEl) etaEl.textContent = etaText;

    panel.querySelectorAll("[data-step-index]").forEach((el) => {
      const index = Number(el.getAttribute("data-step-index"));
      el.classList.toggle("is-done", isDone || index < activeIndex);
      el.classList.toggle("is-active", isRunning && index === activeIndex);
      const hintEl = el.querySelector(".step__hint");
      const etaStep = el.querySelector(".step__eta");
      if (hintEl) {
        if (isRunning && index === activeIndex) hintEl.textContent = "Сейчас…";
        else if (isDone || index < activeIndex) hintEl.textContent = "Готово";
        else hintEl.textContent = `~${PIPELINE[index].seconds} с · ${PIPELINE[index].hint}`;
      }
      if (etaStep) {
        etaStep.textContent =
          isDone || index < activeIndex || (isRunning && index === activeIndex)
            ? ""
            : `~${PIPELINE[index].seconds} с`;
      }
    });
  }

  function startProcessing(card) {
    if (!kitReady(card)) {
      showToast("Проверьте класс и состав документов.");
      return;
    }
    if (card.status === "processing" || state.processing.active) return;
    stopProcessingTimer();
    card.status = "processing";
    state.processing.active = true;
    state.processing.stepIndex = 0;
    state.processing.startedAt = Date.now();
    state.wizardStep = "run";
    render();

    state.processing.timer = setInterval(() => {
      state.processing.stepIndex += 1;
      if (state.processing.stepIndex >= PIPELINE.length) {
        stopProcessingTimer();
        card.status = "done";
        state.processing.startedAt = null;
        state.wizardStep = "review";
        resetReviewState(card);
        selectDefaultAttr(card);
        state.reviewFilter = "attention";
        showToast("Извлечение завершено. Требуется сверка атрибутов.");
        render();
        return;
      }
      patchProcessingUi(card);
    }, STEP_MS);
  }

  function restartProcessing(card) {
    stopProcessingTimer();
    state.processing.stepIndex = -1;
    state.processing.startedAt = null;
    if (card.status === "processing" || card.status === "done") {
      card.status = "ready";
    }
    resetReviewState(card);
    startProcessing(card);
  }

  function downloadResultsJson(card) {
    ensureReviewState(card);
    const ot = objectType(card.objectTypeCode);
    const rows = getAttrOrder(card).map((attrId) => {
      const meta = attrMeta(attrId, card.objectTypeCode);
      const status = attrStatus(card, attrId);
      return {
        eos_id: displayEosId(card.eos_id),
        class_code: ot.code,
        class_title: ot.title,
        variant: card.variant || null,
        document_priority: card.documents.map((d) => displayFileName(d.file_name)),
        attr_id: attrId,
        attr_name: meta.attr_name,
        attr_type: meta.attr_type,
        value: status.value,
        unit: status.unit,
        proposed: status.proposed,
        proposed_unit: status.proposedUnit,
        confidence: status.conf,
        edited: status.edited,
        confirmed: status.confirmed,
      };
    });
    const blob = new Blob([JSON.stringify(rows, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${displayEosId(card.eos_id)}-attributes.json`;
    a.click();
    URL.revokeObjectURL(url);
    showToast("Результат выгружен.");
  }

  function countByStatus() {
    const counts = { all: SEED.cards.length, draft: 0, ready: 0, processing: 0, done: 0, error: 0 };
    SEED.cards.forEach((c) => {
      counts[c.status] += 1;
    });
    return counts;
  }

  function filteredCards() {
    const q = state.searchQuery.trim().toLowerCase();
    let cards = SEED.cards.filter((c) => {
      if (state.statusFilter !== "all" && c.status !== state.statusFilter) return false;
      if (!q) return true;
      const ot = objectType(c.objectTypeCode);
      const hay = [c.name, c.eos_id, ot.title, c.variant || "", ...c.documents.map((d) => d.file_name)]
        .join(" ")
        .toLowerCase();
      return hay.includes(q);
    });

    cards = [...cards].sort((a, b) => {
      if (state.sortBy === "name") return a.name.localeCompare(b.name, "ru");
      if (state.sortBy === "status") return STATUS_ORDER[a.status] - STATUS_ORDER[b.status];
      if (state.sortBy === "date-asc") return a.created_at.localeCompare(b.created_at);
      return b.created_at.localeCompare(a.created_at);
    });
    return cards;
  }

  function moveDocument(card, index, direction) {
    const target = index + direction;
    if (target < 0 || target >= card.documents.length) return;
    const copy = [...card.documents];
    const [item] = copy.splice(index, 1);
    copy.splice(target, 0, item);
    card.documents = copy;
    if (card.status === "done") {
      card.status = "ready";
      showToast("Приоритет документов изменён. Требуется повторный запуск обработки.");
    }
  }

  function openCard(cardId) {
    state.view = "detail";
    state.cardId = cardId;
    const card = getCard(cardId);
    state.wizardStep = defaultWizardStep(card);
    ensureReviewState(card);
    selectDefaultAttr(card);
    state.reviewFilter = "attention";
    render();
  }

  function goBackToCards() {
    stopProcessingTimer();
    const card = state.cardId ? getCard(state.cardId) : null;
    if (card && card.status === "processing") card.status = "ready";
    state.view = "cards";
    state.cardId = null;
    render();
  }

  function renderCards() {
    const cards = filteredCards();
    const counts = countByStatus();
    const search = escapeHtml(state.searchQuery);

    const filters = ["all", "draft", "ready", "done"]
      .filter((id) => id === "all" || counts[id] > 0 || state.statusFilter === id)
      .map((id) => {
        const label = id === "all" ? "Все" : STATUS_LABEL[id];
        return `<button type="button" class="filter-chip ${state.statusFilter === id ? "is-active" : ""}" data-filter="${id}">${label}<span class="filter-chip__count">${counts[id]}</span></button>`;
      })
      .join("");

    const rows = cards
      .map((c) => {
        const ot = objectType(c.objectTypeCode);
        const variant = c.variant ? `<span class="task-row__chip">${escapeHtml(c.variant)}</span>` : "";
        return `
      <button type="button" class="task-row" data-open-card="${c.id}">
        <div class="task-row__main">
          <div class="task-row__top">
            <h2 class="task-row__title">${escapeHtml(c.name)}</h2>
            <span class="badge badge--${c.status}">${STATUS_LABEL[c.status]}</span>
          </div>
          <div class="task-row__meta">
            <span class="task-row__id">${escapeHtml(displayEosId(c.eos_id))}</span>
            <span>${escapeHtml(ot.title)}</span>
            <span>${formatDocCount(c.documents.length)}</span>
            ${variant}
            <span>${formatDate(c.created_at)}</span>
          </div>
        </div>
        <span class="task-row__chevron" aria-hidden="true">→</span>
      </button>`;
      })
      .join("");

    main.innerHTML = `
      <section class="hero">
        <div class="hero__kicker">Рабочее место эксперта</div>
        <h1>Карточки МТР</h1>
        <p>Карточки уже поступили в работу. Подтвердите класс и комплект документов, запустите извлечение и сверьте атрибуты карточки МТР.</p>
      </section>
      <div class="stats">
        <div class="stat"><div class="stat__value">${SEED.cards.length}</div><div class="stat__label">всего</div></div>
        <div class="stat"><div class="stat__value">${counts.ready + counts.draft}</div><div class="stat__label">к обработке</div></div>
        <div class="stat"><div class="stat__value">${counts.done}</div><div class="stat__label">на проверке</div></div>
      </div>
      <div class="toolbar toolbar--rich">
        <div class="toolbar__top">
          <label class="search-field">
            <span class="visually-hidden">Поиск</span>
            <input type="search" id="card-search" placeholder="Поиск по названию, коду МТР, классу…" value="${search}" />
          </label>
          <label class="sort-field">
            <span class="sort-field__label">Сортировка</span>
            <select id="card-sort">
              <option value="date-desc" ${state.sortBy === "date-desc" ? "selected" : ""}>Сначала новые</option>
              <option value="date-asc" ${state.sortBy === "date-asc" ? "selected" : ""}>Сначала старые</option>
              <option value="name" ${state.sortBy === "name" ? "selected" : ""}>По названию</option>
              <option value="status" ${state.sortBy === "status" ? "selected" : ""}>По статусу</option>
            </select>
          </label>
        </div>
        <div class="toolbar__filters">${filters}</div>
      </div>
      <div class="task-list">
        ${rows || `<div class="empty">Ничего не найдено</div>`}
      </div>
    `;

    const searchInput = document.getElementById("card-search");
    searchInput.addEventListener("input", () => {
      state.searchQuery = searchInput.value;
      const pos = searchInput.selectionStart;
      render();
      const next = document.getElementById("card-search");
      if (next) {
        next.focus();
        next.setSelectionRange(pos, pos);
      }
    });

    document.getElementById("card-sort").addEventListener("change", (e) => {
      state.sortBy = e.target.value;
      render();
    });

    main.querySelectorAll("[data-filter]").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.statusFilter = btn.getAttribute("data-filter");
        render();
      });
    });

    main.querySelectorAll("[data-open-card]").forEach((row) => {
      row.addEventListener("click", () => openCard(row.getAttribute("data-open-card")));
    });
  }

  function renderStepper(card) {
    const current = wizardIndex(state.wizardStep);
    return `
      <ol class="stepper" aria-label="Шаги карточки">
        ${WIZARD.map((step, index) => {
          const reachable = canEnterStep(card, step.id);
          let cls = "stepper__item";
          if (index === current) cls += " is-current";
          else if (index < current || (card.status === "done" && index <= current)) cls += " is-done";
          if (!reachable && index > current) cls += " is-locked";
          return `
            <li class="${cls}">
              <button type="button" class="stepper__btn" data-wizard="${step.id}" ${reachable ? "" : "disabled"}>
                <span class="stepper__num">${index + 1}</span>
                <span class="stepper__label">${escapeHtml(step.title)}</span>
              </button>
            </li>`;
        }).join("")}
      </ol>`;
  }

  function renderDetail() {
    const card = getCard(state.cardId);
    if (!card) {
      state.view = "cards";
      renderCards();
      return;
    }

    if (!canEnterStep(card, state.wizardStep)) {
      state.wizardStep = defaultWizardStep(card);
    }

    const ot = objectType(card.objectTypeCode);
    let panel = "";
    if (state.wizardStep === "kit") panel = renderKitStep(card);
    if (state.wizardStep === "run") panel = renderRunStep(card);
    if (state.wizardStep === "review") panel = renderReviewStep(card);
    if (state.wizardStep === "export") panel = renderExportStep(card);

    main.innerHTML = `
      <button type="button" class="back-link" id="back-to-cards">← К списку карточек</button>
      <div class="detail-head">
        <div>
          <h1>${escapeHtml(card.name)}</h1>
          <div class="detail-head__meta">
            <span class="badge badge--${card.status}">${STATUS_LABEL[card.status]}</span>
            <span class="task-row__id">${escapeHtml(displayEosId(card.eos_id))}</span>
            <span>${escapeHtml(ot.title)}</span>
            ${card.variant ? `<span class="scenario">${escapeHtml(card.variant)}</span>` : ""}
          </div>
        </div>
      </div>
      ${renderStepper(card)}
      <div class="panel">
        <div class="tab-panel">${panel}</div>
      </div>
    `;

    document.getElementById("back-to-cards").addEventListener("click", goBackToCards);

    main.querySelectorAll("[data-wizard]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const next = btn.getAttribute("data-wizard");
        if (!canEnterStep(card, next)) return;
        state.wizardStep = next;
        render();
      });
    });

    bindWizardActions(card);
  }

  function renderKitStep(card) {
    const selected = objectType(card.objectTypeCode);
    const ready = kitReady(card);
    const canEditPriority = card.status !== "processing";
    const attrCount = getAttrOrder(card).length;

    const files = card.documents
      .map(
        (doc, index) => `
      <li class="priority-item">
        <div class="priority-item__rank">${index + 1}</div>
        <div class="priority-item__body">
          <div class="file-list__name">${escapeHtml(displayFileName(doc.file_name))}</div>
          <div class="muted">${
            index === 0
              ? "Приоритетный источник при конфликте значений"
              : `Приоритет ${index + 1}`
          }</div>
        </div>
        <div class="priority-item__actions">
          <button type="button" class="btn btn--secondary btn--sm" data-move="-1" data-index="${index}" ${!canEditPriority || index === 0 ? "disabled" : ""} title="Выше">↑</button>
          <button type="button" class="btn btn--secondary btn--sm" data-move="1" data-index="${index}" ${!canEditPriority || index === card.documents.length - 1 ? "disabled" : ""} title="Ниже">↓</button>
          <button type="button" class="btn btn--secondary btn--sm" data-download="${escapeHtml(doc.file_name)}">Скачать</button>
        </div>
      </li>`,
      )
      .join("");

    return `
      <div class="step-intro">
        <h2 class="step-intro__title">Шаг 1 · Комплект документов</h2>
        <p class="muted">Документы уже приложены к карточке. Скачайте их при необходимости и задайте приоритет источников перед извлечением атрибутов.</p>
      </div>

      <div class="kit-summary">
        <div class="kit-summary__row">
          <span class="kit-summary__label">Код МТР</span>
          <span class="kit-summary__value mono">${escapeHtml(displayEosId(card.eos_id))}</span>
        </div>
        <div class="kit-summary__row">
          <span class="kit-summary__label">Наименование</span>
          <span class="kit-summary__value">${escapeHtml(card.name)}</span>
        </div>
        <div class="kit-summary__row kit-summary__row--control">
          <span class="kit-summary__label">Класс МТР</span>
          <div class="kit-control">
            <div class="kit-summary__value" id="field-class">${escapeHtml(selected.title)}</div>
            <div class="kit-hint">Класс уже определён для карточки · ${attrCount} атрибутов в схеме</div>
          </div>
        </div>
        <div class="kit-summary__row kit-summary__row--control">
          <span class="kit-summary__label">Исполнение</span>
          <div class="kit-control">
            <input id="field-variant" class="field-control" type="text" placeholder="Например: Исп. B" value="${escapeHtml(card.variant || "")}" />
            <div class="kit-hint">Введите идентификатор варианта исполнения изделия</div>
          </div>
        </div>
      </div>

      ${
        classReady(card)
          ? renderClassSchema(card)
          : `<div class="note">Класс «${escapeHtml(selected.title)}» есть в справочнике, но в этом демо извлечение для него недоступно.</div>`
      }

      <div class="section">
        <h3 class="section-title">Документы и приоритет</h3>
        <p class="muted">Порядок в списке задаёт приоритет источника: при расхождении значений одного атрибута в разных файлах используется документ выше.</p>
        <ul class="file-list priority-list">${files}</ul>
      </div>

      <div class="wizard-nav">
        <span class="muted">${ready ? "Комплект готов к извлечению" : "Добавьте документы к карточке"}</span>
        <button type="button" class="btn btn--primary" id="btn-to-run" ${ready ? "" : "disabled"}>Перейти к извлечению</button>
      </div>
    `;
  }

  function renderRunStep(card) {
    const canStart =
      kitReady(card) &&
      !state.processing.active &&
      (card.status === "ready" || card.status === "draft" || card.status === "error");
    const { isDone, isRunning, activeIndex, percent, etaText, statusLine } = processingProgress(card);

    const stepsHtml = PIPELINE.map((step, index) => {
      let cls = "step";
      if (isDone || index < activeIndex) cls += " is-done";
      else if (isRunning && index === activeIndex) cls += " is-active";
      const hint =
        isRunning && index === activeIndex
          ? "Сейчас…"
          : isDone || index < activeIndex
            ? "Готово"
            : `~${step.seconds} с · ${step.hint}`;
      return `
        <div class="${cls}" data-step-index="${index}">
          <div class="step__dot" aria-hidden="true"></div>
          <div class="step__body">
            <div class="step__title">${escapeHtml(step.title)}</div>
            <div class="step__hint">${escapeHtml(hint)}</div>
          </div>
          <div class="step__eta">${
            isDone || index < activeIndex || (isRunning && index === activeIndex)
              ? ""
              : `~${step.seconds} с`
          }</div>
        </div>`;
    }).join("");

    return `
      <div data-run-panel>
      <div class="step-intro">
        <h2 class="step-intro__title">Шаг 2 · Извлечение атрибутов</h2>
        <p class="muted" data-run-status>${escapeHtml(statusLine)}</p>
      </div>

      <div class="progress-meta">
        <div class="progress-meta__bar">
          <div class="progress-bar" aria-hidden="true"><div class="progress-bar__fill" data-run-fill style="width:${percent}%"></div></div>
        </div>
        <div class="progress-meta__stats">
          <span class="progress-pct" data-run-pct>${percent}%</span>
          <span class="muted" data-run-eta>${escapeHtml(etaText)}</span>
        </div>
      </div>

      <div class="steps steps--compact">${stepsHtml}</div>

      <div class="wizard-nav">
        <button type="button" class="btn btn--secondary" id="btn-back-kit" ${isRunning ? "disabled" : ""}>Вернуться к комплекту</button>
        <div class="wizard-nav__right">
          ${
            isRunning
              ? `<button type="button" class="btn btn--secondary" id="btn-stop">Прервать</button>`
              : ""
          }
          ${
            canStart
              ? `<button type="button" class="btn btn--primary" id="btn-process">Запустить извлечение</button>`
              : ""
          }
          ${
            isDone
              ? `<button type="button" class="btn btn--secondary" id="btn-restart">Запустить повторно</button>
                 <button type="button" class="btn btn--primary" id="btn-to-review">Перейти к сверке атрибутов</button>`
              : ""
          }
        </div>
      </div>
      </div>
    `;
  }

  function renderEvidenceBlock(card, attrId) {
    const evidence = getEvidence(card, attrId);
    const attrName = evidence.attr_name || attrMeta(attrId, card.objectTypeCode).attr_name;

    if (evidence.kind === "candidates" || evidence.kind === "nearest") {
      const items = (evidence.candidates || [])
        .map((c, index) =>
          renderEvidenceCard(
            c,
            evidence.kind === "nearest" ? `кандидат ${index + 1}` : `источник ${index + 1}`,
            `${card.id}:${attrId}:${index}`,
            attrName,
          ),
        )
        .join("");
      return `<div class="evidence-list">${items || `<div class="empty-inline">Ближайшие фрагменты не найдены.</div>`}</div>`;
    }

    return renderEvidenceCard(evidence, "источник", `${card.id}:${attrId}:0`, attrName);
  }

  function renderUnitSelect(meta, unit) {
    if (!meta.units || !meta.units.length) return "";
    if (meta.units.length === 1) {
      return `<span class="value-editor__unit is-fixed" title="Единица измерения">${escapeHtml(
        meta.units[0],
      )}</span>`;
    }
    const options = meta.units
      .map(
        (u) =>
          `<option value="${escapeHtml(u)}" ${u === unit ? "selected" : ""}>${escapeHtml(u)}</option>`,
      )
      .join("");
    return `<select id="review-unit-select" class="field-control value-editor__unit-select" aria-label="Единица измерения">${options}</select>`;
  }

  function renderValueEditor(meta, selected) {
    const typeHint = `<div class="value-editor__type">Тип: <strong>${escapeHtml(
      typeLabel(meta.attr_type),
    )}</strong></div>`;

    if (meta.attr_type === "enum") {
      const options = [
        `<option value="">— нет в документе —</option>`,
        ...(meta.allowed_values || []).map(
          (v) =>
            `<option value="${escapeHtml(v)}" ${selected.value === v ? "selected" : ""}>${escapeHtml(
              v,
            )}</option>`,
        ),
      ].join("");
      return `
        ${typeHint}
        <label class="value-editor__label" for="review-value-select">Значение из справочника</label>
        <div class="value-editor__row">
          <select id="review-value-select" class="field-control">${options}</select>
        </div>`;
    }

    if (meta.attr_type === "range") {
      const min = selected.value && typeof selected.value === "object" ? selected.value.min : "";
      const max = selected.value && typeof selected.value === "object" ? selected.value.max : "";
      return `
        ${typeHint}
        <label class="value-editor__label">Диапазон</label>
        <div class="value-editor__row value-editor__row--range">
          <input id="review-range-min" class="field-control" type="number" step="any" placeholder="от" value="${escapeHtml(
            min === null || min === undefined ? "" : String(min),
          )}" />
          <span class="value-editor__range-sep">…</span>
          <input id="review-range-max" class="field-control" type="number" step="any" placeholder="до" value="${escapeHtml(
            max === null || max === undefined ? "" : String(max),
          )}" />
          ${renderUnitSelect(meta, selected.unit)}
        </div>`;
    }

    if (meta.attr_type === "number") {
      return `
        ${typeHint}
        <label class="value-editor__label" for="review-value-input">Числовое значение</label>
        <div class="value-editor__row">
          <input id="review-value-input" class="field-control" type="number" step="any" value="${escapeHtml(
            selected.value === null || selected.value === undefined ? "" : String(selected.value),
          )}" placeholder="${selected.empty ? "Нет значения" : ""}" />
          ${renderUnitSelect(meta, selected.unit)}
        </div>`;
    }

    return `
      ${typeHint}
      <label class="value-editor__label" for="review-value-input">Текстовое значение</label>
      <div class="value-editor__row">
        <input id="review-value-input" class="field-control" type="text" value="${escapeHtml(
          selected.value === null || selected.value === undefined ? "" : String(selected.value),
        )}" placeholder="${selected.empty ? "Нет значения" : ""}" autocomplete="off" />
      </div>`;
  }

  function renderReviewStep(card) {
    if (card.status !== "done") {
      return `
        <div class="step-intro">
          <h2 class="step-intro__title">Шаг 3 · Сверка атрибутов</h2>
          <p class="muted">Сначала запустите извлечение на предыдущем шаге.</p>
        </div>
        <div class="wizard-nav">
          <button type="button" class="btn btn--primary" id="btn-back-run">Вернуться к извлечению</button>
        </div>
      `;
    }

    ensureReviewState(card);
    const attrOrder = getAttrOrder(card);
    if (!state.selectedAttrId || !attrOrder.includes(state.selectedAttrId)) {
      selectDefaultAttr(card);
    }

    const counts = reviewCounts(card);
    const visible = filteredReviewAttrs(card);
    const selectedId = state.selectedAttrId;
    const selectedMeta = attrMeta(selectedId, card.objectTypeCode);
    const selected = attrStatus(card, selectedId);

    const filters = [
      { id: "attention", label: "Требуют проверки", count: counts.attention },
      { id: "all", label: "Все", count: counts.total },
      { id: "edited", label: "Изменённые", count: counts.edited },
      { id: "confirmed", label: "Подтверждённые", count: counts.confirmed },
    ]
      .map(
        (f) => `
      <button type="button" class="filter-chip ${state.reviewFilter === f.id ? "is-active" : ""}" data-review-filter="${f.id}">
        ${f.label}<span class="filter-chip__count">${f.count}</span>
      </button>`,
      )
      .join("");

    const rows = visible
      .map((attrId) => {
        const meta = attrMeta(attrId, card.objectTypeCode);
        const s = attrStatus(card, attrId);
        const classes = [
          "attr-row",
          attrId === selectedId ? "is-selected" : "",
          s.needsAttention ? "is-attention" : "",
          s.confirmed ? "is-confirmed" : "",
          s.edited ? "is-edited" : "",
        ]
          .filter(Boolean)
          .join(" ");
        const statusLabel = s.confirmed
          ? "подтверждено"
          : s.edited
            ? "изменено"
            : s.empty
              ? "пусто"
              : s.conf === "lc"
                ? "проверить"
                : "предложено";
        return `
        <button type="button" class="${classes}" data-select-attr="${attrId}">
          <div class="attr-row__top">
            <span class="attr-row__name">${escapeHtml(meta.attr_name)}</span>
            <span class="conf conf--${s.conf}">${s.conf === "hc" ? "высокая" : "проверить"}</span>
          </div>
          <div class="attr-row__bottom">
            <span class="attr-row__value">${escapeHtml(formatValue(s.value, s.unit))}</span>
            <span class="attr-row__status">${statusLabel}</span>
          </div>
        </button>`;
      })
      .join("");

    const proposedSame =
      valuesEqual(selected.value, selected.proposed) &&
      (selected.unit || null) === (selected.proposedUnit || null);
    const proposedLine = proposedSame
      ? `<div class="muted">Совпадает с предложением системы</div>`
      : `<div class="review-proposed">Система предложила: <strong>${escapeHtml(
          formatValue(selected.proposed, selected.proposedUnit),
        )}</strong>
           <button type="button" class="btn btn--sm btn--secondary" id="btn-reset-value">Вернуть</button>
         </div>`;

    return `
      <div class="step-intro">
        <h2 class="step-intro__title">Шаг 3 · Сверка атрибутов</h2>
        <p class="muted">Сверьте предложенные значения атрибутов карточки МТР с фрагментами документов. Сначала разберите атрибуты с низкой уверенностью: поправьте значение с учётом типа (число, справочник, диапазон), при необходимости смените единицу измерения и подтвердите.</p>
      </div>

      <div class="summary">
        <div class="summary__item summary__item--warn">${counts.attention} требуют проверки</div>
        <div class="summary__item">${counts.confirmed}/${counts.total} подтверждено</div>
        ${counts.edited ? `<div class="summary__item summary__item--edit">${counts.edited} изменено экспертом</div>` : ""}
      </div>

      <div class="review-layout">
        <div class="review-list">
          <div class="review-filters">${filters}</div>
          <div class="attr-rows">
            ${
              rows ||
              `<div class="empty-inline">В этом фильтре атрибутов нет. Переключитесь на «Все».</div>`
            }
          </div>
          <div class="review-list__footer">
            <button type="button" class="btn btn--secondary btn--sm" id="btn-accept-hc">Подтвердить все с высокой уверенностью</button>
          </div>
        </div>

        <div class="review-detail" data-review-detail>
          <div class="review-detail__head">
            <div>
              <h3 class="review-detail__title">${escapeHtml(selectedMeta.attr_name)}</h3>
              <div class="review-detail__meta">
                <span class="conf conf--${selected.conf}">${selected.conf === "hc" ? "высокая уверенность" : "требует проверки"}</span>
                <span class="status-chip">${escapeHtml(typeLabel(selectedMeta.attr_type))}</span>
                ${selected.edited ? `<span class="status-chip status-chip--edit">изменено</span>` : ""}
                ${selected.confirmed ? `<span class="status-chip status-chip--ok">подтверждено</span>` : ""}
              </div>
            </div>
          </div>

          <div class="value-editor">
            ${renderValueEditor(selectedMeta, selected)}
            ${proposedLine}
            <div class="value-editor__actions">
              <button type="button" class="btn btn--primary btn--sm" id="btn-confirm-attr">
                ${selected.confirmed ? "Снять подтверждение" : "Подтвердить"}
              </button>
              <button type="button" class="btn btn--secondary btn--sm" id="btn-clear-attr">Очистить / нет в документе</button>
            </div>
          </div>

          <div class="evidence-panel">
            <h4 class="evidence-panel__title">Фрагмент документа</h4>
            ${renderEvidenceBlock(card, selectedId)}
          </div>
        </div>
      </div>

      <div class="wizard-nav">
        <button type="button" class="btn btn--secondary" id="btn-back-run">Вернуться к извлечению</button>
        <div class="wizard-nav__right">
          ${
            counts.attention
              ? `<span class="muted">Осталось проверить: ${counts.attention}</span>`
              : `<span class="muted">Спорные атрибуты разобраны</span>`
          }
          <button type="button" class="btn btn--primary" id="btn-to-export">К выгрузке карточки</button>
        </div>
      </div>
    `;
  }

  function renderExportStep(card) {
    if (card.status !== "done") {
      return `
        <div class="step-intro">
          <h2 class="step-intro__title">Шаг 4 · Выгрузка карточки</h2>
          <p class="muted">Выгрузка доступна после извлечения и сверки атрибутов.</p>
        </div>
        <div class="wizard-nav">
          <button type="button" class="btn btn--primary" id="btn-back-review">Вернуться к сверке</button>
        </div>
      `;
    }

    ensureReviewState(card);
    const counts = reviewCounts(card);

    return `
      <div class="step-intro">
        <h2 class="step-intro__title">Шаг 4 · Выгрузка карточки</h2>
        <p class="muted">В файл попадут значения после правок эксперта, единицы измерения, признак подтверждения и исходное предложение системы.</p>
      </div>

      <div class="export-card">
        <div>
          <div class="export-card__title">${escapeHtml(displayEosId(card.eos_id))}-attributes.json</div>
          <div class="muted">${counts.total} атрибутов · ${counts.confirmed} подтверждено · ${counts.edited} изменено</div>
        </div>
        <button type="button" class="btn btn--primary" id="btn-download-json">Выгрузить карточку</button>
      </div>

      ${
        counts.attention
          ? `<div class="note">Ещё ${counts.attention} атрибута с низкой уверенностью не подтверждены. Выгрузка доступна, но лучше вернуться к сверке.</div>`
          : `<div class="note note--info">Спорные атрибуты подтверждены или исправлены.</div>`
      }

      <div class="wizard-nav">
        <button type="button" class="btn btn--secondary" id="btn-back-review">Вернуться к сверке</button>
        <button type="button" class="btn btn--primary" id="btn-finish">Завершить</button>
      </div>
    `;
  }

  function bindWizardActions(card) {
    const variantField = document.getElementById("field-variant");
    if (variantField) {
      variantField.addEventListener("input", () => {
        card.variant = variantField.value;
      });
      variantField.addEventListener("change", () => {
        card.variant = variantField.value.trim();
        render();
      });
    }

    main.querySelectorAll("[data-download]").forEach((btn) => {
      btn.addEventListener("click", () => {
        downloadPdf(btn.getAttribute("data-download"));
      });
    });

    main.querySelectorAll("[data-move]").forEach((btn) => {
      btn.addEventListener("click", () => {
        moveDocument(card, Number(btn.getAttribute("data-index")), Number(btn.getAttribute("data-move")));
        render();
      });
    });

    const toRun = document.getElementById("btn-to-run");
    if (toRun) {
      toRun.addEventListener("click", () => {
        if (!kitReady(card)) return;
        state.wizardStep = "run";
        render();
      });
    }

    const backKit = document.getElementById("btn-back-kit");
    if (backKit) {
      backKit.addEventListener("click", () => {
        state.wizardStep = "kit";
        render();
      });
    }

    const processBtn = document.getElementById("btn-process");
    if (processBtn) {
      processBtn.addEventListener("click", () => startProcessing(card));
    }

    const stopBtn = document.getElementById("btn-stop");
    if (stopBtn) {
      stopBtn.addEventListener("click", () => abortProcessing(card));
    }

    const restartBtn = document.getElementById("btn-restart");
    if (restartBtn) {
      restartBtn.addEventListener("click", () => restartProcessing(card));
    }

    const toReview = document.getElementById("btn-to-review");
    if (toReview) {
      toReview.addEventListener("click", () => {
        state.wizardStep = "review";
        render();
      });
    }

    const backRun = document.getElementById("btn-back-run");
    if (backRun) {
      backRun.addEventListener("click", () => {
        state.wizardStep = "run";
        render();
      });
    }

    main.querySelectorAll("[data-review-filter]").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.reviewFilter = btn.getAttribute("data-review-filter");
        const visible = filteredReviewAttrs(card);
        if (visible.length && !visible.includes(state.selectedAttrId)) {
          state.selectedAttrId = visible[0];
        }
        render();
      });
    });

    main.querySelectorAll("[data-select-attr]").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.selectedAttrId = btn.getAttribute("data-select-attr");
        render();
      });
    });

    main.querySelectorAll("[data-evidence-toggle]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const key = btn.getAttribute("data-evidence-toggle");
        state.evidenceExpanded[key] = !state.evidenceExpanded[key];
        render();
      });
    });

    const syncRowPreview = (attrId) => {
      const slot = card.values[attrId];
      const row = main.querySelector(`[data-select-attr="${attrId}"]`);
      if (!row) return;
      const valueEl = row.querySelector(".attr-row__value");
      const statusEl = row.querySelector(".attr-row__status");
      if (valueEl) valueEl.textContent = formatValue(slot?.value, slot?.unit);
      if (statusEl) statusEl.textContent = "изменено";
      row.classList.add("is-edited");
      row.classList.remove("is-confirmed");
    };

    const bindUnitSelect = (attrId) => {
      const unitSelect = document.getElementById("review-unit-select");
      if (!unitSelect) return;
      unitSelect.addEventListener("change", () => {
        ensureReviewState(card);
        card.values[attrId].unit = unitSelect.value;
        markAttrDirty(card, attrId);
        syncRowPreview(attrId);
        render();
      });
    };

    const attrId = state.selectedAttrId;
    if (attrId) {
      const meta = attrMeta(attrId, card.objectTypeCode);
      bindUnitSelect(attrId);

      const enumSelect = document.getElementById("review-value-select");
      if (enumSelect) {
        enumSelect.addEventListener("change", () => {
          ensureReviewState(card);
          const raw = enumSelect.value;
          card.values[attrId].value = raw === "" ? null : raw;
          markAttrDirty(card, attrId);
          render();
        });
      }

      const valueInput = document.getElementById("review-value-input");
      if (valueInput) {
        valueInput.addEventListener("input", () => {
          ensureReviewState(card);
          if (meta.attr_type === "number") {
            card.values[attrId].value = parseNumberInput(valueInput.value);
          } else {
            const text = valueInput.value.trim();
            card.values[attrId].value = text === "" ? null : valueInput.value;
          }
          markAttrDirty(card, attrId);
          syncRowPreview(attrId);
        });
        valueInput.addEventListener("change", () => render());
      }

      const rangeMin = document.getElementById("review-range-min");
      const rangeMax = document.getElementById("review-range-max");
      if (rangeMin && rangeMax) {
        const updateRange = () => {
          ensureReviewState(card);
          const min = parseNumberInput(rangeMin.value);
          const max = parseNumberInput(rangeMax.value);
          if (min === null && max === null) card.values[attrId].value = null;
          else card.values[attrId].value = { min, max };
          markAttrDirty(card, attrId);
          syncRowPreview(attrId);
        };
        rangeMin.addEventListener("input", updateRange);
        rangeMax.addEventListener("input", updateRange);
        rangeMin.addEventListener("change", () => render());
        rangeMax.addEventListener("change", () => render());
      }
    }

    const confirmAttr = document.getElementById("btn-confirm-attr");
    if (confirmAttr) {
      confirmAttr.addEventListener("click", () => {
        ensureReviewState(card);
        const id = state.selectedAttrId;
        card.confirmed[id] = !card.confirmed[id];
        if (card.confirmed[id]) {
          const next = orderedReviewAttrs(card).find(
            (other) => other !== id && attrStatus(card, other).needsAttention,
          );
          if (next) state.selectedAttrId = next;
          showToast("Значение подтверждено.");
        }
        render();
      });
    }

    const clearAttr = document.getElementById("btn-clear-attr");
    if (clearAttr) {
      clearAttr.addEventListener("click", () => {
        ensureReviewState(card);
        const id = state.selectedAttrId;
        const meta = attrMeta(id, card.objectTypeCode);
        card.values[id] = {
          value: null,
          unit: card.values[id]?.unit ?? defaultUnit(meta),
        };
        markAttrDirty(card, id);
        showToast("Значение очищено.");
        render();
      });
    }

    const resetValue = document.getElementById("btn-reset-value");
    if (resetValue) {
      resetValue.addEventListener("click", () => {
        ensureReviewState(card);
        const id = state.selectedAttrId;
        card.values[id] = {
          value: cloneValue(card.predictions[id].value),
          unit: card.predictions[id].unit,
        };
        markAttrDirty(card, id);
        render();
      });
    }

    const acceptHc = document.getElementById("btn-accept-hc");
    if (acceptHc) {
      acceptHc.addEventListener("click", () => {
        ensureReviewState(card);
        let n = 0;
        getAttrOrder(card).forEach((id) => {
          if ((card.confidence?.[id] || "hc") === "hc") {
            card.confirmed[id] = true;
            n += 1;
          }
        });
        showToast(`Подтверждено атрибутов с высокой уверенностью: ${n}.`);
        render();
      });
    }

    const toExport = document.getElementById("btn-to-export");
    if (toExport) {
      toExport.addEventListener("click", () => {
        state.wizardStep = "export";
        render();
      });
    }

    const backReview = document.getElementById("btn-back-review");
    if (backReview) {
      backReview.addEventListener("click", () => {
        state.wizardStep = "review";
        render();
      });
    }

    const downloadJson = document.getElementById("btn-download-json");
    if (downloadJson) {
      downloadJson.addEventListener("click", () => downloadResultsJson(card));
    }

    const finish = document.getElementById("btn-finish");
    if (finish) {
      finish.addEventListener("click", () => {
        showToast("Работа по карточке завершена.");
        goBackToCards();
      });
    }
  }

  function render() {
    if (state.view === "cards") renderCards();
    else renderDetail();
  }

  render();

  const navHome = document.getElementById("nav-cards") || document.getElementById("nav-tasks");
  if (navHome) {
    navHome.addEventListener("click", goBackToCards);
  }

  document.querySelectorAll(".nav__item[disabled]").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      showToast("Раздел будет доступен в полной системе.");
    });
  });
})();
