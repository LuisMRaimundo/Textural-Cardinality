"""Gradio interface for vertical cardinality analysis."""

from __future__ import annotations

import statistics
from typing import Any

import gradio as gr
import plotly.graph_objects as go

from textural_dimension.analysis import (
    DEFAULT_BIN_CENTS,
    DEFAULT_EDO,
    TUNING_PRESETS,
    analyze_vertical_cardinality,
    write_cardinality_csv,
    write_cardinality_json,
)


def _extract_path(file_obj: Any) -> str:
    if file_obj is None:
        raise gr.Error("Please upload a score file (MusicXML / MXL / MIDI).")
    if isinstance(file_obj, str):
        return file_obj
    if hasattr(file_obj, "name") and file_obj.name:
        return str(file_obj.name)
    raise gr.Error("Invalid file input.")


def _normalize(values: list[float]) -> list[float]:
    if not values:
        return []
    vmax = max(values)
    if vmax <= 0:
        return [0.0 for _ in values]
    return [v / vmax for v in values]


def _build_plot(analysis: dict[str, Any], *, view_mode: str, pc_secondary_axis: bool):
    edo = int(analysis.get("edo", 12))
    times = [float(r["time_quarters"]) for r in analysis["series"]]
    vnc = [float(r["vertical_note_count"] or 0) for r in analysis["series"]]
    vup = [float(r["vertical_unique_pitch_count"] or 0) for r in analysis["series"]]
    vpc_raw = [
        float(r["vertical_pitch_class_cardinality"])
        if r["vertical_pitch_class_cardinality"] is not None
        else 0.0
        for r in analysis["series"]
    ]
    is_normalized = view_mode == "Normalized (0-1)"
    y1_title = "Normalized Cardinality (0-1)" if is_normalized else "Cardinality"
    y2_title = f"PC Cardinality ({edo}-EDO)" if not is_normalized else f"Normalized PC ({edo}-EDO, 0-1)"
    pc_label = f"Pitch-Class Cardinality ({edo}-EDO)"

    if is_normalized:
        vnc_plot = _normalize(vnc)
        vup_plot = _normalize(vup)
        vpc_plot = [v / float(edo) if edo > 0 else 0.0 for v in vpc_raw]
    else:
        vnc_plot = vnc
        vup_plot = vup
        vpc_plot = vpc_raw

    peak_idx = max(range(len(vnc_plot)), key=lambda i: vnc_plot[i]) if vnc_plot else 0

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=times,
            y=vnc_plot,
            mode="lines+markers",
            name="Note Count",
            line={"color": "#2E86DE", "width": 2.5},
            marker={"size": 5},
            hovertemplate="Time: %{x:.3f}<br>Note Count: %{y}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=times,
            y=vup_plot,
            mode="lines+markers",
            name="Unique Pitch Count",
            line={"color": "#10AC84", "width": 2.5},
            marker={"size": 5},
            hovertemplate="Time: %{x:.3f}<br>Unique Pitches: %{y}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=times,
            y=vpc_plot,
            mode="lines+markers",
            name=pc_label,
            line={"color": "#EE5253", "width": 2.5, "dash": "dot"},
            marker={"size": 5},
            hovertemplate=f"Time: %{{x:.3f}}<br>PC Cardinality ({edo}-EDO): %{{y}}<extra></extra>",
            yaxis="y2" if pc_secondary_axis else "y",
        )
    )
    if times:
        fig.add_trace(
            go.Scatter(
                x=[times[peak_idx]],
                y=[vnc_plot[peak_idx]],
                mode="markers+text",
                name="Peak Note Count",
                text=["Peak"],
                textposition="top center",
                marker={"color": "#1B4F72", "size": 10, "symbol": "diamond"},
                hovertemplate="Peak at t=%{x:.3f}<br>Value=%{y}<extra></extra>",
            )
        )
    fig.update_layout(
        template="plotly_white",
        title={
            "text": "Textural cardinality - Vertical Cardinality Profile",
            "x": 0.01,
            "xanchor": "left",
        },
        xaxis_title="Time (quarterLength)",
        yaxis_title=y1_title,
        yaxis2={
            "title": y2_title,
            "overlaying": "y",
            "side": "right",
            "showgrid": False,
            "visible": pc_secondary_axis,
        },
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "left",
            "x": 0,
        },
        margin={"l": 60, "r": 30, "t": 90, "b": 55},
        hovermode="x unified",
        font={"family": "Inter, Segoe UI, Arial", "size": 13},
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(0,0,0,0.07)", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(0,0,0,0.07)", zeroline=False, rangemode="tozero")
    return fig


