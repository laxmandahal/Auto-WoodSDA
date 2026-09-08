# -*- coding: utf-8 -*-
"""
2D plan-view and 3D wireframe rendering of a BuildingConfig's geometry, for
visual sanity-checking while editing (see plan: "there is no existing
visualization anywhere in the repo of the actual 3D wall-line/panel geometry
a researcher is defining").

Deliberately reads ONLY `config.geometry` (plain floats/ints/lists) rather
than going through `BuildingModelClass`/`openseespy_eigen.model_builders` --
those need a full df_inputs row and (for model_builders) openseespy itself to
build anything, neither of which this preview should require. Node/floor-
height arithmetic here (`np.cumsum` for floor elevations) mirrors
model_builders.py's own `floorHeights` computation for consistency, but is a
independent, dependency-free reimplementation of just the coordinate math --
not a call into that module.

Wall-line "grid lines" are inferred directly from the raw panel coordinate
matrices (each distinct Z among X-direction panels, each distinct X among
Z-direction panels) rather than from `x_wall_lines`/`y_wall_lines`' own
`name`/`geometry` fields, so this stays correct even if those lists and the
geometry matrices haven't been reconciled yet mid-edit. Wall-line names are
attached as a best-effort label only when the count of distinct coordinates
matches the count of named wall lines in the corresponding list -- otherwise
lines are labeled numerically and that's shown as an explicit mismatch
warning by the caller, not silently guessed.
"""

import numpy as np
import plotly.graph_objects as go

X_COLOR = "#1f77b4"
Z_COLOR = "#ff7f0e"
COLUMN_COLOR = "#7f7f7f"


def floor_heights(story_heights):
    return np.cumsum(np.insert(np.asarray(story_heights, dtype=float), 0, 0.0))


def _distinct_lines(coords_along, coords_fixed):
    """coords_fixed is the coordinate that's constant along one wall line
    (Z for an X-direction line, X for a Z-direction line); coords_along is the
    varying position of each panel along that line. Returns a dict
    {fixed_value: sorted list of along-values} across ALL stories (a line's
    plan position doesn't change store-to-story in every archetype examined,
    but this takes the union just in case)."""
    lines = {}
    for story_along, story_fixed in zip(coords_along, coords_fixed):
        for a, f in zip(story_along, story_fixed):
            lines.setdefault(round(f, 6), set()).add(round(a, 6))
    return {f: sorted(vals) for f, vals in sorted(lines.items())}


def wall_line_labels(distinct_fixed_values, wall_lines):
    """Best-effort name mapping -- see module docstring. Returns a list of
    labels, same length/order as `distinct_fixed_values` (already sorted).
    `wall_lines` may be a list of WallLine pydantic models OR plain dicts
    (e.g. straight out of a BuildingConfig.model_dump() -- the GUI's working
    session state is plain dicts, not live model instances)."""
    def _name(wl):
        return wl["name"] if isinstance(wl, dict) else wl.name

    names = [_name(wl) for wl in wall_lines] if wall_lines else []
    if len(names) == len(distinct_fixed_values):
        return names, True
    return [f"line {i+1}" for i in range(len(distinct_fixed_values))], False


