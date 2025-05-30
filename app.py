import streamlit as st
import pandas as pd
import re

st.title("🧩 Lead Qualification Tool")

uploaded_file = st.file_uploader("Upload your Excel or CSV file", type=["csv", "xlsx"])

def extract_domain(email):
    match = re.search(r'@([A-Za-z0-9.-]+)', str(email))
    return match.group(1) if match else ""

if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    # Basic column normalization
    df.columns = [col.strip().lower() for col in df.columns]

    # Rename expected columns
    expected = {
        "first & last name": "Name",
        "business email id": "Email",
        "designation": "Designation",
        "comment": "Comment",
        "others": "Others"
    }

    df_renamed = df.rename(columns={k: v for k, v in expected.items() if k in df.columns})

    # Extract domain
    if "Email" in df_renamed.columns:
        df_renamed["Domain"] = df_renamed["Email"].apply(extract_domain)
    else:
        st.error("Expected column 'Business email id' is missing.")
        st.stop()

    st.subheader("📄 Extracted Data")
    st.dataframe(df_renamed)
