"""DriveGrowth application shell. Run: streamlit run app.py."""
import streamlit as st
from src.config import ROOT, DB_PATH, DISCLAIMER
from src.ui import html

st.set_page_config(page_title="DriveGrowth · Growth & operations", page_icon="↗", layout="wide", initial_sidebar_state="expanded")
st.html(f"<style>{(ROOT / 'assets' / 'style.css').read_text()}</style>")

if not DB_PATH.exists():
    st.title("DriveGrowth")
    st.info("Create the synthetic data and local database to open the workspace.")
    st.code("python -m src.generate_data\npython -m src.generate_experiments\npython -m src.database", language="bash")
    st.caption(DISCLAIMER)
    st.stop()

with st.sidebar:
    html('<div class="brand"><div class="brand-mark">↗</div><div class="brand-name">DriveGrowth</div></div>'
         '<div class="workspace">DRIVECO / ANALYTICS</div>')
    page = st.radio("Workspace", ["Executive overview", "Experiments"],
                    index=int(st.query_params.get("page") == "experiments"),
                    key="workspace", label_visibility="collapsed")

st.query_params["page"] = "experiments" if page == "Experiments" else "overview"
if page == "Experiments":
    from views.experiments import render_experiments
    render_experiments()
else:
    from views.overview import render_overview
    render_overview()
