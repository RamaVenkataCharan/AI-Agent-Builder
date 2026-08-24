"""
AI Agent Builder - Developer Interface
======================================
Design Rationale & Palette Justification:
- Context: High-precision autonomous developer tool (CI/CD pipeline & orchestration graph).
- Theme: Clean technical dark workspace.
  * Canvas: Deep Obsidian (#0B0F19)
  * Surface/Cards: Slate Navy (#111827)
  * Border/Dividers: Steel Gunmetal (#1F2937 / #374151)
  * Primary Accent: Cyan/Sky telemetry (#0284C7 / #38BDF8)
  * Status Pass: Clean Matrix Emerald (#10B981)
  * Status Retry/Replan: Industrial Amber (#F59E0B)
  * Status Fail: Signal Crimson (#EF4444)
  * Typography: JetBrains Mono / SF Mono / Consolas for tokens, tools & payloads; Inter / System Sans for criteria.
"""

import json
import os
import sys
import time
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).parent.parent.resolve()
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
from app.config import settings
from app.core.orchestrator import AgentOrchestrator
from app.llm.factory import get_llm_provider
from app.models.plan import EvaluationVerdictType, TaskStatus
from app.models.run_state import AgentRun, RunStatus
from app.tools.registry import default_tool_registry

st.set_page_config(
    page_title="AI Agent Builder — Autonomous Orchestration",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Design System
st.markdown(
    """
    <style>
    /* Design Tokens: Dark Technical CI Console */
    :root {
        --canvas: #0B0F19;
        --surface: #111827;
        --surface-hover: #1F2937;
        --border: #374151;
        --accent: #0284C7;
        --accent-glow: #38BDF8;
        --text-primary: #F3F4F6;
        --text-muted: #9CA3AF;
        --pass: #10B981;
        --retry: #F59E0B;
        --fail: #EF4444;
    }

    /* Base Typography & Background */
    .stApp {
        background-color: #0B0F19;
        color: #F3F4F6;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    .telemetry-bar {
        display: flex;
        align-items: center;
        gap: 16px;
        padding: 10px 16px;
        background: #111827;
        border: 1px solid #1F2937;
        border-radius: 4px;
        margin-bottom: 20px;
        font-family: 'SF Mono', 'Segoe UI Mono', 'Roboto Mono', monospace;
        font-size: 0.85rem;
    }

    .telemetry-chip {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        color: #9CA3AF;
    }

    .telemetry-value {
        color: #38BDF8;
        font-weight: 600;
    }

    /* Execution Pipeline Step Node */
    .step-node {
        background: #111827;
        border: 1px solid #1F2937;
        border-left: 4px solid #374151;
        border-radius: 4px;
        padding: 14px 18px;
        margin-bottom: 14px;
        transition: border-color 0.2s ease;
    }
    .step-node.status-completed {
        border-left-color: #10B981;
    }
    .step-node.status-running {
        border-left-color: #0284C7;
        background: #0f172a;
    }
    .step-node.status-retrying {
        border-left-color: #F59E0B;
    }
    .step-node.status-failed {
        border-left-color: #EF4444;
    }

    .step-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 6px;
    }

    .step-id {
        font-family: 'SF Mono', 'Segoe UI Mono', monospace;
        font-size: 0.8rem;
        font-weight: 600;
        color: #38BDF8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .step-title {
        font-size: 1.05rem;
        font-weight: 600;
        color: #F9FAFB;
    }

    .verdict-pill {
        display: inline-block;
        font-family: 'SF Mono', 'Segoe UI Mono', monospace;
        font-size: 0.75rem;
        font-weight: 700;
        padding: 3px 8px;
        border-radius: 3px;
        text-transform: uppercase;
    }
    .verdict-pass { background: rgba(16, 185, 129, 0.15); color: #34D399; border: 1px solid #059669; }
    .verdict-retry { background: rgba(245, 158, 11, 0.15); color: #FBBF24; border: 1px solid #D97706; }
    .verdict-fail { background: rgba(239, 68, 68, 0.15); color: #F87171; border: 1px solid #DC2626; }
    .verdict-pending { background: #1F2937; color: #9CA3AF; border: 1px solid #374151; }

    .tool-badge {
        font-family: 'SF Mono', 'Segoe UI Mono', monospace;
        font-size: 0.78rem;
        background: #1E293B;
        color: #E2E8F0;
        padding: 2px 6px;
        border-radius: 3px;
        border: 1px solid #334155;
    }

    .criteria-box {
        background: #0d131f;
        border-left: 2px solid #38BDF8;
        padding: 8px 12px;
        margin: 8px 0;
        font-size: 0.88rem;
        color: #CBD5E1;
    }

    .reasoning-text {
        font-family: 'SF Mono', 'Segoe UI Mono', monospace;
        font-size: 0.82rem;
        color: #94A3B8;
        margin: 6px 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Sidebar: System Configuration & Tool Registry
with st.sidebar:
    st.markdown("### ⚡ AI Agent Engine")
    st.caption("Plan → Execute → Evaluate → Improve Loop")

    st.markdown("#### LLM Provider")
    provider_choice = st.selectbox(
        "Active Backend",
        options=["mock", "ollama", "openai"],
        index=0 if settings.LLM_PROVIDER == "mock" else (1 if settings.LLM_PROVIDER == "ollama" else 2),
        help="Select 'mock' for instant zero-token verification, or 'ollama' / 'openai' for live inference.",
    )

    if provider_choice == "ollama":
        model_name = st.text_input("Ollama Model", value=settings.LLM_MODEL or "llama3:latest")
        endpoint = st.text_input("Ollama Base URL", value=settings.OLLAMA_BASE_URL)
    elif provider_choice == "openai":
        model_name = st.text_input("OpenAI Model", value="gpt-4o-mini")
        api_key = st.text_input("API Key", type="password", value=settings.OPENAI_API_KEY)
        endpoint = st.text_input("API Base URL", value=settings.OPENAI_BASE_URL)
    else:
        model_name = "mock-agent-v1"
        endpoint = "in-memory mock"

    st.divider()
    st.markdown("#### Pluggable Tools")
    tools = default_tool_registry.list_tools()
    for t in tools:
        with st.expander(f"`{t['name']}`", expanded=False):
            st.caption(t["description"])

    st.divider()
    st.caption(f"Workspace: `{settings.WORKSPACE_DIR}`")
    st.caption(f"Max Iterations Cap: `{settings.MAX_ITERATIONS}`")


# Header & Goal Dispatch
st.markdown("## ⚡ AI Agent Builder")
st.markdown("Autonomous multi-step execution pipeline with skeptical evaluator reflection and RAG memory.")

col_prompt, col_controls = st.columns([3, 1])

with col_prompt:
    presets = [
        "Create a python script that calculates fibonacci sequence and save it to workspace as fibonacci.py, then execute it and verify output.",
        "Build a CLI todo list manager in Python with persistent JSON storage and unit tests.",
        "Generate a data utility that calculates SHA256 hashes for files in the workspace.",
    ]
    preset_choice = st.selectbox("Load Goal Preset:", ["(Select Preset...)"] + presets)
    default_text = "" if preset_choice == "(Select Preset...)" else preset_choice

    goal_input = st.text_area(
        "Agent Goal Statement:",
        value=default_text,
        height=90,
        placeholder="State your goal in plain English (e.g. 'Create a Python script that calculates fibonacci sequence and save it to workspace')",
    )

with col_controls:
    st.write("")
    st.write("")
    max_iters = st.slider("Iteration Cap", min_value=1, max_value=15, value=settings.MAX_ITERATIONS)
    budget_usd = st.number_input("Budget Guard ($)", min_value=0.1, max_value=50.0, value=2.0, step=0.5)
    dispatch_button = st.button("▶ Dispatch Goal", type="primary", use_container_width=True)

if "active_run" not in st.session_state:
    st.session_state.active_run = None

if dispatch_button:
    if not goal_input.strip():
        st.error("Goal statement is required.")
    else:
        with st.spinner("Decomposing goal into structured plan and launching executor..."):
            llm = get_llm_provider(provider_name=provider_choice, model=model_name)
            orchestrator = AgentOrchestrator(
                llm_provider=llm,
                tool_registry=default_tool_registry,
            )

            run_result = orchestrator.run(
                goal=goal_input.strip(),
                max_iterations=max_iters,
                cost_budget_usd=budget_usd,
            )
            st.session_state.active_run = run_result

# Render Active Run
if st.session_state.active_run:
    run: AgentRun = st.session_state.active_run

    # Top Telemetry Bar
    status_label = run.status.value.upper()
    status_color = "#10B981" if run.status == RunStatus.COMPLETED else ("#EF4444" if run.status == RunStatus.FAILED else "#0284C7")

    st.markdown(
        f"""
        <div class="telemetry-bar">
            <div class="telemetry-chip">RUN ID: <span class="telemetry-value">{run.run_id}</span></div>
            <div class="telemetry-chip">STATUS: <span style="color: {status_color}; font-weight: 700;">{status_label}</span></div>
            <div class="telemetry-chip">ITERATIONS: <span class="telemetry-value">{run.current_iteration}/{run.max_iterations}</span></div>
            <div class="telemetry-chip">STEPS: <span class="telemetry-value">{len(run.step_records)}/{len(run.plan.steps) if run.plan else 0}</span></div>
            <div class="telemetry-chip">UPDATED: <span class="telemetry-value">{run.updated_at[:19]}Z</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if run.final_result:
        st.success(f"**Result**: {run.final_result}")
    elif run.error_message:
        st.error(f"**Termination Reason**: {run.error_message}")

    # Tabs for Pipeline, Tool Reasoning, Workspace, and Logs
    tab_pipeline, tab_workspace, tab_memory, tab_logs = st.tabs([
        "📊 Execution Pipeline & Verdicts",
        "📂 Workspace File Artifacts",
        "🧠 RAG Memory & Session Trace",
        "📜 System Telemetry Logs",
    ])

    with tab_pipeline:
        if run.plan:
            st.markdown(f"**Plan Strategy (v{run.plan.version})**: {run.plan.summary}")
            st.write("")

            for step in run.plan.steps:
                # Find execution record matching step
                rec = next((r for r in run.step_records if r.step_id == step.id), None)
                v_type = rec.evaluation.verdict.value if (rec and rec.evaluation) else "pending"
                pill_class = f"verdict-{v_type}"
                node_status = f"status-{step.status.value}"

                dur_str = f" • {rec.duration_seconds}s" if (rec and rec.duration_seconds) else ""
                tool_used_str = rec.tool_used if rec else (step.suggested_tool or "none")

                st.markdown(
                    f"""
                    <div class="step-node {node_status}">
                        <div class="step-header">
                            <div>
                                <span class="step-id">{step.id} (Order {step.order})</span>
                                <div class="step-title">{step.title}</div>
                            </div>
                            <div>
                                <span class="verdict-pill {pill_class}">{v_type.upper()}{dur_str}</span>
                            </div>
                        </div>
                        <div style="color: #9CA3AF; font-size: 0.9rem; margin-bottom: 6px;">{step.description}</div>
                        <div class="criteria-box">
                            <b>Acceptance Criteria:</b> {step.expected_outcome}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if rec:
                    with st.expander(f"⚙️ Step {step.order} Tool Inspection & Reason ({tool_used_str})", expanded=False):
                        st.markdown(f"**Tool Selection Rationale:** `{rec.tool_selection_reasoning or 'Direct suggestion'}`")
                        c1, c2 = st.columns(2)
                        with c1:
                            st.write("**Tool Inputs:**")
                            st.json(rec.tool_inputs or {})
                            st.write("**Tool Output / Result:**")
                            st.code(rec.tool_output or "(No output)")
                        with c2:
                            st.write("**Evaluator Reflection:**")
                            if rec.evaluation:
                                st.markdown(f"**Reason:** {rec.evaluation.reason}")
                                st.markdown(f"**Feedback:** {rec.evaluation.feedback}")
                                st.markdown(f"**Score:** `{rec.evaluation.score}`")
                                if rec.evaluation.suggested_action:
                                    st.markdown(f"**Suggested Action:** `{rec.evaluation.suggested_action}`")
                            st.write("**Memory Operations:**")
                            st.caption(f"Reads: `{rec.memory_reads}` | Writes: `{rec.memory_writes}`")

    with tab_workspace:
        st.subheader("Generated Workspace Files")
        ws = settings.workspace_path
        ws_files = list(ws.rglob("*"))
        real_files = [f for f in ws_files if f.is_file()]

        if not real_files:
            st.info("No files written to `./workspace` yet.")
        else:
            chosen = st.selectbox("Inspect File:", real_files, format_func=lambda p: str(p.relative_to(ws)))
            if chosen:
                st.caption(f"Size: {chosen.stat().st_size} bytes | Path: `{chosen}`")
                try:
                    with open(chosen, "r", encoding="utf-8", errors="replace") as f:
                        data = f.read()
                    st.code(data, language="python" if chosen.suffix == ".py" else "text")
                except Exception as e:
                    st.error(f"Failed to read file: {e}")

    with tab_memory:
        st.subheader("Session Memory Inspectability")
        mem_records = [r for r in run.step_records if r.memory_writes]
        if not mem_records:
            st.info("No memory records committed.")
        for r in mem_records:
            st.markdown(f"**Memory Document `{r.memory_writes[0]}`** (From Step `{r.step_id}`)")
            st.code(f"Step: {r.step_title}\nTool: {r.tool_used}\nOutput:\n{r.tool_output}")

    with tab_logs:
        st.subheader("Run Telemetry Stream")
        for log in run.logs:
            lvl_color = "#10B981" if log.level == "SUCCESS" else ("#EF4444" if log.level == "ERROR" else ("#F59E0B" if log.level == "WARNING" else "#6B7280"))
            st.markdown(
                f"<span style='font-family: monospace; color: #9CA3AF;'>{log.timestamp[11:19]}</span> "
                f"<span style='font-family: monospace; color: {lvl_color}; font-weight: 700;'>[{log.level}]</span> "
                f"<b>[{log.source}]</b>: {log.message}",
                unsafe_allow_html=True,
            )