def run_cardinality_app(
    file_obj: Any,
    time_step: float,
    tuning_preset: str,
    bin_cents: float,
    edo: int,
    auto_detect_tuning: bool,
    view_mode: str,
    pc_secondary_axis: bool,
):
    score_path = _extract_path(file_obj)
    ts = float(time_step) if time_step is not None else 0.25
    if ts <= 0:
        raise gr.Error("Time step must be > 0.")
    preset = None if tuning_preset == "(none)" else tuning_preset
    analysis = analyze_vertical_cardinality(
        score_path,
        time_step=ts,
        bin_cents=float(bin_cents) if bin_cents is not None else DEFAULT_BIN_CENTS,
        edo=int(edo) if edo is not None else DEFAULT_EDO,
        auto_detect_tuning=bool(auto_detect_tuning),
        tuning_preset=preset,
    )
    fig = _build_plot(analysis, view_mode=view_mode, pc_secondary_axis=bool(pc_secondary_axis))
    csv_path = write_cardinality_csv(analysis)
    json_path = write_cardinality_json(analysis)
    note_values = [float(r["vertical_note_count"] or 0) for r in analysis["series"]]
    unique_values = [float(r["vertical_unique_pitch_count"] or 0) for r in analysis["series"]]
    pc_values = [float(r["vertical_pitch_class_cardinality"] or 0) for r in analysis["series"]]
    summary = (
        f"File: {analysis['source_file']}\n"
        f"Duration (quarters): {analysis['duration_quarters']:.3f}\n"
        f"Time step: {analysis['time_step']}\n"
        f"EDO: {analysis.get('edo', 12)}\n"
        f"Pitch-class universe: {analysis.get('pitch_class_universe', 'Z12')}\n"
        f"Tuning provenance: {analysis.get('params', {}).get('tuning', {}).get('tuning_provenance', 'n/a')}\n"
        f"Events: {analysis.get('event_count', 'n/a')}\n"
        f"Windows: {len(analysis['series'])}\n"
        f"Note Count min/max/mean: {min(note_values):.0f}/{max(note_values):.0f}/{statistics.fmean(note_values):.2f}\n"
        f"Unique Pitch min/max/mean: {min(unique_values):.0f}/{max(unique_values):.0f}/{statistics.fmean(unique_values):.2f}\n"
        f"PC Cardinality min/max/mean: {min(pc_values):.0f}/{max(pc_values):.0f}/{statistics.fmean(pc_values):.2f}"
    )
    return fig, summary, csv_path, json_path


def build_demo() -> gr.Blocks:
    demo = gr.Blocks(title="Textural cardinality - Vertical Cardinality", theme=gr.themes.Soft())
    with demo:
        gr.Markdown("# Textural cardinality")
        gr.Markdown("Upload a MusicXML/MXL/MIDI score to compute vertical cardinality over time.")
        file_in = gr.File(label="Score file (MusicXML / MXL / MIDI)")
        with gr.Row():
            time_step_in = gr.Number(value=0.25, label="Time step (quarterLength)")
            tuning_preset_in = gr.Dropdown(
                choices=["(none)"] + sorted(TUNING_PRESETS.keys()),
                value="(none)",
                label="Tuning preset",
            )
            bin_cents_in = gr.Number(value=DEFAULT_BIN_CENTS, label="Bin size (cents)")
            edo_in = gr.Radio(
                choices=[12, 19, 24, 31, 48, 53, 72],
                value=DEFAULT_EDO,
                label="Pitch-class universe (EDO)",
            )
            auto_detect_in = gr.Checkbox(value=False, label="Auto-detect tuning from score")
            view_mode_in = gr.Radio(
                choices=["Raw Counts", "Normalized (0-1)"],
                value="Raw Counts",
                label="Display mode",
            )
            pc_axis_in = gr.Checkbox(value=True, label="Use secondary axis for PC cardinality")
        run_btn = gr.Button("Run analysis", variant="primary")
        plot_out = gr.Plot(label="Vertical cardinality plot")
        summary_out = gr.Textbox(label="Summary", lines=10)
        csv_out = gr.File(label="Download CSV")
        json_out = gr.File(label="Download JSON")
        run_btn.click(
            fn=run_cardinality_app,
            inputs=[file_in, time_step_in, tuning_preset_in, bin_cents_in, edo_in, auto_detect_in, view_mode_in, pc_axis_in],
            outputs=[plot_out, summary_out, csv_out, json_out],
        )
    return demo


def main() -> None:
    build_demo().launch(inbrowser=True)


if __name__ == "__main__":
    main()
