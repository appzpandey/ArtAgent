import streamlit as st
import pandas as pd
import re
import requests
from bs4 import BeautifulSoup
import json

# --------------------------
# CONFIGURABLE
# --------------------------
COMPANY_NAME = "Teamlease"
COMPANY_WEBSITE = "https://www.teamlease.com"
SERVICES_URL = "https://group.teamlease.com/"

LLM_PROVIDERS = {
    "Groq (Mixtral - Free)": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "model": "mixtral-8x7b-32768",
        "headers": lambda key: {"Authorization": f"Bearer {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}", "Content-Type": "application/json"}
    },
    "Together AI (Free)": {
        "url": "https://api.together.xyz/v1/chat/completions",
        "model": "mistralai/Mixtral-8x7B-Instruct-v0.1",
        "headers": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    },
    "Replicate (Free with restrictions)": {
        "url": None,
        "model": None,
        "headers": lambda key: {}
    },
    "OpenAI (GPT-3.5)": {
        "url": "https://api.openai.com/v1/chat/completions",
        "model": "gpt-3.5-turbo",
        "headers": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    }
}

# --------------------------
# Helper Functions
# --------------------------
def extract_domain(email):
    match = re.search(r'@([A-Za-z0-9.-]+)', str(email))
    return match.group(1) if match else ""

def get_services(url):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        services_list = []
        for li in soup.find_all("li"):
            text = li.get_text(strip=True)
            if any(k in text.lower() for k in ["staffing", "training", "education", "skilling", "hr"]):
                services_list.append(text)
        return list(set(services_list))[:10] or ["No services found."]
    except Exception as e:
        return [f"Error fetching services: {e}"]

def get_llm_rating(provider, api_key, services, comment, domain):
    try:
        if provider not in LLM_PROVIDERS:
            return 3  # default

        config = LLM_PROVIDERS[provider]
        if not config["url"]:
            return 3  # skip if not configured

        payload = {
            "model": config["model"],
            "messages": [{
                "role": "user",
                "content": f"""You are a lead qualification expert.

Company Services:
{', '.join(services)}

Lead Info:
Comment: {comment}
Company Domain: {domain}

Based on the relevance between the comment/company and the services, rate the lead as:
1: Highly qualified
2: Medium qualified
3: Not qualified

Return only the number (1, 2, or 3)."""
            }],
            "temperature": 0
        }

        response = requests.post(config["url"], headers=config["headers"](api_key), data=json.dumps(payload))
        rating = response.json()['choices'][0]['message']['content'].strip()
        return int(rating) if rating in ['1', '2', '3'] else 3
    except Exception as e:
        return 3  # fallback if any error

# --------------------------
# UI
# --------------------------
st.set_page_config(page_title="Lead Qualification Tool", layout="wide")
st.title("🧩 Lead Qualification Tool")

# Sidebar for LLM selection
st.sidebar.title("🤖 LLM Settings")
selected_llm = st.sidebar.selectbox("Choose LLM Provider", list(LLM_PROVIDERS.keys()))
api_key = st.sidebar.text_input(f"{selected_llm} API Key", type="password")

# Company Info
st.markdown("### 🏢 Company Info")
st.write(f"**Company Name:** {COMPANY_NAME}")
st.write(f"**Website:** [{COMPANY_WEBSITE}]({COMPANY_WEBSITE})")
services = get_services(SERVICES_URL)
st.write("**Services Provided:**")
for service in services:
    st.markdown(f"- {service}")

# File upload
st.markdown("### 📤 Upload CSV/Excel")
uploaded_file = st.file_uploader("Upload your lead file", type=["csv", "xlsx"])

if uploaded_file:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)
    df.columns = [col.strip().lower() for col in df.columns]

    expected = {
        "first & last name": "Name",
        "business email id": "Email",
        "designation": "Designation",
        "comment": "Comment",
        "others": "Others"
    }

    df = df.rename(columns={k: v for k, v in expected.items() if k in df.columns})
    if "Email" not in df.columns or "Comment" not in df.columns:
        st.error("CSV must contain 'Business email id' and 'Comment' columns.")
        st.stop()

    df["Domain"] = df["Email"].apply(extract_domain)
    st.markdown("### 📄 Extracted Data")
    st.dataframe(df)

    if api_key:
        st.markdown("### 🌟 Company Rating")
        ratings = []
        with st.spinner("Rating leads using LLM..."):
            for _, row in df.iterrows():
                rating = get_llm_rating(
                    selected_llm,
                    api_key,
                    services,
                    row.get("Comment", ""),
                    row.get("Domain", "")
                )
                ratings.append(rating)
        rating_df = df[["Name", "Email", "Domain"]].copy()
        rating_df["Rating"] = ratings
        st.dataframe(rating_df)
    else:
        st.warning("Please provide a valid API key in the sidebar to proceed with lead rating.")
