import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine

# --- 1. Database Setup ---
engine = create_engine(st.secrets["NEON_URI"])

def load_data():
    try:
        query = "SELECT * FROM survey_data"
        return pd.read_sql(query, engine)
    except Exception:
        return pd.DataFrame() 

st.set_page_config(page_title="NY CEO Survey Dashboard", layout="wide")
st.title("📊 NY CEO 2025 Survey Dashboard")
st.markdown("Interactive filtering and charting for the Siena Research Institute NY CEO Survey.")

# --- 2. Admin: Secured Data Loader ---
st.sidebar.header("⚙️ Admin: Load Database")
admin_pw = st.sidebar.text_input("Admin Password", type="password")

# Check password (set ADMIN_PW in Streamlit Secrets, fallback is 'secret123')
if admin_pw == st.secrets.get("ADMIN_PW", "secret123"):
    uploaded_file = st.sidebar.file_uploader("Upload cleaned_survey_data.csv", type=["csv"])
    if uploaded_file is not None:
        if st.sidebar.button("Push to Neon DB"):
            with st.spinner("Uploading to database..."):
                new_df = pd.read_csv(uploaded_file)
                new_df.to_sql("survey_data", engine, if_exists="replace", index=False)
            st.sidebar.success("Database updated successfully!")
            st.rerun()
elif admin_pw:
    st.sidebar.error("Incorrect password.")

st.sidebar.markdown("---")

# --- 3. Main App Logic & Filters ---
df = load_data()

if df.empty:
    st.info("👋 Welcome! The database is currently empty. Please enter the admin password in the sidebar and upload the cleaned CSV to get started.")
    st.stop()

st.sidebar.header("Filter Options")

# Question Filter
questions = df['question_text'].unique()
selected_question = st.sidebar.selectbox("Select a Question", questions)

# Category Filter (Region, Industry, Time, etc.)
segment_types = df['segment_type'].unique()
selected_type = st.sidebar.selectbox("Select Demographic Category", segment_types)

# Multi-select for Side-by-Side Comparison
available_values = df[df['segment_type'] == selected_type]['segment_value'].unique()
# Default to showing the first value, but allow selecting multiple
selected_values = st.sidebar.multiselect("Select Segments to Compare", available_values, default=[available_values[0]])

# Apply filters
filtered_df = df[
    (df['question_text'] == selected_question) & 
    (df['segment_value'].isin(selected_values))
]

# --- 4. Graphing and Charting ---
st.subheader(f"{selected_question}")

if not filtered_df.empty:
    # If looking at 'Time' (2022, 2023, 2024), render a Line Chart for Trend Analysis
    if selected_type == "Time":
        # Sort values so years appear in chronological order
        trend_df = filtered_df.sort_values(by="segment_value")
        fig = px.line(
            trend_df,
            x="segment_value",
            y="percentage",
            color="response",
            markers=True,
            title="Trend Over Time",
            labels={"percentage": "Percentage (%)", "segment_value": "Year", "response": "Response"}
        )
        fig.update_layout(yaxis=dict(range=[0, 100]))
        st.plotly_chart(fig, use_container_width=True)

    # Otherwise, render a Grouped Bar Chart for demographic comparisons
    else:
        filtered_df = filtered_df.sort_values(by="percentage", ascending=True)
        fig = px.bar(
            filtered_df, 
            x="percentage", 
            y="response", 
            color="segment_value", # Color by demographic segment for comparison
            barmode="group",       # Group bars side-by-side
            orientation='h',
            text="percentage",
            title=f"Responses by {selected_type}",
            labels={"percentage": "Percentage (%)", "response": "Survey Response", "segment_value": "Segment"}
        )
        fig.update_traces(texttemplate='%{text}%', textposition='outside')
        fig.update_layout(xaxis=dict(range=[0, 100]), legend_title_text=selected_type)
        st.plotly_chart(fig, use_container_width=True)
    
    with st.expander("View Raw Data"):
        st.dataframe(filtered_df, use_container_width=True)
else:
    st.warning("No data available for this selection. Please select at least one segment to compare.")
