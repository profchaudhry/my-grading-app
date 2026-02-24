import streamlit as st


def load_styles() -> None:
    st.markdown("""
        <style>
            /* Main title */
            .main-title {
                font-size: 40px;
                font-weight: 700;
                text-align: center;
                margin-top: 40px;
            }

            /* Subtitle */
            .sub-title {
                font-size: 18px;
                text-align: center;
                color: gray;
                margin-bottom: 40px;
            }

            /* Sidebar cleanup */
            section[data-testid="stSidebar"] .block-container {
                padding-top: 1rem;
            }

            /* Metric card emphasis */
            div[data-testid="metric-container"] {
                background-color: #f9f9f9;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 12px;
            }
        </style>
    """, unsafe_allow_html=True)
