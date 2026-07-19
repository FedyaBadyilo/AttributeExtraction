# Новая гипотеза из шаблона (GitLab Community)

На GitLab Community нет custom project templates. Новый репозиторий создаём через Git: копируем файлы шаблона локально и пушим в **пустой** проект гипотезы.

## Репозиторий-шаблон

Подставьте URL своего template-репозитория (`TEMPLATE_URL`).

| Способ | URL |
| ------ | --- |
| SSH    | `git@<GIT_HOST>:<GROUP>/hypothesis-template.git` |
| HTTPS  | `https://<GIT_HOST>/<GROUP>/hypothesis-template.git` |

## Что понадобится

- Доступ на **чтение** к шаблону
- Права на **запись** в группу, куда создаёте гипотезу
- Локально: `git`, SSH или HTTPS к своему Git-хосту

Замените в командах только:

- `TEMPLATE_URL` — URL шаблона
- `HYPOTHESIS_URL` — URL **нового** проекта
- `my-hypothesis` — имя локальной папки

## 1. Пустой проект в GitLab

**New project → Create blank project**

- Укажите группу и имя проекта
- **Снимите** «Initialize repository with a README» — репозиторий должен быть пустым

Скопируйте URL нового проекта — это `HYPOTHESIS_URL`.

## 2. Клонировать шаблон и отвязать от него

```bash
git clone --depth 1 TEMPLATE_URL my-hypothesis
cd my-hypothesis

rm -rf .git
git init
git branch -M main
git add -A
git commit -m "Initial commit from hypothesis template"
```

`--depth 1` — только последний снимок файлов, без истории шаблона.

## 3. Привязать к репозиторию гипотезы и запушить

```bash
git remote add origin HYPOTHESIS_URL
git push -u origin main
```

После push в GitLab появятся файлы и ветка `main`. Шаблон на сервере не меняется.

## 4. Настройка после создания

| Действие | Зачем |
| --- | --- |
| Обновить `README.md` | Название и описание гипотезы |
| `.env.example` → `.env` | Ключи и URL (`.env` не коммитить) |
| При необходимости — `config.yaml` | Модели и параметры под задачу |
