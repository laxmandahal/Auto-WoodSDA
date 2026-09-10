# -*- coding: utf-8 -*-
"""
Small helpers converting between BuildingConfig's plain list/list-of-list
fields and Streamlit's `st.data_editor` (which wants a DataFrame). Applied
directly to the known, concrete schema fields (Codes/schema/building_config.py)
rather than a generic Pydantic-introspecting form renderer -- the schema is
small and stable enough that hand-mapped widgets are more predictable than a
generic layer, matching this repo's general preference for concrete code
over abstraction until a real second use case demands it.
"""

import pandas as pd
import streamlit as st


def edit_vector(label, values, key, story_labels=None, help=None):
    """List[float] -> one-column editable table, one row per entry."""
    n = len(values)
    index = story_labels if story_labels and len(story_labels) == n else [f"#{i+1}" for i in range(n)]
    df = pd.DataFrame({label: values}, index=index)
    if help:
        st.caption(help)
    edited = st.data_editor(df, key=key, use_container_width=True)
    return edited[label].tolist()


def edit_matrix(label, values, key, row_labels=None, col_labels=None, help=None):
    """Matrix (List[List[float]]) -> editable table, one row per outer index
    (typically story), one column per inner index (typically wall/panel)."""
    n_rows = len(values)
    n_cols = len(values[0]) if n_rows else 0
    index = row_labels if row_labels and len(row_labels) == n_rows else [f"row {i+1}" for i in range(n_rows)]
    columns = col_labels if col_labels and len(col_labels) == n_cols else [f"col {j+1}" for j in range(n_cols)]
    df = pd.DataFrame(values, index=index, columns=columns)
    if help:
        st.caption(help)
    edited = st.data_editor(df, key=key, use_container_width=True)
    return edited.values.tolist()


def edit_str_matrix(label, values, key, row_labels=None, col_labels=None, help=None):
    return edit_matrix(label, values, key, row_labels, col_labels, help)  # dtype is inferred; strings round-trip fine


def edit_int_matrix(label, values, key, row_labels=None, col_labels=None, help=None):
    result = edit_matrix(label, values, key, row_labels, col_labels, help)
    return [[int(v) for v in row] for row in result]


def story_labels(n_stories):
    return [f"Story {i+1}" for i in range(n_stories)]


def floor_labels(n_stories):
    return ["Ground"] + [f"Floor {i+1}" for i in range(n_stories)]
