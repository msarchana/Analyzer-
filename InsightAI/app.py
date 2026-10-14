import logging, os, re
from pathlib import Path
from datetime import datetime
import pandas as pd
import plotly.express as px
import streamlit as st
import database as db
import auth
from analyzer import analyze_text, clean_text
from config import APP_NAME, APP_SUBTITLE, TOPICS, MAX_TEXT_CHARS, LOG_DIR, REPORT_DIR, SENTIMENT_MODEL, TOPIC_MODEL, configure_logging
from reports import make_pdf_report

Path(REPORT_DIR).mkdir(parents=True, exist_ok=True)
logger = configure_logging()
logger.info("InsightAI app startup initiated")

st.set_page_config(page_title=APP_NAME, page_icon="🧠", layout="wide", initial_sidebar_state="expanded")
db.init_db()

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
:root { --navy:#0b1224; --panel:#111d35; --cyan:#67e8f9; --violet:#a78bfa; }
.stApp { background: radial-gradient(ellipse at 15% 0%, #172747 0%, #0b1224 42%, #080d19 100%); color:#edf3ff; font-family:'DM Sans',sans-serif; }
h1,h2,h3 { font-family:'Space Grotesk',sans-serif !important; letter-spacing:-.025em; }
[data-testid="stSidebar"] { background:linear-gradient(180deg,#101a30,#0b1224); border-right:1px solid #253453; }
[data-testid="stMetric"] { background:linear-gradient(135deg,rgba(30,47,78,.92),rgba(18,29,51,.9)); border:1px solid #304362; padding:18px; border-radius:16px; }
div.stButton > button { border-radius:10px; border:1px solid #435b80; font-weight:600; transition:all .15s ease; }
div.stButton > button[kind="primary"] { background:linear-gradient(100deg,#0ea5e9,#7c3aed); border:0; color:white; }
div.stTextArea textarea, div.stTextInput input { background:#101a30; color:#edf3ff; border:1px solid #304362; border-radius:10px; }
[data-testid="stDataFrame"], [data-testid="stTable"] { border:1px solid #304362; border-radius:12px; overflow:hidden; }
.insight-hero { padding:26px 28px; border:1px solid #304362; border-radius:20px; background:linear-gradient(120deg,rgba(21,42,73,.96),rgba(37,26,76,.75)); margin-bottom:20px; }
.insight-eyebrow { color:#67e8f9; font-size:.78rem; font-weight:700; letter-spacing:.16em; text-transform:uppercase; }
.insight-sub { color:#b7c4dc; font-size:1rem; }
.pill { display:inline-block; border:1px solid #40577a; border-radius:999px; padding:4px 10px; margin:3px; color:#dbeafe; background:#172640; font-size:.85rem; }
.small-muted { color:#a9b9d4; font-size:.86rem; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

def audit(event, status="INFO", details=""):
    user = st.session_state.get("user")
    try:
        db.log_event(user["id"] if user else None, user["username"] if user else "system", event, status, details)
    except Exception:
        logger.exception("Could not save audit event: %s", event)

def header(title, subtitle=""):
    st.markdown(f'<div class="insight-hero"><div class="insight-eyebrow">InsightAI · NLP Intelligence</div><h1 style="margin:.4rem 0">{title}</h1><div class="insight-sub">{subtitle}</div></div>', unsafe_allow_html=True)

def logo():
    st.markdown('<div style="display:flex;align-items:center;gap:10px;padding:8px 0 20px"><div style="font-size:2rem">🧠</div><div><div style="font-family:Space Grotesk;font-size:1.5rem;font-weight:700">Insight<span style="color:#67e8f9">AI</span></div><div class="small-muted">Text intelligence platform</div></div></div>', unsafe_allow_html=True)

def login_screen():
    logo()
    header("Understand text beyond words", "Analyze sentiment, discover topics, and turn unstructured text into useful insights.")
    left, right = st.columns([1.05, 1], gap="large")
    with left:
        st.subheader("What you can do")
        for title, desc in [
            ("🧭 Context insights", "Sentiment, topic confidence, keywords and readable summaries."),
            ("📊 Analytics dashboard", "Explore your analysis history and compare results."),
            ("🛡️ Secure workspace", "Personal history, role-based admin controls and audit logs."),
        ]:
            st.markdown(f"**{title}**")
            st.caption(desc)
        st.info("AI results are estimates. Review important decisions independently.")
    with right:
        tab_login, tab_register = st.tabs(["Sign in", "Create account"])
        with tab_login:
            with st.form("login_form"):
                login_value = st.text_input("Username or email", key="login_id")
                password = st.text_input("Password", type="password", key="login_password")
                submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)
            if submitted:
                user, message = auth.login(login_value, password)
                if user:
                    st.session_state.user = user
                    st.session_state.pop("last_result", None)
                    st.rerun()
                st.error(message)
        with tab_register:
            with st.form("register_form"):
                username = st.text_input("Username", key="reg_username")
                email = st.text_input("Email address", key="reg_email")
                new_password = st.text_input("Password (10+ characters)", type="password", key="reg_password")
                confirm = st.text_input("Confirm password", type="password", key="reg_confirm")
                registered = st.form_submit_button("Create account", type="primary", use_container_width=True)
            if registered:
                if new_password != confirm:
                    st.error("Passwords do not match.")
                else:
                    ok, message = auth.register(username, email, new_password)
                    st.success(message) if ok else st.error(message)
    st.caption("InsightAI is a student project prototype. For public deployment, add HTTPS, stronger operational controls and managed secrets.")

if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    login_screen()
    st.stop()

user = st.session_state.user
# Re-check account status on each rerun so disabled accounts cannot continue using the app.
fresh = db.get_user_by_id(user["id"])
if not fresh or not fresh["active"]:
    st.session_state.user = None
    st.error("Your account is disabled or no longer exists. Please contact an administrator.")
    st.stop()
st.session_state.user = dict(fresh)

with st.sidebar:
    logo()
    st.markdown(f"Signed in as **{user['username']}**")
    st.markdown(f'<span class="pill">{user["role"].upper()}</span>', unsafe_allow_html=True)
    nav_items = ["Overview", "Analyze text", "Batch analysis", "Analysis history", "Reports"]
    if user["role"] == "admin":
        nav_items += ["Admin panel", "Audit logs", "System information"]
    page = st.radio("WORKSPACE", nav_items, label_visibility="visible")
    st.divider()
    st.caption("Models")
    st.caption("RoBERTa · Sentiment")
    st.caption("BART · Topic classification")
    st.caption("First analysis downloads pretrained models.")
    if st.button("Log out", use_container_width=True):
        audit("LOGOUT", "SUCCESS", "Signed out")
        st.session_state.user = None
        st.rerun()

def run_and_save(text, source="manual"):
    result = analyze_text(text)
    analysis_id = db.save_analysis(user["id"], source, result["text"], result["sentiment"],
                                   result["sentiment_score"], result["topic"], result["topic_score"], result["keywords"])
    audit("ANALYSIS_COMPLETED", "SUCCESS", f"analysis_id={analysis_id}; source={source}; words={result['word_count']}")
    logger.info("Analysis completed user_id=%s analysis_id=%s source=%s", user["id"], analysis_id, source)
    return result, analysis_id

def display_result(result, key_prefix="r"):
    c1, c2, c3 = st.columns(3)
    c1.metric("Sentiment", result["sentiment"].title())
    c2.metric("Sentiment confidence", f'{result["sentiment_score"]:.1%}')
    c3.metric("Predicted topic", result["topic"])
    st.progress(max(0, min(1, result["sentiment_score"])), text=f'Sentiment model score · {result["sentiment_score"]:.1%}')
    topic_df = pd.DataFrame({"Topic": result["topic_labels"], "Confidence": result["topic_scores"]})
    fig = px.bar(topic_df, x="Topic", y="Confidence", range_y=[0,1], text=topic_df["Confidence"].map(lambda x:f"{x:.1%}"),
                 title="Topic confidence by category", color="Confidence", color_continuous_scale=["#263c62","#22d3ee","#a78bfa"])
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#e5edff",
                      margin=dict(l=10,r=10,t=55,b=10), coloraxis_showscale=False)
    fig.update_traces(textposition="outside", cliponaxis=False)
    st.plotly_chart(fig, use_container_width=True, key=f"{key_prefix}_topics")
    st.markdown("**Keywords**")
    kws = result["keywords"]
    st.markdown(" ".join(f'<span class="pill">{w}</span>' for w in kws) if kws else '<span class="small-muted">No significant keywords detected.</span>', unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    m1.metric("Words", result["word_count"])
    m2.metric("Characters", result["character_count"])
    m3.metric("Sentences (approx.)", result["sentence_count"])
    if result["sentiment_score"] < .55 or result["topic_score"] < .45:
        st.warning("At least one prediction has relatively low confidence. Treat the result cautiously.")
    st.caption("Confidence is a model score, not a guarantee of correctness. Topic scores show relative model preference.")
    with st.expander("Read the result in context"):
        st.write(f'The model classified this text as **{result["sentiment"]}** in sentiment and **{result["topic"]}** in topic.')
        st.write(f'Its strongest sentiment score was {result["sentiment_score"]:.1%}; the leading topic score was {result["topic_score"]:.1%}.')
        st.write("Keywords are extracted with a lightweight frequency-based method. They are clues, not a complete semantic explanation.")
    from reports import make_pdf_report
    pdf = make_pdf_report(result, user["username"])
    st.download_button("Download this analysis as PDF", pdf, file_name="insightai_analysis.pdf", mime="application/pdf", key=f"{key_prefix}_pdf")

if page == "Overview":
    header("Your intelligence overview", "A clear view of your text-analysis workspace.")
    rows = db.get_analyses(user["id"], limit=1000)
    total = len(rows)
    pos = sum(r["sentiment"] == "positive" for r in rows)
    neg = sum(r["sentiment"] == "negative" for r in rows)
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total analyses", total)
    c2.metric("Positive", pos)
    c3.metric("Negative", neg)
    c4.metric("Topics tracked", len(set(r["topic"] for r in rows)))
    if rows:
        df = pd.DataFrame([dict(r) for r in rows])
        a,b = st.columns(2)
        with a:
            fig = px.pie(df, names="sentiment", hole=.55, title="Sentiment distribution",
                         color="sentiment", color_discrete_map={"positive":"#34d399","negative":"#fb7185","neutral":"#fbbf24"})
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#e5edff")
            st.plotly_chart(fig, use_container_width=True)
        with b:
            topic_df = df["topic"].value_counts().rename_axis("Topic").reset_index(name="Analyses")
            fig = px.bar(topic_df, x="Topic", y="Analyses", title="Topics analyzed", color="Analyses", color_continuous_scale=["#334155","#22d3ee"])
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#e5edff", coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)
        st.subheader("Recent analyses")
        st.dataframe(df[["created_at","source_name","sentiment","sentiment_score","topic","topic_score","word_count"]].head(10),
                     use_container_width=True, hide_index=True)
    else:
        st.info("Your dashboard is ready. Go to **Analyze text** to run your first analysis.")

elif page == "Analyze text":
    header("Analyze text", "Understand sentiment, topic, keywords, and text characteristics.")
    text = st.text_area("Paste a review, message, article, or paragraph", height=220,
        placeholder="Example: The new AI tool helps students learn faster and makes studying easier.", max_chars=MAX_TEXT_CHARS)
    if st.button("✨ Analyze text", type="primary"):
        if not clean_text(text):
            st.warning("Please enter some text first.")
        else:
            try:
                with st.spinner("Running RoBERTa sentiment and BART topic models…"):
                    result, aid = run_and_save(text)
                st.session_state.last_result = result
                st.success(f"Analysis complete · ID {aid}")
            except Exception as exc:
                audit("ANALYSIS_FAILED", "ERROR", type(exc).__name__)
                logger.exception("Analysis failed")
                st.error("The AI models could not complete the analysis. Check your connection and model downloads, then try again.")
                with st.expander("Technical details"):
                    st.code(str(exc))
    if st.session_state.get("last_result"):
        display_result(st.session_state.last_result, "manual")

elif page == "Batch analysis":
    header("Batch analysis", "Analyze multiple text records from a CSV file.")
    st.caption("Your CSV must contain a column named `text`. Optionally include `id` or `source`.")
    sample = pd.DataFrame({"id":[1,2], "text":["The service was excellent and very helpful.","The application is confusing and failed twice."]})
    st.download_button("Download sample CSV", sample.to_csv(index=False).encode("utf-8"), "insightai_sample.csv", "text/csv")
    upload = st.file_uploader("Upload CSV", type=["csv"])
    if upload:
        try:
            frame = pd.read_csv(upload)
            if "text" not in frame.columns:
                st.error("CSV needs a column named 'text'.")
            elif len(frame) > 100:
                st.error("For this student prototype, upload at most 100 rows per batch.")
            else:
                st.dataframe(frame.head(10), use_container_width=True)
                if st.button("Analyze batch", type="primary"):
                    results = []
                    progress = st.progress(0)
                    for i, row in frame.iterrows():
                        try:
                            result, aid = run_and_save(str(row["text"]), str(row.get("source", row.get("id", f"row-{i+1}"))))
                            results.append({"row":i+1,"text":result["text"][:160],"sentiment":result["sentiment"],
                                "sentiment_confidence":result["sentiment_score"],"topic":result["topic"],
                                "topic_confidence":result["topic_score"],"keywords":", ".join(result["keywords"]),"analysis_id":aid})
                        except Exception as exc:
                            audit("BATCH_ROW_FAILED","ERROR",f"row={i+1}; error={type(exc).__name__}")
                            results.append({"row":i+1,"text":str(row["text"])[:160],"sentiment":"ERROR",
                                "sentiment_confidence":0,"topic":"Unavailable","topic_confidence":0,"keywords":"","analysis_id":None})
                        progress.progress((i+1)/len(frame))
                    out = pd.DataFrame(results)
                    st.session_state.batch_results = out
                    st.dataframe(out, use_container_width=True, hide_index=True)
                    st.download_button("Export batch results (CSV)", out.to_csv(index=False).encode("utf-8"),
                                       "insightai_batch_results.csv","text/csv")
        except Exception as exc:
            st.error(f"Could not read the CSV: {exc}")
    if st.session_state.get("batch_results") is not None:
        st.dataframe(st.session_state.batch_results, use_container_width=True, hide_index=True)

elif page == "Analysis history":
    header("Analysis history", "Search and manage analyses saved to your account.")
    rows = db.get_analyses(user["id"], limit=1000)
    if rows:
        df = pd.DataFrame([dict(r) for r in rows])
        query = st.text_input("Search preview, topic, sentiment, or source")
        if query:
            mask = df.astype(str).apply(lambda col: col.str.contains(query, case=False, na=False)).any(axis=1)
            df = df[mask]
        st.dataframe(df[["id","created_at","source_name","text_preview","sentiment","sentiment_score","topic","topic_score","keywords","word_count"]],
                     use_container_width=True, hide_index=True)
        st.download_button("Export history CSV", df.to_csv(index=False).encode("utf-8"), "insightai_history.csv","text/csv")
        with st.form("delete_history_form"):
            target = st.number_input("Analysis ID to delete", min_value=1, step=1)
            confirm_delete = st.checkbox("I confirm I want to permanently delete this analysis")
            delete = st.form_submit_button("Delete analysis")
        if delete:
            if confirm_delete:
                db.delete_analysis(int(target), user["id"])
                audit("ANALYSIS_DELETED","SUCCESS",f"analysis_id={int(target)}")
                st.success("If that analysis belonged to your account, it has been deleted.")
                st.rerun()
            else:
                st.warning("Confirm deletion before continuing.")
    else:
        st.info("No saved analyses yet. Run an analysis to build your history.")

elif page == "Reports":
    header("Reports & exports", "Download your saved analysis history for review or presentation.")
    rows = db.get_analyses(user["id"], limit=1000)
    if rows:
        df = pd.DataFrame([dict(r) for r in rows])
        st.metric("Available saved records", len(df))
        st.dataframe(df[["created_at","source_name","sentiment","sentiment_score","topic","topic_score","keywords","word_count"]],
                     use_container_width=True, hide_index=True)
        st.download_button("Download report data (CSV)", df.to_csv(index=False).encode("utf-8"), "insightai_report.csv","text/csv")
        st.caption("For an individual PDF, open Analyze text and download the report after analysis.")
    else:
        st.info("No reports yet. Analyze text first.")

elif page == "Admin panel" and user["role"] == "admin":
    header("Administration", "Manage access and monitor application activity.")
    stats = db.admin_stats()
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Accounts", stats["users"])
    c2.metric("Active accounts", stats["active_users"])
    c3.metric("Total analyses", stats["analyses"])
    c4.metric("Logged errors", stats["errors"])
    st.subheader("User management")
    users = db.list_users()
    if users:
        st.dataframe(pd.DataFrame([dict(r) for r in users]), use_container_width=True, hide_index=True)
        selectable = [r for r in users if r["id"] != user["id"] and r["role"] != "admin"]
        if selectable:
            options = {f'{r["username"]} · {r["email"]} · ID {r["id"]}': dict(r) for r in selectable}
            with st.form("admin_user_form"):
                selected_label = st.selectbox("Select a user", list(options))
                action = st.selectbox("Action", ["Disable account","Enable account"])
                done = st.form_submit_button("Apply change")
            if done:
                selected = options[selected_label]
                db.set_user_active(selected["id"], action == "Enable account")
                audit("USER_STATUS_CHANGED","SUCCESS",f"target_user_id={selected['id']}; action={action}")
                st.success(f"Updated account status for {selected['username']}.")
                st.rerun()
    st.subheader("Usage trends")
    all_rows = db.get_analyses(limit=1000)
    if all_rows:
        df = pd.DataFrame([dict(r) for r in all_rows])
        counts = df.groupby("username").size().reset_index(name="Analyses")
        fig = px.bar(counts, x="username", y="Analyses", title="Analyses by user")
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#e5edff")
        st.plotly_chart(fig, use_container_width=True)
    st.caption("Admin permissions are checked on the server-side application code, not just by hiding navigation items.")

elif page == "Audit logs" and user["role"] == "admin":
    header("Audit logs", "Review account, analysis, and system events.")
    logs = db.get_logs(limit=1000)
    df = pd.DataFrame([dict(r) for r in logs])
    if not df.empty:
        status_filter = st.multiselect("Filter status", sorted(df["status"].dropna().unique()), default=sorted(df["status"].dropna().unique()))
        event_filter = st.text_input("Filter event or username")
        df = df[df["status"].isin(status_filter)]
        if event_filter:
            mask = df[["event","username","details"]].astype(str).apply(lambda c:c.str.contains(event_filter,case=False,na=False)).any(axis=1)
            df = df[mask]
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button("Export filtered logs CSV", df.to_csv(index=False).encode("utf-8"), "insightai_audit_logs.csv","text/csv")
    else:
        st.info("No events recorded yet.")

elif page == "System information" and user["role"] == "admin":
    header("System information", "Application configuration and model details.")
    st.markdown(f"**Application:** {APP_NAME}")
    st.markdown(f"**Sentiment model:** `{SENTIMENT_MODEL}`")
    st.markdown(f"**Topic model:** `{TOPIC_MODEL}`")
    st.markdown(f"**Topics:** {', '.join(TOPICS)}")
    st.markdown(f"**Maximum analyzed characters per record:** {MAX_TEXT_CHARS}")
    st.markdown(f"**Python logging file:** `{LOG_DIR}/app.log`")
    st.markdown(f"**Database:** SQLite (`insightai.db`)")
    st.info("Models are pretrained and downloaded from Hugging Face on first use. The project performs inference; it does not train these models from scratch.")

st.divider()
st.caption("InsightAI · Student project prototype · AI confidence scores are estimates, not guarantees.")
