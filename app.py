import streamlit as st
import pandas as pd
import os

# We use relative names so it works on the web
CSV_FILE = "portfolio.csv"

st.set_page_config(page_title="JDL Terminal", page_icon="📟")
st.title("📟 JDL Intelligence Terminal")

# A simple check to see if our 'Toy Box' is there
if os.path.exists(CSV_FILE):
    df = pd.read_csv(CSV_FILE)
    st.success("✅ Portfolio loaded successfully!")
    st.dataframe(df, use_container_width=True)
else:
    st.error("❌ portfolio.csv not found in this folder!")
    st.info("Upload a portfolio.csv to this folder to see your data.")