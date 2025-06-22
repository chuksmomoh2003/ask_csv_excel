#!/usr/bin/env python
# coding: utf-8

# In[1]:


"""
Streamlit Conversational Data Analysis App
──────────────────────────────────────────
• Upload CSV/XLSX
• Build plots (incl. Clustered Bar Chart)
• Ask GPT‑4 questions; GPT can execute Python
  code on the *entire* DataFrame via function
  calling, so no row limit.
• All column names and string cells are
  converted to lowercase to avoid case issues.
"""

import streamlit as st
import pandas as pd
import openai
import matplotlib.pyplot as plt
import seaborn as sns
import io
import json
import textwrap

# ────────────────────────────────────────────────────────────────────────────────
# 1️⃣  OPENAI KEY
# ────────────────────────────────────────────────────────────────────────────────
openai.api_key = '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'

# ────────────────────────────────────────────────────────────────────────────────
# 2️⃣  MODERN CSS
# ────────────────────────────────────────────────────────────────────────────────
def local_css(css_text: str):
    st.markdown(f"<style>{css_text}</style>", unsafe_allow_html=True)

local_css("""
section[data-testid="stSidebar"] { background-color:#f0f2f6; }
section[data-testid="stSidebar"] .css-1d391kg { font-family:'Roboto'; font-size:16px; }
[data-testid="stAppViewContainer"] { background-image:linear-gradient(to right,#dfe9f3,#ffffff); }
h1 { font-family:'Roboto'; font-size:48px; color:#30336b; }
button[kind="primary"] { background-color:#30336b; color:white; border-radius:8px; font-size:18px; }
""")

# ────────────────────────────────────────────────────────────────────────────────
# 3️⃣  SESSION STATE
# ────────────────────────────────────────────────────────────────────────────────
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "df" not in st.session_state:
    st.session_state.df = None
if "dataset_context" not in st.session_state:
    st.session_state.dataset_context = ""

# ────────────────────────────────────────────────────────────────────────────────
# 4️⃣  HEADER
# ────────────────────────────────────────────────────────────────────────────────
st.title("Conversational Data Analysis App")
st.write("Upload your dataset, ask analytical questions, and build plots using the sidebar.")

# ────────────────────────────────────────────────────────────────────────────────
# 5️⃣  FILE UPLOAD
# ────────────────────────────────────────────────────────────────────────────────
uploaded_file = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx"])

