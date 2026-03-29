"""
CitySync AI — Main Application
Multi-Agent Building Plan Compliance System.
"""

import streamlit as st
import pandas as pd
import json

import ui.layout as layout
import core.vision_reader as vision_reader
import core.report_generator as report_generator
import core.floor_plan_annotator as annotator
from agents.orchestrator import Orchestrator
from agents.report_agent import ReportAgent


def main():
    layout.set_page_config()
    selected_city = layout.render_sidebar()
    layout.render_header()

    uploaded_file = st.file_uploader(
        "Upload a PDF floor plan",
        type=["pdf"],
        help="Upload a residential building floor plan PDF for compliance analysis."
    )

    if uploaded_file is None:
        layout.render_no_file_uploaded_message()
        return

    st.success(f"✅ File **{uploaded_file.name}** uploaded successfully!")

    loader_placeholder = st.empty()
    with loader_placeholder:
        st.components.v1.html(
            """
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
            body {
                margin: 0;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 150px;
                font-family: 'Inter', sans-serif;
                background: transparent;
            }
            .loader-container {
                display: flex;
                flex-direction: column;
                align-items: center;
                background: white;
                padding: 20px 40px;
                border-radius: 12px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.08);
                border: 1px solid #eef2f6;
            }
            .spinner {
                width: 40px;
                height: 40px;
                border: 4px solid #eef2f6;
                border-top: 4px solid #2a5298;
                border-radius: 50%;
                animation: spin 1s linear infinite;
                margin-bottom: 15px;
            }
            @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
            .processing-text {
                color: #1e3c72;
                font-size: 16px;
                font-weight: 600;
                margin-bottom: 5px;
            }
            .timer {
                color: #666;
                font-size: 14px;
                font-variant-numeric: tabular-nums;
            }
            </style>
            <div class="loader-container">
                <div class="spinner"></div>
                <div class="processing-text">Processing Floor Plan...</div>
                <div class="timer" id="timer">00:00</div>
            </div>
            <script>
                let seconds = 0;
                setInterval(() => {
                    seconds++;
                    const mins = String(Math.floor(seconds / 60)).padStart(2, '0');
                    const secs = String(seconds % 60).padStart(2, '0');
                    document.getElementById('timer').innerText = mins + ':' + secs;
                }, 1000);
            </script>
            """,
            height=180
        )

    # ── Run the Multi-Agent Orchestrator ─────────────────────────────
    orch = Orchestrator()
    result = orch.run(uploaded_file, city=selected_city)
    
    loader_placeholder.empty()

    image = result["image"]
    text = result["text"]
    method = result["extraction_method"]
    rooms = result["rooms"]
    compliance_results = result["results"]
    score = result["compliance_score"]
    approval = result["approval_status"]
    total_area = result["total_area"]
    cross_flags = result["cross_room_flags"]
    audit_trail = result["audit_trail"]
    status_updates = result["status_updates"]
    text_blocks = result.get("text_blocks", [])

    # ── 1. Agent Workflow Status Panel ────────────────────────────────
    st.divider()
    st.subheader("🤖 Agent Workflow")

    # Group status updates by agent
    agent_icons = {
        "orchestrator": "🎯",
        "document_agent": "📄",
        "room_agent": "🔍",
        "compliance_agent": "⚖️",
        "report_agent": "📝",
    }
    agent_names = {
        "orchestrator": "Orchestrator",
        "document_agent": "Document Agent",
        "room_agent": "Room Agent",
        "compliance_agent": "Compliance Agent",
        "report_agent": "Report Agent",
    }
    status_icons = {
        "ok": "✅",
        "retry": "🔄",
        "running": "⏳",
    }

    with st.expander("View Agent Activity Log", expanded=True):
        for update in status_updates:
            agent = update.get("agent", "unknown")
            icon = agent_icons.get(agent, "🔧")
            s_icon = status_icons.get(update.get("status", "running"), "⏳")
            name = agent_names.get(agent, agent)
            msg = update.get("message", "")

            if update.get("status") == "retry":
                st.warning(f"{icon} **{name}** — {msg}")
            elif update.get("status") == "ok":
                st.success(f"{icon} **{name}** — {msg}")
            else:
                st.info(f"{icon} **{name}** — {msg}")

    # ── 2. Approval Badge ────────────────────────────────────────────
    st.divider()
    badge_colors = {
        "APPROVED": ("#d4edda", "#155724", "✅ APPROVED"),
        "CONDITIONAL": ("#fff3cd", "#856404", "⚠️ CONDITIONAL APPROVAL"),
        "REJECTED": ("#f8d7da", "#721c24", "❌ REJECTED"),
    }
    bg, fg, label = badge_colors.get(approval, ("#e2e3e5", "#383d41", approval))
    st.markdown(
        f'<div style="background-color:{bg};color:{fg};padding:20px;border-radius:10px;'
        f'text-align:center;font-size:24px;font-weight:bold;margin:10px 0;">'
        f'{label} — {score:.0f}% Compliant</div>',
        unsafe_allow_html=True,
    )

    # ── 3. View Extracted Text ───────────────────────────────────────
    with st.expander("📄 View Extracted Raw Text", expanded=False):
        if text and len(text.strip()) > 10:
            st.caption(f"🔍 Text extracted via **{method}**.")
            st.text_area("Content", text, height=200)
        else:
            st.warning("No readable text found.")

    # ── 4. Visual Understanding ──────────────────────────────────────
    st.divider()
    st.subheader("👁️ Visual Understanding")
    if image is not None:
        st.image(image, caption="Floor Plan Preview (Page 1)", use_container_width=True)

    # ── 5. Room Data Editor ──────────────────────────────────────────
    st.divider()
    st.subheader("📝 Room Data")

    if rooms:
        st.caption(
            f"✅ **{len(rooms)} rooms** auto-detected via **{method}**. "
            "Review and correct any inaccuracies before re-running compliance."
        )
    else:
        st.warning("No rooms detected. Please enter room data manually.")
        rooms = [{"room_name": "Room 1", "width_ft": 0, "length_ft": 0}]

    # Show room confidence as a separate info section
    low_conf_rooms = [r for r in rooms if r.get("confidence", 1.0) < 0.7]
    if low_conf_rooms:
        st.warning(
            f"⚠️ {len(low_conf_rooms)} room(s) have low confidence and may need manual review: "
            + ", ".join(r["room_name"] for r in low_conf_rooms)
        )

    # Cross-room validation warnings
    for flag in cross_flags:
        st.warning(f"🏠 {flag}")

    room_data = st.data_editor(
        [{k: v for k, v in r.items() if k != "confidence"} for r in rooms],
        num_rows="dynamic",
        column_config={
            "room_name": "Room Name",
            "width_ft": st.column_config.NumberColumn("Width (ft)", min_value=0, format="%.1f"),
            "length_ft": st.column_config.NumberColumn("Length (ft)", min_value=0, format="%.1f"),
        },
        use_container_width=True,
        hide_index=True
    )

    # ── 6. Compliance Results ────────────────────────────────────────
    st.divider()
    st.subheader(f"✅ Compliance Check — {selected_city}")

    if compliance_results:
        # Dashboard Metrics
        pass_count = sum(1 for r in compliance_results if r["status"] == "PASS")
        fail_count = sum(1 for r in compliance_results if r["status"] == "FAIL")

        st.markdown("### 📊 Compliance Dashboard")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Area", f"{total_area:.1f} sq ft")
        c2.metric("Rooms Verified", len(compliance_results))
        c3.metric("Compliance Score", f"{score:.1f}%")
        c4.metric("Pass / Fail", f"{pass_count} / {fail_count}")

        st.divider()

        # Results Table
        results_df = pd.DataFrame(compliance_results)
        display_cols = ["room_name", "area_sqft", "required_area_sqft", "status", "severity", "reason"]
        display_df = results_df[display_cols].copy()
        display_df.columns = ["Room Name", "Area (sq ft)", "Required (sq ft)", "Status", "Severity", "Reason"]

        def highlight_status(val):
            colors = {
                "PASS": "background-color: #d4edda; color: #155724",
                "FAIL": "background-color: #f8d7da; color: #721c24",
                "NOT_APPLICABLE": "background-color: #e2e3e5; color: #383d41",
                "INSUFFICIENT_DATA": "background-color: #fff3cd; color: #856404"
            }
            return colors.get(val, "")

        st.dataframe(
            display_df.style.map(highlight_status, subset=["Status"]),
            use_container_width=True,
            hide_index=True
        )

        # ── 7. Reasoning Chains (per room) ───────────────────────────
        st.divider()
        st.subheader("🧠 Agent Reasoning")
        st.caption("Step-by-step reasoning from the Compliance Agent for each room.")

        for r in compliance_results:
            chain = r.get("reasoning_chain", [])
            status_emoji = "✅" if r["status"] == "PASS" else "❌" if r["status"] == "FAIL" else "⚠️"
            with st.expander(f"{status_emoji} {r['room_name']} — {r['status']}", expanded=False):
                if chain:
                    for step in chain:
                        st.markdown(f"→ {step}")
                else:
                    st.info("No reasoning chain available for this room.")

                if r.get("code_reference"):
                    st.markdown(f'📖 *{r["code_reference"]}*')
                if r.get("suggested_fix"):
                    st.markdown(f'💡 **Fix:** {r["suggested_fix"]}')

        # ── Fix Suggestions ──────────────────────────────────────────
        failing = [r for r in compliance_results if r["status"] == "FAIL"]
        if failing:
            st.markdown("### 🛠️ Suggested Fixes")
            for r in failing:
                with st.expander(f"❌ {r['room_name']}", expanded=True):
                    st.markdown(f"**Issue:** {r['reason']}")
                    if r.get("suggested_fix"):
                        st.markdown(f'<div class="fix-box">💡 {r["suggested_fix"]}</div>', unsafe_allow_html=True)
                    if r.get("code_reference"):
                        st.markdown(f'<p class="code-ref">📖 {r["code_reference"]}</p>', unsafe_allow_html=True)

        # ── Annotated Floor Plan (interactive overlay) ──────────────
        if image is not None:
            st.divider()
            st.subheader("🗺️ Annotated Floor Plan")
            annotation_data = annotator.build_annotation_data(compliance_results, image.size, text_blocks)
            html_overlay = annotator.render_interactive_overlay(image, annotation_data)
            component_height = annotator.estimate_component_height(len(compliance_results))
            st.components.v1.html(html_overlay, height=component_height, scrolling=True)

    # ── 8. Audit Trail ───────────────────────────────────────────────
    st.divider()
    st.subheader("📋 Audit Trail")
    st.caption(f"Complete decision log — {len(audit_trail)} entries from all agents.")

    with st.expander("View Full Audit Trail", expanded=False):
        for entry in audit_trail:
            agent_icon = agent_icons.get(entry.get("agent", ""), "🔧")
            agent_name = agent_names.get(entry.get("agent", ""), entry.get("agent", ""))
            st.markdown(f"**#{entry['id']}** {agent_icon} `{agent_name}` → **{entry['action']}** (conf: {entry['confidence']:.0%})")
            st.caption(f"⏰ {entry['timestamp']}")
            if entry.get("reasoning"):
                for step in entry["reasoning"]:
                    st.markdown(f"  → {step}")
            st.divider()

    # Download audit trail as JSON
    audit_json = json.dumps(audit_trail, indent=2, default=str)
    st.download_button(
        label="⬇ Download Audit Trail (JSON)",
        data=audit_json.encode("utf-8"),
        file_name=f"{selected_city.lower().replace(' ', '_')}_audit_trail.json",
        mime="application/json",
        help="Download the complete agent decision log.",
    )

    # ── 9. Export Reports ────────────────────────────────────────────
    if compliance_results:
        st.divider()
        st.subheader("📥 Export Compliance Report")

        exp_col1, exp_col2 = st.columns(2)

        # CSV Export
        with exp_col1:
            export_rows = []
            for idx, room in enumerate(compliance_results):
                r_name = room["room_name"]
                r_type = "Other"
                if "bedroom" in r_name.lower() or "guest" in r_name.lower():
                    r_type = "Bedroom"
                elif "kitchen" in r_name.lower():
                    r_type = "Kitchen"
                elif "living" in r_name.lower() or "dining" in r_name.lower():
                    r_type = "Living Room"
                elif "toilet" in r_name.lower() or "bath" in r_name.lower():
                    r_type = "Bathroom"

                w, l = room["width_ft"], room["length_ft"]
                conf = "HIGH" if (w and l and w > 0 and l > 0) else "LOW"

                export_rows.append({
                    "room_id": f"R{idx + 1}",
                    "room_name": r_name,
                    "room_type": r_type,
                    "width_ft": w,
                    "length_ft": l,
                    "area_sqft": room["area_sqft"],
                    "min_required_area_sqft": room["required_area_sqft"],
                    "status": room["status"],
                    "violation_reason": room["reason"] if room["status"] == "FAIL" else "",
                    "suggested_fix": room.get("suggested_fix", ""),
                    "code_reference": room.get("code_reference", ""),
                    "city": selected_city,
                    "confidence_level": conf,
                    "approval_status": approval,
                })

            csv_bytes = pd.DataFrame(export_rows).to_csv(index=False).encode("utf-8")
            st.download_button(
                label="⬇ Download CSV",
                data=csv_bytes,
                file_name=f"{selected_city.lower().replace(' ', '_')}_compliance_report.csv",
                mime="text/csv",
                help="Download raw compliance data as CSV.",
            )

        # PDF Export
        with exp_col2:
            report_agent = ReportAgent(orch.audit)
            pdf_bytes = report_agent.generate_pdf(
                compliance_results, selected_city, score, total_area, approval
            )
            st.download_button(
                label="⬇ Download PDF Report",
                data=pdf_bytes,
                file_name=f"{selected_city.lower().replace(' ', '_')}_compliance_report.pdf",
                mime="application/pdf",
                help="Download a professional compliance report as PDF.",
            )


if __name__ == "__main__":
    main()
