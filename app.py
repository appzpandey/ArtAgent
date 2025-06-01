import streamlit as st
import pandas as pd
import re
import requests
from bs4 import BeautifulSoup

# --------------------------
# CONFIGURABLE INFO
# --------------------------
COMPANY_NAME = "Teamlease"
COMPANY_WEBSITE = "https://www.teamlease.com"
SERVICES_URL = "https://group.teamlease.com/"

# --------------------------
# Function to extract domain
# --------------------------
def extract_domain(email):
    match = re.search(r'@([A-Za-z0-9.-]+)', str(email))
    return match.group(1) if match else ""

# --------------------------
# Function to extract services from website
# --------------------------
def get_services(url):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Customize this depending on actual HTML structure
        # For Teamlease's site, let's target service-related sections
        services_list = []

        for li in soup.find_all("li"):
            text = li.get_text(strip=True)
            if any(keyword in text.lower() for keyword in ["staffing", "training", "education", "skilling", "hr"]):
                services_list.append(text)

        services_list = list(set(services_list))  # Remove duplicates
        return services_list[:10] if services_list else ["No services found."]
    except Exception as e:
        return [f"Error fetching services: {str(e)}"]

# --------------------------
# STREAMLIT UI
# --------------------------
st.title("🧩 Lead Qualification Tool")

# Display company information
st.markdown("### 🏢 Company Info")
st.write(f"**Company Name:** {COMPANY_NAME}")
st.write(f"**Website:** [{COMPANY_WEBSITE}]({COMPANY_WEBSITE})")
st.write("**Services Provided:**")
for service in get_services(SERVICES_URL):
    st.markdown(f"- {service}")

# File uploader
st.markdown("### 📤 Upload CSV or Excel")
uploaded_file = st.file_uploader("Upload your file", type=["csv", "xlsx"])

# Process file
if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    # Normalize columns
    df.columns = [col.strip().lower() for col in df.columns]

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

    # Display Data
    st.markdown("### 📄 Extracted Lead Data")
    st.dataframe(df_renamed)