if uploaded_file:
    # --------------------------------------------------------------------------
    # 5a. Read file into DataFrame
    # --------------------------------------------------------------------------
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    # --------------------------------------------------------------------------
    # 5b. Convert EVERYTHING to lowercase (column names + string cells)
    # --------------------------------------------------------------------------
    df.columns = df.columns.str.lower()
    df = df.applymap(lambda x: x.lower() if isinstance(x, str) else x)

    st.session_state.df = df

    # --------------------------------------------------------------------------
    # 5c. Build dataset context for GPT
    # --------------------------------------------------------------------------
    schema_lines = [f"{col} ({dtype})" for col, dtype in zip(df.columns, df.dtypes)]
    schema_str = ", ".join(schema_lines)
    sample_rows = df.head(5).to_dict(orient="records")
    st.session_state.dataset_context = (
        f"Dataset columns and dtypes: {schema_str}. "
        f"First 5 rows: {json.dumps(sample_rows, default=str)}"
    )

    # --------------------------------------------------------------------------
    # 5d. Preview
    # --------------------------------------------------------------------------
    st.write("### Data Preview:")
    st.dataframe(df.head())

    # --------------------------------------------------------------------------
    # 5e. PLOT BUILDER
    # --------------------------------------------------------------------------
    st.sidebar.header("🛠️ Build Your Own Plot")
    plot_type = st.sidebar.selectbox(
        "Plot type:",
        (
            "None",
            "Scatter Plot",
            "Line Plot",
            "Histogram",
            "Bar Plot",
            "Clustered Bar Chart",  # NEW
            "Correlation Heatmap",
        ),
    )

    # Dynamic UI controls
    x_axis = y_axis = column = hue_axis = None
    if plot_type in ("Scatter Plot", "Line Plot"):
        x_axis = st.sidebar.selectbox("X‑axis:", df.columns)
        y_axis = st.sidebar.selectbox("Y‑axis:", df.columns)
    elif plot_type in ("Histogram", "Bar Plot"):
        column = st.sidebar.selectbox("Column:", df.columns)
    elif plot_type == "Clustered Bar Chart":
        x_axis = st.sidebar.selectbox("X‑axis (categorical):", df.columns)
        hue_axis = st.sidebar.selectbox(
            "Hue / Cluster (categorical):",
            [col for col in df.columns if col != x_axis],
        )

    generate_plot = st.sidebar.button("Generate Plot")

    # --------------------------------------------------------------------------
    # 5f. PLOT GENERATION
    # --------------------------------------------------------------------------
    if generate_plot and plot_type != "None":
        fig, ax = plt.subplots(figsize=(8, 6))

        if plot_type == "Scatter Plot":
            sns.scatterplot(x=df[x_axis], y=df[y_axis], ax=ax)
            ax.set_title(f"{x_axis} vs {y_axis}")

        elif plot_type == "Line Plot":
            sns.lineplot(x=df[x_axis], y=df[y_axis], ax=ax)
            ax.set_title(f"{x_axis} vs {y_axis}")

        elif plot_type == "Histogram":
            data = df[column].dropna().astype(float).to_numpy()
            ax.hist(data, bins="auto", alpha=0.7)
            ax.set_title(f"Histogram of {column}")

        elif plot_type == "Bar Plot":
            df[column].value_counts().plot(kind="bar", ax=ax)
            ax.set_title(f"Bar Plot of {column}")

        elif plot_type == "Clustered Bar Chart":
            sns.countplot(data=df, x=x_axis, hue=hue_axis, ax=ax)
            ax.set_title(f"Clustered Bar Chart of {x_axis} by {hue_axis}")

        elif plot_type == "Correlation Heatmap":
            sns.heatmap(df.corr(numeric_only=True), annot=True, cmap="coolwarm", ax=ax)
            ax.set_title("Correlation Heatmap")

        st.pyplot(fig)

        # ----------------------------------------------------------------------
        # 5g. DOWNLOAD BUTTONS
        # ----------------------------------------------------------------------
        buf_png, buf_pdf, buf_svg = io.BytesIO(), io.BytesIO(), io.BytesIO()
        fig.savefig(buf_png, format="png")
        fig.savefig(buf_pdf, format="pdf")
        fig.savefig(buf_svg, format="svg")
        for buf in (buf_png, buf_pdf, buf_svg):
            buf.seek(0)

        st.write("### Download this plot:")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.download_button("📥 PNG", buf_png, file_name="plot.png", mime="image/png")
        with col2:
            st.download_button("📥 PDF", buf_pdf, file_name="plot.pdf", mime="application/pdf")
        with col3:
            st.download_button("📥 SVG", buf_svg, file_name="plot.svg", mime="image/svg+xml")

    # --------------------------------------------------------------------------
    # 5h. AI‑DRIVEN Q&A (FULL‑DATA ACCESS)
    # --------------------------------------------------------------------------
    st.write("## Ask analytical questions using AI:")
    user_query = st.text_input("Type your question here:")

    if user_query:
        # ① Add user message
        st.session_state.chat_history.append({"role": "user", "content": user_query})

        # ② Base system prompt
        base_system_prompt = (
            "You are a data analysis assistant. "
            "A pandas DataFrame named `df` containing the **entire** dataset is available. "
            "All column names and string values are lowercase. "
            "Use pandas to compute answers. NEVER hard‑code the answer; "
            "always derive it from `df`. "
            "If the answer requires inspecting data, return a JSON function call "
            "with Python code that assigns the final answer to a variable named `result`.\n\n"
            f"{st.session_state.dataset_context}"
        )

        # ③ Function schema for GPT
        functions = [
            {
                "name": "run_python",
                "description": "Execute Python code on the DataFrame `df` to compute the answer.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": (
                                "Python code that uses pandas as `pd` and the existing "
                                "DataFrame `df`. The code must set a variable `result` "
                                "to the final answer (string or numeric)."
                            ),
                        }
                    },
                    "required": ["code"],
                },
            }
        ]

        # ④ Build messages
        messages = (
            [{"role": "system", "content": base_system_prompt}]
            + st.session_state.chat_history
        )

        # ⑤ Call GPT
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",  # or any GPT‑4 variant
            messages=messages,
            functions=functions,
            function_call="auto",
            temperature=0.2,
            max_tokens=800,
        )

        choice = response.choices[0]

        # ⑥ Handle GPT output
        if choice.finish_reason == "function_call":
            # Parse JSON string inside "arguments"
            func_call = choice.message["function_call"]
            try:
                args_dict = json.loads(func_call.get("arguments", "{}"))
                code_str = args_dict.get("code", "")
            except json.JSONDecodeError:
                code_str = ""
                st.error("⚠️ Could not decode function arguments from GPT.")

            if not code_str:
                st.error("⚠️ No code received from GPT.")
            else:
                with st.expander("🔍 Generated Python code (click to view)", expanded=False):
                    st.code(textwrap.dedent(code_str), language="python")

                # Sandbox execution
                local_vars = {"df": st.session_state.df.copy(), "pd": pd}
                try:
                    exec(code_str, {}, local_vars)
                    result = local_vars.get("result", "**No `result` variable set**")
                except Exception as e:
                    result = f"⚠️ Error while executing code: {e}"

                st.write("### Chatbot:")
                st.write(result)
                st.session_state.chat_history.append(
                    {"role": "assistant", "content": str(result)}
                )

        else:
            # GPT answered directly
            reply = choice.message.content.strip()
            st.write("### Chatbot:")
            st.write(reply)
            st.session_state.chat_history.append({"role": "assistant", "content": reply})

else:
    st.info("👆 Upload a file to get started!")


# In[ ]:




