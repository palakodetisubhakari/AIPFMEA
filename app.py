# -*- coding: utf-8 -*-
import os
import io
import pandas as pd
import streamlit as st
from azure.core.credentials import AzureKeyCredential
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage

# --- Azure Inference Config ---
endpoint = "https://models.github.ai/inference"
model = "openai/gpt-4"  # Updated from "openai/gpt-4.1" to "openai/gpt-4"

# Load token securely from Streamlit secrets
token = st.secrets.get("GITHUB_TOKEN", None)

if not token:
    st.error("❌ GITHUB_TOKEN not found. Please add it to your Streamlit secrets.")
    st.stop()

# --- GPT Client ---
client = ChatCompletionsClient(
    endpoint=endpoint,
    credential=AzureKeyCredential(token),
)

# --- Streamlit UI ---
st.title("🛠️ AI-Powered PFMEA Generator")
st.write("Upload previous PFMEA (optional), fill in the process details, and generate a new one.")

uploaded_file = st.file_uploader("📤 Upload Previous PFMEA Excel (optional)", type=["xlsx"])
past_context = ""

if uploaded_file:
    try:
        df_prev = pd.read_excel(uploaded_file)
        st.success("✅ Previous PFMEA uploaded.")
        past_context = df_prev.head(5).to_markdown(index=False)
    except Exception as e:
        st.warning(f"⚠️ Failed to read file: {e}")

process_name = st.text_input("🔧 Enter Process Name:")
airbag_type = st.text_input("🎈 Enter Airbag Type:")
notes = st.text_area("📝 Additional Notes (optional):")

if st.button("🚀 Generate PFMEA"):
    if not process_name or not airbag_type:
        st.warning("Please fill in both process name and airbag type.")
    else:
        base_prompt = f"""
You are a PFMEA generation assistant for automotive manufacturing.

Generate a detailed PFMEA for:
- Process: {process_name}
- Airbag Type: {airbag_type}
- Notes: {notes or "None"}

Output as a markdown table with the following columns:
| Process Step | Potential Failure Mode | Effect of Failure | Severity (1–10) | Causes | Occurrence (1–10) | Current Controls | Detection (1–10) | RPN | Recommended Actions |
"""
        if past_context:
            base_prompt += "\nHere is an example PFMEA:\n" + past_context

        with st.spinner("🧠 Generating PFMEA..."):
            try:
                response = client.complete(
                    messages=[
                        SystemMessage("You are an expert PFMEA assistant."),
                        UserMessage(base_prompt)
                    ],
                    temperature=0.5,
                    top_p=1,
                    model=model
                )

                content = response.choices[0].message.content
                st.markdown("### ✅ Generated PFMEA")
                st.markdown(content)

                # --- Parse Markdown Table to Excel ---
                lines = [line for line in content.splitlines() if "|" in line and "---" not in line]
                if len(lines) >= 2:
                    headers = [h.strip() for h in lines[0].split("|")[1:-1]]
                    rows = [[c.strip() for c in row.split("|")[1:-1]] for row in lines[1:]]
                    df_final = pd.DataFrame(rows, columns=headers)

                    output = io.BytesIO()
                    df_final.to_excel(output, index=False, sheet_name="PFMEA")
                    output.seek(0)

                    st.download_button("📥 Download PFMEA Excel",
                        data=output,
                        file_name="PFMEA_Generated.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.warning("⚠️ GPT did not return a valid markdown table.")
            except Exception as e:
                st.error(f"❌ Error generating PFMEA: {e}")
