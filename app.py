import streamlit as st
import pandas as pd
import re
import requests
from bs4 import BeautifulSoup
import json

# -------------------------------
# CONFIGURATION SECTION
# -------------------------------
COMPANY_NAME = "Teamlease"
COMPANY_WEBSITE = "https://www.teamlease.com"
SERVICES_URL = "https://group.teamlease.com/"

LLM_PROVIDERS = {
    "Groq (Mixtral - Free)": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "model": "mixtral-8x7b-32768",
        "headers": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    },
    "Together AI (Mixtral - Free)": {
        "url": "https://api.together.xyz/v1/chat/completions",
        "model": "mistralai/Mixtral-8x7B-Instruct-v0.1",
        "headers": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    },
    "OpenAI (GPT-3.5)": {
        "url": "https://api.openai.com/v1/chat/completions",
        "model": "gpt-3.5-turbo",
        "headers": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    }
}

# -------------------------------
# Helper Functions
# -------------------------------
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
            if any(k in text.lower() for k in [
                "staffing", "training", "education", "skilling", "hr", "compliance", "apprenticeship", "degree"
            ]):
                services_list.append(text)
        return list(set(services_list))[:10] or ["No services found."]
    except Exception as e:
        return [f"Error fetching services: {e}"]

def get_llm_rating(provider, api_key, services, comment, domain):
    try:
        if provider not in LLM_PROVIDERS:
            return 3

        if not str(comment).strip():
            return 0

        config = LLM_PROVIDERS[provider]
        if not config["url"]:
            return 3

        prompt = f"""
You are a lead qualification expert.

### Company Services:
{', '.join(services)}

### Lead Comment:
{comment}

### Company Domain:
{domain}

Instructions:
- If the comment is empty or missing, return 0.
- If the comment does not logically or reasonably relate to the services provided, return 3.
- Count how many services are clearly matched in the comment.
- Use this rating system:
    - Rating 1: More than 50% of the services are matched
    - Rating 2: 25–50% of the services are matched
    - Rating 3: Less than 25% or irrelevant comment
    - Rating 0: Comment is missing or empty

Only return a single digit rating (0, 1, 2, or 3). Do not include any explanation.
"""

        payload = {
            "model": config["model"],
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0
        }

        response = requests.post(config["url"], headers=config["headers"](api_key), data=json.dumps(payload))
        rating = response.json()['choices'][0]['message']['content'].strip()
        return int(rating) if rating in ['0', '1', '2', '3'] else 3
    except Exception:
        return 3

# -------------------------------
# Streamlit UI
# -------------------------------
st.set_page_config(page_title="Lead Qualification Tool", layout="wide")
st.title("🎯 Lead Qualification Tool")

# Sidebar - API Key Input
st.sidebar.title("🔑 LLM Settings")
selected_llm = st.sidebar.selectbox("Choose LLM Provider", list(LLM_PROVIDERS.keys()))
api_key = st.sidebar.text_input("Enter API Key", type="password")

# Company Info Display
st.markdown("### 🏢 Company Info")
st.write(f"**Company Name:** {COMPANY_NAME}")
st.write(f"**Website:** [{COMPANY_WEBSITE}]({COMPANY_WEBSITE})")
services = get_services(SERVICES_URL)
st.write("**Services Provided:**")
for s in services:
    st.markdown(f"- {s}")

# File Upload Section
st.markdown("### 📥 Upload Lead File (CSV or Excel)")
uploaded_file = st.file_uploader("Choose a file", type=["csv", "xlsx"])

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
    df.rename(columns={k: v for k, v in expected.items() if k in df.columns}, inplace=True)

    if "Email" not in df.columns or "Comment" not in df.columns:
        st.error("Missing required columns: 'Business email id' and 'Comment'")
        st.stop()

    # Extract Domain
    df["Domain"] = df["Email"].apply(extract_domain)

    st.markdown("### 🧾 Extracted Data")
    st.dataframe(df)

    if api_key:
        st.markdown("### ⭐ Company Rating (0 = No Comment, 1 = High, 3 = Low)")
        ratings = []
        with st.spinner("Evaluating leads with LLM..."):
            for _, row in df.iterrows():
                rating = get_llm_rating(
                    selected_llm,
                    api_key,
                    services,
                    row.get("Comment", ""),
                    row.get("Domain", "")
                )
                ratings.append(rating)

        result_df = df[["Name", "Email", "Domain"]].copy()
        result_df["Rating"] = ratings
        st.dataframe(result_df)
    else:
        st.warning("🔐 Please enter a valid API key to process lead ratings.")