def plan_view_figure(geometry, story_index, x_wall_lines=None, y_wall_lines=None):
    """`geometry`: the Geometry pydantic model (or anything with the same
    attributes) for the archetype being edited. `story_index`: 0-based story
    to display (panel coordinate matrices are per-story)."""
    x_max = geometry.floor_max_x_dimension[story_index]
    z_max = geometry.floor_max_z_dimension[story_index]

    fig = go.Figure()
    fig.add_shape(type="rect", x0=0, y0=0, x1=x_max, y1=z_max,
                  line=dict(color="lightgray", width=1), fillcolor="rgba(0,0,0,0)")

    x_lines = _distinct_lines(geometry.x_panel_x_coords, geometry.x_panel_z_coords)
    x_labels, x_matched = wall_line_labels(list(x_lines.keys()), x_wall_lines)
    for (z_val, x_positions), label in zip(x_lines.items(), x_labels):
        fig.add_trace(go.Scatter(
            x=[0, x_max], y=[z_val, z_val], mode="lines",
            line=dict(color=X_COLOR, width=1, dash="dot"), showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(
            x=x_positions, y=[z_val] * len(x_positions), mode="markers",
            marker=dict(color=X_COLOR, size=9, symbol="square"),
            name=f"X: {label}", legendgroup="x"))

    z_lines = _distinct_lines(geometry.z_panel_z_coords, geometry.z_panel_x_coords)
    z_labels, z_matched = wall_line_labels(list(z_lines.keys()), y_wall_lines)
    for (x_val, z_positions), label in zip(z_lines.items(), z_labels):
        fig.add_trace(go.Scatter(
            x=[x_val, x_val], y=[0, z_max], mode="lines",
            line=dict(color=Z_COLOR, width=1, dash="dot"), showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(
            x=[x_val] * len(z_positions), y=z_positions, mode="markers",
            marker=dict(color=Z_COLOR, size=9, symbol="square"),
            name=f"Z: {label}", legendgroup="z"))

    if story_index < len(geometry.leaning_column_node_x) and story_index + 1 < len(geometry.leaning_column_node_x):
        # leaning-column coordinates are per FLOOR LEVEL (n+1 rows); the columns
        # relevant to this story's plan are the ones at its top floor level.
        col_x = geometry.leaning_column_node_x[story_index + 1]
        col_z = geometry.leaning_column_node_z[story_index + 1]
        fig.add_trace(go.Scatter(
            x=col_x, y=col_z, mode="markers",
            marker=dict(color=COLUMN_COLOR, size=7, symbol="circle-open"),
            name="Leaning columns"))

    fig.update_layout(
        xaxis_title="X (in)", yaxis_title="Z (in)",
        yaxis=dict(scaleanchor="x", scaleratio=1),
        title=f"Plan view -- story {story_index + 1}",
        margin=dict(l=40, r=20, t=40, b=40), height=500,
    )
    return fig, x_matched, z_matched


def wireframe_3d_figure(geometry):
    """Full-height wireframe: leaning columns as vertical lines floor-to-floor,
    X/Z panel positions as vertical markers/lines story-to-story."""
    heights = floor_heights(geometry.story_heights)
    n_stories = geometry.number_of_stories

    fig = go.Figure()

    num_columns = len(geometry.leaning_column_node_x[0]) if geometry.leaning_column_node_x else 0
    for j in range(num_columns):
        xs = [geometry.leaning_column_node_x[i][j] for i in range(len(heights))]
        zs = [geometry.leaning_column_node_z[i][j] for i in range(len(heights))]
        fig.add_trace(go.Scatter3d(
            x=xs, y=zs, z=heights, mode="lines+markers",
            line=dict(color=COLUMN_COLOR, width=3),
            marker=dict(size=3, color=COLUMN_COLOR),
            name="Leaning column" if j == 0 else None, showlegend=(j == 0),
            legendgroup="columns",
        ))

    def _add_panels(x_coords_per_story, z_coords_per_story, color, label):
        first = True
        for i in range(n_stories):
            xs, zs = x_coords_per_story[i], z_coords_per_story[i]
            for x, z in zip(xs, zs):
                fig.add_trace(go.Scatter3d(
                    x=[x, x], y=[z, z], z=[heights[i], heights[i + 1]],
                    mode="lines", line=dict(color=color, width=4),
                    name=label if first else None, showlegend=first,
                    legendgroup=label, hoverinfo="skip",
                ))
                first = False

    _add_panels(geometry.x_panel_x_coords, geometry.x_panel_z_coords, X_COLOR, "X-direction panels")
    _add_panels(geometry.z_panel_x_coords, geometry.z_panel_z_coords, Z_COLOR, "Z-direction panels")

    fig.update_layout(
        scene=dict(
            xaxis_title="X (in)", yaxis_title="Z (in)", zaxis_title="Elevation (in)",
            aspectmode="data",
        ),
        margin=dict(l=0, r=0, t=30, b=0), height=650,
        title="3D geometry preview (wireframe -- panels & leaning columns only, no analysis)",
    )
    return fig
