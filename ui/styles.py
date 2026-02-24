import streamlit as st


def load_styles() -> None:
    st.markdown("""
        <style>
            /* ── Global ── */
            html, body, [class*="css"] {
                font-family: 'Inter', 'Segoe UI', sans-serif;
            }

            /* ── Sidebar ── */
            section[data-testid="stSidebar"] {
                background-color: #1a1f2e;
            }
            section[data-testid="stSidebar"] * {
                color: #e2e8f0 !important;
            }
            section[data-testid="stSidebar"] .stRadio label {
                padding: 6px 12px;
                border-radius: 6px;
                transition: background 0.2s;
            }
            section[data-testid="stSidebar"] .stRadio label:hover {
                background-color: #2d3748;
            }
            section[data-testid="stSidebar"] hr {
                border-color: #2d3748 !important;
            }

            /* ── Page header ── */
            .main-title {
                font-size: 38px;
                font-weight: 800;
                text-align: center;
                margin-top: 30px;
                color: #1a1f2e;
                letter-spacing: -1px;
            }
            .sub-title {
                font-size: 16px;
                text-align: center;
                color: #64748b;
                margin-bottom: 30px;
            }

            /* ── Role badge ── */
            .role-badge {
                display: inline-block;
                padding: 3px 10px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            .badge-admin    { background: #fef3c7; color: #92400e; }
            .badge-faculty  { background: #dbeafe; color: #1e40af; }
            .badge-student  { background: #dcfce7; color: #166534; }

            /* ── Stat cards ── */
            div[data-testid="metric-container"] {
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                padding: 16px 20px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.06);
            }
            div[data-testid="metric-container"] label {
                color: #64748b !important;
                font-size: 13px !important;
                font-weight: 500 !important;
            }
            div[data-testid="metric-container"] [data-testid="stMetricValue"] {
                font-size: 28px !important;
                font-weight: 700 !important;
                color: #1a1f2e !important;
            }

            /* ── Tables ── */
            .dataframe {
                border-radius: 10px !important;
                overflow: hidden;
            }

            /* ── Buttons ── */
            .stButton > button {
                border-radius: 8px;
                font-weight: 500;
                transition: all 0.2s;
            }
            .stButton > button:hover {
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(0,0,0,0.12);
            }

            /* ── Forms ── */
            .stForm {
                background: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                padding: 20px;
            }

            /* ── Section header ── */
            .section-header {
                font-size: 20px;
                font-weight: 700;
                color: #1a1f2e;
                margin-bottom: 4px;
            }
            .section-sub {
                font-size: 13px;
                color: #94a3b8;
                margin-bottom: 20px;
            }

            /* ── Grade badge ── */
            .grade-a  { color: #16a34a; font-weight: 700; }
            .grade-b  { color: #2563eb; font-weight: 700; }
            .grade-c  { color: #d97706; font-weight: 700; }
            .grade-d  { color: #ea580c; font-weight: 700; }
            .grade-f  { color: #dc2626; font-weight: 700; }

            /* ── Hide streamlit branding ── */
            #MainMenu { visibility: hidden; }
            footer    { visibility: hidden; }
        </style>
    """, unsafe_allow_html=True)


def role_badge(role: str) -> str:
    return f'<span class="role-badge badge-{role}">{role}</span>'


def section_header(title: str, subtitle: str = "") -> None:
    st.markdown(f'<p class="section-header">{title}</p>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<p class="section-sub">{subtitle}</p>', unsafe_allow_html=True)
