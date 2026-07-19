"""
RAG labeling: Streamlit UI. One attribute at a time, candidates from hybrid retrieval search.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st

from infra.config import get_config_and_env
from research.datasets.access import RAG_LABELS_DIR

from apps.rag_labeling.config_paths import EOS_IDS, get_class_attribute
from apps.rag_labeling.ground_truth import build_tasks, execution_variant_for_eos
from apps.rag_labeling.labels_store import (
    clear_labels,
    clear_labels_for_eos,
    load_labels,
    load_user_set,
    save_labels,
    save_user_set,
)
from apps.rag_labeling.pipeline import QDRANT_COLLECTION_TEMPLATE_RAG, ensure_indexed
from apps.rag_labeling.search import search_candidates


def _eos_key(eos_id: int) -> str:
    return str(eos_id)


def chunk_content(payload: dict) -> str:
    return payload["content"]


def saved_label_short(labels: dict, task: dict, user_set: dict | None = None) -> str:
    eos_key = _eos_key(task["eos_id"])
    attr_id = task["attr_id"]
    if user_set is not None and attr_id not in user_set.get(eos_key, set()):
        return "не размечен"
    if eos_key not in labels or attr_id not in labels[eos_key]:
        return "не размечен"
    val = labels[eos_key][attr_id]
    if val is None:
        return "нет в документе"
    return f"point {val}"


def main() -> None:
    st.set_page_config(page_title="RAG labeling", layout="wide")
    if st.session_state.get("scroll_to_top"):
        st.session_state["scroll_to_top"] = False
        try:
            st.html("<script>window.scrollTo(0,0);</script>", unsafe_allow_javascript=True)
        except Exception:
            pass
    st.title("Разметка RAG: выбор чанка по атрибуту")

    config = get_config_and_env()

    if "labels" not in st.session_state:
        st.session_state.labels = load_labels()
    if "user_set" not in st.session_state:
        raw = load_user_set()
        if raw is None:
            labels = st.session_state.labels
            raw = {}
            for eos_key, doc_labels in labels.items():
                if any(doc_labels.get(a) is not None for a in doc_labels):
                    raw[eos_key] = set(doc_labels.keys())
                else:
                    raw[eos_key] = set()
            save_user_set(raw)
        st.session_state.user_set = raw
    if "eos_id" not in st.session_state:
        st.session_state.eos_id = EOS_IDS[0] if EOS_IDS else None

    with st.sidebar:
        st.subheader("Документ")
        new_doc = st.selectbox(
            "Выберите документ",
            options=EOS_IDS,
            index=EOS_IDS.index(st.session_state.eos_id) if st.session_state.eos_id in EOS_IDS else 0,
            key="sidebar_doc",
        )
        if new_doc != st.session_state.eos_id:
            st.session_state.eos_id = new_doc
            st.session_state.tasks = build_tasks(new_doc)
            st.session_state.candidates_cache = {}
            _tasks = st.session_state.tasks
            _user_set = st.session_state.user_set.setdefault(_eos_key(new_doc), set())
            idx = 0
            for i, t in enumerate(_tasks):
                if t["attr_id"] not in _user_set:
                    idx = i
                    break
            else:
                idx = len(_tasks)
            st.session_state.task_index = idx
            st.rerun()

        _ev = execution_variant_for_eos(st.session_state.eos_id) if st.session_state.eos_id else None
        if _ev:
            st.caption(f"Вариант исполнения: {_ev}")
        st.markdown("---")
        _tasks = st.session_state.get("tasks") or (
            build_tasks(st.session_state.eos_id) if st.session_state.eos_id else []
        )
        _user_set = st.session_state.user_set.setdefault(_eos_key(st.session_state.eos_id), set())
        labeled = sum(1 for t in _tasks if t["attr_id"] in _user_set)
        total = len(_tasks)
        if total:
            st.caption(f"Размечено: {labeled} / {total}")

        st.markdown("---")
        st.subheader("Разметка заново")

        if st.session_state.get("confirm_reset_current"):
            st.warning(
                f"Сбросить разметку и переиндексировать только текущий документ "
                f"({st.session_state.eos_id})?"
            )
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Да, сбросить (текущий)", type="primary"):
                    eos_id = st.session_state.eos_id
                    if eos_id:
                        clear_labels_for_eos(eos_id)
                        st.session_state.labels = load_labels()
                        st.session_state.user_set = load_user_set() or {}
                        st.session_state.candidates_cache = {}
                        st.session_state.tasks = build_tasks(eos_id)
                        st.session_state.task_index = 0
                        for key in list(st.session_state.keys()):
                            if key.startswith("selected_") or key.startswith("custom_input_"):
                                del st.session_state[key]
                        with st.spinner("Переиндексация…"):
                            ensure_indexed(eos_id, config, force=True)
                    st.session_state.confirm_reset_current = False
                    st.session_state["scroll_to_top"] = True
                    st.rerun()
            with c2:
                if st.button("Отмена", key="btn_cancel_reset_current"):
                    st.session_state.confirm_reset_current = False
                    st.rerun()
        else:
            if st.button("Сбросить разметку (текущий документ)"):
                st.session_state.confirm_reset_current = True
                st.rerun()

        st.markdown("---")
        st.caption("Ниже — глобальный сброс (все документы).")

        if st.session_state.get("confirm_reset"):
            st.warning("Все метки будут удалены. Продолжить?")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Да, сбросить", type="primary"):
                    clear_labels()
                    st.session_state.labels = {}
                    st.session_state.user_set = {}
                    st.session_state.candidates_cache = {}
                    st.session_state.task_index = 0
                    st.session_state.confirm_reset = False
                    for key in list(st.session_state.keys()):
                        if key.startswith("selected_") or key.startswith("custom_input_"):
                            del st.session_state[key]
                    st.rerun()
            with c2:
                if st.button("Отмена"):
                    st.session_state.confirm_reset = False
                    st.rerun()
        else:
            if st.button("Сбросить разметку"):
                st.session_state.confirm_reset = True
                st.rerun()

        st.markdown("---")
        if total and labeled == total:
            if st.button("📤 Экспорт датасета", type="primary", key="export_btn_sidebar"):
                eos_export = st.session_state.eos_id
                if not eos_export:
                    st.error("Документ не выбран — экспорт не выполнен.")
                else:
                    eos_key = _eos_key(eos_export)
                    user_set = st.session_state.user_set
                    labels = st.session_state.labels
                    doc_labels = labels.setdefault(eos_key, {})
                    doc_user_set = user_set.setdefault(eos_key, set())

                    task_attr_ids = {t["attr_id"] for t in build_tasks(eos_export)}
                    all_labeled = task_attr_ids <= doc_user_set
                    has_any_non_null = any(doc_labels.get(a) is not None for a in doc_user_set)

                    if not all_labeled or not has_any_non_null:
                        st.error(
                            "Экспорт не выполнен: для этого документа не выполнены условия "
                            "(все целевые атрибуты в разметке и есть хотя бы одна не-null метка)."
                        )
                    else:
                        RAG_LABELS_DIR.mkdir(parents=True, exist_ok=True)
                        export_tasks = build_tasks(eos_export)
                        rows = [
                            {
                                "attr_id": t["attr_id"],
                                "target_point_id": doc_labels.get(t["attr_id"]),
                            }
                            for t in export_tasks
                        ]
                        out_path = RAG_LABELS_DIR / f"{eos_export}.json"
                        with open(out_path, "w", encoding="utf-8") as f:
                            json.dump(rows, f, ensure_ascii=False, indent=2)
                        st.success(f"✅ Экспортирован **{eos_export}.json** в {RAG_LABELS_DIR}")

    if "tasks" not in st.session_state:
        st.session_state.tasks = build_tasks(st.session_state.eos_id) if st.session_state.eos_id else []
    if "task_index" not in st.session_state:
        _user_set = st.session_state.user_set.setdefault(_eos_key(st.session_state.eos_id), set())
        idx = 0
        for i, t in enumerate(st.session_state.tasks):
            if t["attr_id"] not in _user_set:
                idx = i
                break
        else:
            idx = len(st.session_state.tasks)
        st.session_state.task_index = idx
    if "candidates_cache" not in st.session_state:
        st.session_state.candidates_cache = {}

    tasks = st.session_state.tasks
    task_index = st.session_state.task_index
    labels = st.session_state.labels

    if not tasks:
        st.info("Нет документов или атрибутов. Проверьте EOS_IDS и ground_truth.jsonl.")
        return

    if task_index >= len(tasks):
        st.success("✅ Все атрибуты размечены! Кнопка экспорта доступна в сайдбаре.")
        st.info("Вы можете продолжить редактировать разметку, выбрав атрибут из списка навигации ниже.")
        task_index = len(tasks) - 1

    task = tasks[task_index]
    eos_id = task["eos_id"]
    attr_id = task["attr_id"]
    eos_key = _eos_key(eos_id)

    st.markdown("**Перейти к атрибуту:**")
    nav_options = list(range(len(tasks)))
    user_set = st.session_state.user_set
    nav_labels = [
        f"{i + 1}. {tasks[i]['attr_id']} — {tasks[i]['attr_name']} — "
        f"{saved_label_short(labels, tasks[i], user_set)}"
        for i in nav_options
    ]
    new_index = st.selectbox(
        "Атрибут",
        options=nav_options,
        index=task_index,
        format_func=lambda i: nav_labels[i],
    )
    if new_index != task_index:
        st.session_state.task_index = new_index
        st.session_state["scroll_to_top"] = True
        st.rerun()

    col_prev, _, col_next = st.columns([1, 4, 1])
    with col_prev:
        if st.button("← Предыдущий", key="btn_prev_attr", disabled=(task_index == 0)):
            st.session_state.task_index = task_index - 1
            st.session_state["scroll_to_top"] = True
            st.rerun()
    with col_next:
        if st.button("Следующий →", key="btn_next_attr", disabled=(task_index >= len(tasks) - 1)):
            st.session_state.task_index = task_index + 1
            st.session_state["scroll_to_top"] = True
            st.rerun()

    st.write(f"**Атрибут {task_index + 1} из {len(tasks)}**")
    st.write(f"**{attr_id}** — {task['attr_name']}")
    if task.get("descr"):
        st.caption(f"Описание: {task['descr']}")
    _ev_main = execution_variant_for_eos(eos_id)
    if _ev_main:
        st.caption(f"Вариант исполнения: {_ev_main}")
    st.caption(
        f"Сохранено: {saved_label_short(labels, task, st.session_state.user_set)}. "
        "Выберите другой вариант и нажмите «Сохранить и следующий», чтобы изменить."
    )

    if task_index not in st.session_state.candidates_cache:
        with st.spinner("Поиск кандидатов…"):
            ensure_indexed(eos_id, config)
            attr = get_class_attribute(task["class_code"], attr_id)
            collection_name = QDRANT_COLLECTION_TEMPLATE_RAG.format(eos_id=eos_id)
            st.session_state.candidates_cache[task_index] = search_candidates(
                config,
                collection_name,
                attr,
                execution_variant=_ev_main,
                reference_value=str(task["value"]),
                limit=10,
            )
    candidates = st.session_state.candidates_cache[task_index]

    sel_key = f"selected_{task_index}"
    if sel_key not in st.session_state:
        saved = labels.get(eos_key, {}).get(attr_id)
        if saved is not None and isinstance(saved, int) and 0 <= saved < len(candidates):
            st.session_state[sel_key] = candidates[saved]["id"]
        else:
            st.session_state[sel_key] = saved

    selected_point_id = st.session_state.get(sel_key)
    candidate_ids = [c["id"] for c in candidates]

    st.progress((task_index + 1) / len(tasks), text=f"Атрибут {task_index + 1} из {len(tasks)}")
    st.success(f"**Эталон:** {task['value']}")

    st.markdown("---")
    st.markdown("**Кандидаты (выберите чанк или «Нет в документе»):**")

    for i, c in enumerate(candidates):
        content = chunk_content(c["payload"])
        meta = (c.get("payload") or {}).get("metadata") or {}
        fname = meta.get("file_name") or ""
        chunk_type = meta.get("chunk_type") or ""
        header_path = meta.get("header_path") or []
        path_label = " → ".join(header_path) if header_path else ""
        src_label = " · ".join(part for part in (chunk_type, fname, path_label) if part)
        label = f"#{i + 1} | point_id {c['id']} | score: {c['score']:.3f}" + (
            f" | {src_label}" if src_label else ""
        )
        col_exp, col_btn = st.columns([5, 1])
        with col_exp:
            if selected_point_id == c["id"]:
                st.markdown(f":green[**{label}**]")
            else:
                st.markdown(label)
            with st.expander("Показать контент", expanded=False):
                st.markdown(content)
        with col_btn:
            if st.button("Выбрать", key=f"btn_{task_index}_{i}"):
                st.session_state[sel_key] = c["id"]
                st.rerun()

    col_none, _ = st.columns([5, 1])
    with col_none:
        if st.button("Нет в документе", key=f"btn_{task_index}_none"):
            st.session_state[sel_key] = None
            st.rerun()
        if selected_point_id is None and sel_key in st.session_state:
            st.markdown(":green[**выбрано**]")

    st.markdown("---")
    st.markdown("**Или укажите point_id вручную** (если подходящего нет в топ-10):")
    custom_key = f"custom_input_{task_index}"
    default_custom = (
        selected_point_id
        if (selected_point_id is not None and selected_point_id not in candidate_ids)
        else 0
    )
    custom_val = st.number_input(
        "point_id",
        min_value=0,
        value=int(default_custom),
        step=1,
        key=custom_key,
        help="Qdrant point id в коллекции документа (0..N-1).",
    )
    if st.button("Выбрать этот чанк", key=f"btn_custom_{task_index}"):
        st.session_state[sel_key] = int(custom_val)
        st.rerun()
    if selected_point_id is not None and selected_point_id not in candidate_ids:
        st.caption(f"Выбран point_id {selected_point_id} (вне топ-10).")

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Сохранить и следующий"):
            chosen = st.session_state[sel_key]
            if eos_key not in labels:
                labels[eos_key] = {}
            labels[eos_key][attr_id] = chosen
            st.session_state.user_set.setdefault(eos_key, set()).add(attr_id)
            save_labels(labels)
            save_user_set(st.session_state.user_set)
            st.session_state.task_index = task_index + 1
            st.session_state["scroll_to_top"] = True
            st.rerun()
    with col2:
        if st.button("Пропустить атрибут"):
            if eos_key not in labels:
                labels[eos_key] = {}
            labels[eos_key][attr_id] = None
            st.session_state.user_set.setdefault(eos_key, set()).add(attr_id)
            save_labels(labels)
            save_user_set(st.session_state.user_set)
            st.session_state.task_index = task_index + 1
            st.session_state["scroll_to_top"] = True
            st.rerun()


if __name__ == "__main__":
    main()
