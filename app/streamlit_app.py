import pandas as pd
import plotly.express as px
import streamlit as st

from text_to_sql import ask, get_schema, summarize

st.set_page_config(page_title="Ask Your Data", layout="wide")


st.title("✨ Ask Your Data")
st.caption(
    "Ask questions about a fictional coffee shop chain in plain English. "
    "The app writes the SQL, runs it on the database, and explains the result."
)

EXAMPLES = [
    "Which store has the highest total revenue?",
    "Monthly revenue for 2026",
    "Top 5 best-selling products by quantity",
    "Revenue by payment method",
    "How many loyalty members signed up in each city?",   
]

CHART_COLOR = "#c8842b"


@st.cache_data
def load_schema():
    return get_schema()


def make_chart(df):
    """Draw a chart only when the result is one label column plus one number column."""
    if df.shape[1] != 2 or len(df) < 2 or len(df) > 50:
        return None
    x_col, y_col = df.columns
    if not pd.api.types.is_numeric_dtype(df[y_col]):
        return None
    if pd.api.types.is_numeric_dtype(df[x_col]):
        return None
    looks_like_date = df[x_col].astype(str).str.match(r"^\d{4}-\d{2}").all()
    if looks_like_date:
        return px.line(df, x=x_col, y=y_col, markers=True,
                       color_discrete_sequence=[CHART_COLOR])
    return px.bar(df, x=x_col, y=y_col,
                  color_discrete_sequence=[CHART_COLOR])


schema = load_schema()

# sidebar runs first so example buttons can fill the question box
with st.sidebar:
    st.header("Try an example")
    for example in EXAMPLES:
        if st.button(example):
            st.session_state["question"] = example
            st.session_state["auto_run"] = True
    st.divider()
    with st.expander("Database schema"):
        st.text(schema)

question = st.text_input(
    "Your question",
    key="question",
    placeholder="e.g. Which product category earns the most revenue?",
)
ask_clicked = st.button("Ask", type="primary")
should_run = ask_clicked or st.session_state.pop("auto_run", False)

if should_run and question.strip():
    with st.spinner("Writing and running the query..."):
        try:
            result = ask(question, schema)
            summary = None
            if not result["error"]:
                summary = summarize(question, result["columns"], result["rows"])
            st.session_state["last"] = {
                "question": question,
                "result": result,
                "summary": summary,
                "fatal": None,
            }
        except Exception as e:
            st.session_state["last"] = {
                "question": question,
                "result": None,
                "summary": None,
                "fatal": str(e),
            }

last = st.session_state.get("last")
if last:
    st.subheader(last["question"])

    if last["fatal"]:
        st.error("Something went wrong while contacting the AI service.")
        st.caption(last["fatal"])
    else:
        result = last["result"]

        if result["sql"]:
            with st.expander("Generated SQL", expanded=True):
                st.code(result["sql"], language="sql")
                st.caption(f"Attempts needed: {result['attempts']}")

        if result["error"]:
            if result["error"].startswith(("Cannot answer", "Blocked for safety")):
                st.warning(result["error"])
            else:
                st.error("I could not produce a working query for this question.")
                st.caption(result["error"])
        else:
            if last["summary"]:
                st.info(last["summary"])

            df = pd.DataFrame(result["rows"], columns=result["columns"])
            st.write(f"{len(df)} row(s)")
            st.dataframe(df)

            try:
                fig = make_chart(df)
                if fig is not None:
                    st.plotly_chart(fig)
            except Exception:
                pass  # a chart is a bonus, never a reason to crash