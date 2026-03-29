"""
UI layout and theming for CitySync AI.
"""

import streamlit as st
from data.city_rules import get_available_cities


def set_page_config():
    """Sets the page configuration and injects custom CSS."""
    st.set_page_config(
        page_title="CitySync AI",
        page_icon="🏙️",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # ── Custom Premium CSS ──
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

        /* Global Font & Hide Streamlit elements */
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif !important;
        }
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* Main App Background */
        .stApp {
            background-color: #f8fafc;
            background-image: radial-gradient(#e2e8f0 1px, transparent 1px);
            background-size: 20px 20px;
        }

        /* Header bar - Ultra Premium */
        .main-header {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            padding: 2rem 2.5rem;
            border-radius: 16px;
            margin-bottom: 2rem;
            color: white;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
            position: relative;
            overflow: hidden;
            border: 1px solid rgba(255,255,255,0.1);
        }
        /* Glassmorphism flare */
        .main-header::after {
            content: '';
            position: absolute;
            top: -50%; left: -50%; width: 200%; height: 200%;
            background: radial-gradient(circle, rgba(255,255,255,0.08) 0%, transparent 60%);
            transform: translate(25%, 25%);
            pointer-events: none;
        }
        
        .main-header h1 { 
            color: white; margin: 0; font-size: 2.5rem; font-weight: 700; 
            letter-spacing: -0.025em; text-shadow: 0 2px 4px rgba(0,0,0,0.5);
        }
        .main-header p { 
            color: #94a3b8; margin: 0.5rem 0 0 0; font-size: 1.1rem; font-weight: 400; 
        }

        /* Override Streamlit Buttons */
        .stButton>button {
            background-color: #0f172a !important;
            color: white !important;
            border-radius: 8px !important;
            font-weight: 500 !important;
            border: none !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1) !important;
            transition: all 0.2s ease !important;
            padding: 0.5rem 1rem !important;
        }
        .stButton>button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1) !important;
            background-color: #1e293b !important;
        }

        /* Override File Uploader */
        .stFileUploader>div {
            background-color: white;
            border: 2px dashed #cbd5e1;
            border-radius: 12px;
            padding: 2rem 1rem;
            transition: all 0.2s ease;
        }
        .stFileUploader>div:hover {
            border-color: #3b82f6;
            background-color: #f0fdfa;
        }
        
        /* Metric Cards */
        [data-testid="stMetric"] {
            background-color: white;
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
            border: 1px solid #f1f5f9;
            transition: transform 0.2s ease;
        }
        [data-testid="stMetric"]:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        }

        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background-color: #ffffff !important;
            border-right: 1px solid #e2e8f0 !important;
            color: #0f172a !important;
        }
        [data-testid="stSidebar"] p, 
        [data-testid="stSidebar"] li, 
        [data-testid="stSidebar"] span, 
        [data-testid="stSidebar"] label {
            color: #334155 !important;
        }
        [data-testid="stSidebar"] h1, 
        [data-testid="stSidebar"] h2, 
        [data-testid="stSidebar"] h3 {
            color: #0f172a !important;
        }
        
        /* Status badges */
        .badge-pass {
            background-color: #dcfce7; color: #166534;
            padding: 4px 12px; border-radius: 9999px; font-weight: 600; font-size: 0.85rem;
            border: 1px solid #bbf7d0; box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }
        .badge-fail {
            background-color: #fee2e2; color: #991b1b;
            padding: 4px 12px; border-radius: 9999px; font-weight: 600; font-size: 0.85rem;
            border: 1px solid #fecaca; box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }
        .badge-na {
            background-color: #f1f5f9; color: #475569;
            padding: 4px 12px; border-radius: 9999px; font-weight: 600; font-size: 0.85rem;
            border: 1px solid #e2e8f0;
        }
        .badge-warn {
            background-color: #fef3c7; color: #92400e;
            padding: 4px 12px; border-radius: 9999px; font-weight: 600; font-size: 0.85rem;
            border: 1px solid #fde68a;
        }

        .badge-severity-critical {
            background-color: #ef4444; color: white;
            padding: 2px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 600;
        }
        .badge-severity-warning {
            background-color: #f59e0b; color: white;
            padding: 2px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 600;
        }
        .badge-severity-info {
            background-color: #3b82f6; color: white;
            padding: 2px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 600;
        }

        /* Custom Information Cards */
        .metric-card {
            background: white;
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
            border-left: 5px solid #3b82f6;
            margin-bottom: 1rem;
        }
        .metric-card h3 { margin: 0 0 0.5rem 0; font-size: 0.9rem; color: #64748b; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }
        .metric-card .value { font-size: 1.8rem; font-weight: 700; color: #0f172a; }

        /* Fix suggestion box */
        .fix-box {
            background: #f0fdfa;
            border-left: 4px solid #14b8a6;
            padding: 1rem 1.25rem;
            border-radius: 8px;
            margin: 0.5rem 0;
            font-size: 0.95rem;
            color: #0d9488;
            font-weight: 500;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }

        /* Code ref */
        .code-ref {
            font-size: 0.85rem;
            color: #64748b;
            font-family: monospace;
            background: #f1f5f9;
            padding: 2px 6px;
            border-radius: 4px;
        }
        
        /* Expander override */
        .streamlit-expanderHeader {
            background-color: white !important;
            border-radius: 8px;
            font-weight: 600;
        }
        
    </style>
    """, unsafe_allow_html=True)


def render_header():
    """Renders the branded application header."""
    st.markdown("""
    <div class="main-header">
        <h1>🏙️ CitySync AI</h1>
        <p>Real-Time Building Plan Compliance & Analysis Copilot</p>
    </div>
    """, unsafe_allow_html=True)


def render_sidebar() -> str:
    """
    Renders the sidebar content and returns the selected city.

    Returns:
        str: The city selected by the user.
    """
    with st.sidebar:
        st.header("⚙️ Configuration")

        cities = get_available_cities()
        selected_city = st.selectbox(
            "Select City",
            cities,
            index=0,
            help="Choose the city whose building bye-laws to check against."
        )

        st.divider()
        st.header("About")
        st.info(
            f"""
            **CitySync AI** is an automated compliance copilot
            for building floor plans.

            **Active Rule Set:** {selected_city}

            **Features:**
            - Multi-page PDF Text Extraction
            - Visual Floor Plan Analysis
            - Multi-City Rule Engine
            - Code-Grounded Compliance Checks
            - Actionable Fix Suggestions
            - PDF & CSV Report Export
            """
        )
        st.divider()
        st.caption("v1.0.0 — CitySync AI")

    return selected_city


def render_no_file_uploaded_message():
    """Renders a welcome message when no file is uploaded."""
    st.markdown("""
        <div style="text-align: center; margin-top: 4rem; margin-bottom: 3rem;">
            <h1 style="font-size: 3.5rem; font-weight: 800; color: #0f172a; margin-bottom: 1rem; letter-spacing: -0.025em; line-height: 1.1;">
                Automate Building Compliance <br/> <span style="background: linear-gradient(to right, #3b82f6, #14b8a6); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">in Seconds.</span>
            </h1>
            <p style="font-size: 1.25rem; color: #64748b; max-width: 650px; margin: 1.5rem auto 2.5rem auto; line-height: 1.6;">
                Upload a residential floor plan and instantly generate code-grounded, multi-agent compliance audits mapped dynamically to spatial architectural constraints.
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("<br/>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        <div style="background: white; border: 1px solid #e2e8f0; border-radius: 16px; padding: 2rem; text-align: center; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); height: 100%; transition: all 0.2s ease;" onmouseover="this.style.transform='translateY(-4px)';this.style.boxShadow='0 10px 15px -3px rgba(0,0,0,0.1)';" onmouseout="this.style.transform='none';this.style.boxShadow='0 4px 6px -1px rgba(0,0,0,0.05)';">
            <div style="background: #eff6ff; color: #3b82f6; width: 56px; height: 56px; border-radius: 14px; display: flex; align-items: center; justify-content: center; margin: 0 auto 1.5rem auto; font-size: 1.8rem; box-shadow: 0 4px 6px -1px rgba(59,130,246,0.1);">📄</div>
            <h4 style="color: #0f172a; margin-bottom: 0.5rem; font-weight: 700; font-size: 1.1rem;">1. Upload Floor Plan</h4>
            <p style="color: #64748b; font-size: 0.95rem; margin: 0; line-height: 1.5;">Drop a PDF blueprint. We support plans from New Delhi, Mumbai, and Bangalore.</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div style="background: white; border: 1px solid #e2e8f0; border-radius: 16px; padding: 2rem; text-align: center; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); height: 100%; transition: all 0.2s ease;" onmouseover="this.style.transform='translateY(-4px)';this.style.boxShadow='0 10px 15px -3px rgba(0,0,0,0.1)';" onmouseout="this.style.transform='none';this.style.boxShadow='0 4px 6px -1px rgba(0,0,0,0.05)';">
            <div style="background: #fdf4ff; color: #8b5cf6; width: 56px; height: 56px; border-radius: 14px; display: flex; align-items: center; justify-content: center; margin: 0 auto 1.5rem auto; font-size: 1.8rem; box-shadow: 0 4px 6px -1px rgba(139,92,246,0.1);">🧠</div>
            <h4 style="color: #0f172a; margin-bottom: 0.5rem; font-weight: 700; font-size: 1.1rem;">2. Autonomous Analysis</h4>
            <p style="color: #64748b; font-size: 0.95rem; margin: 0; line-height: 1.5;">Five GenAI Agents seamlessly extract, parse, and verify every dimension via spatial OCR.</p>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div style="background: white; border: 1px solid #e2e8f0; border-radius: 16px; padding: 2rem; text-align: center; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); height: 100%; transition: all 0.2s ease;" onmouseover="this.style.transform='translateY(-4px)';this.style.boxShadow='0 10px 15px -3px rgba(0,0,0,0.1)';" onmouseout="this.style.transform='none';this.style.boxShadow='0 4px 6px -1px rgba(0,0,0,0.05)';">
            <div style="background: #f0fdfa; color: #14b8a6; width: 56px; height: 56px; border-radius: 14px; display: flex; align-items: center; justify-content: center; margin: 0 auto 1.5rem auto; font-size: 1.8rem; box-shadow: 0 4px 6px -1px rgba(20,184,166,0.1);">✅</div>
            <h4 style="color: #0f172a; margin-bottom: 0.5rem; font-weight: 700; font-size: 1.1rem;">3. Visual & Export Ready</h4>
            <p style="color: #64748b; font-size: 0.95rem; margin: 0; line-height: 1.5;">View actionable fixes interactively overlaid on the plan, and output an enterprise PDF.</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br/>", unsafe_allow_html=True)


def render_status_badge(status: str) -> str:
    """Returns an HTML badge string for a status value."""
    badge_map = {
        "PASS": "badge-pass",
        "FAIL": "badge-fail",
        "NOT_APPLICABLE": "badge-na",
        "INSUFFICIENT_DATA": "badge-warn"
    }
    cls = badge_map.get(status, "badge-na")
    return f'<span class="{cls}">{status}</span>'


def render_severity_badge(severity: str) -> str:
    """Returns an HTML badge string for a severity value."""
    return f'<span class="badge-severity-{severity}">{severity.upper()}</span>'
