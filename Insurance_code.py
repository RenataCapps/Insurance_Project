import streamlit as st
import mysql.connector
import pandas as pd
from datetime import datetime

# -----------------------------------------------------------------------------
# PAGE CONFIG
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="SEGUROPAR Insurance Analytics Dashboard",
    page_icon="🚗",
    layout="wide",
)

# -----------------------------------------------------------------------------
# CUSTOM CSS (inspirado en tus HTML con Tailwind)
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* General */
    body {
        background-color: #f3f4f6;
    }
    .main-title {
        font-size: 32px;
        font-weight: 800;
        color: #111827;
    }
    .subtitle {
        font-size: 16px;
        color: #4b5563;
    }
    /* KPI cards */
    .kpi-card {
        background-color: #ffffff;
        padding: 16px 20px;
        border-radius: 12px;
        box-shadow: 0 10px 15px -3px rgba(15, 23, 42, 0.08);
        border-bottom: 4px solid #3b82f6;
    }
    .kpi-title {
        font-size: 11px;
        text-transform: uppercase;
        color: #6b7280;
        letter-spacing: 0.05em;
    }
    .kpi-value {
        font-size: 26px;
        font-weight: 800;
        color: #111827;
        margin-top: 4px;
    }
    .kpi-detail {
        font-size: 12px;
        color: #6b7280;
        margin-top: 2px;
    }
    /* Status pills */
    .pill-open {
        background-color: #fef3c7;
        color: #92400e;
    }
    .pill-investigation {
        background-color: #fee2e2;
        color: #b91c1c;
        font-weight: 600;
    }
    .pill-settled {
        background-color: #dcfce7;
        color: #166534;
    }
    .pill-denied {
        background-color: #e5e7eb;
        color: #374151;
    }
    .pill-generic {
        background-color: #dbeafe;
        color: #1d4ed8;
    }
    .status-pill {
        padding: 2px 10px;
        border-radius: 999px;
        font-size: 11px;
        display: inline-block;
    }
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #e0f2fe 0%, #fef9c3 50%, #dcfce7 100%);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# DATABASE CONNECTION
# -----------------------------------------------------------------------------
@st.cache_resource
def get_connection():
    """Connect to your MySQL database on DigitalOcean."""
    try:
        conn = mysql.connector.connect(
            host="db-mysql-itom-do-user-28250611-0.j.db.ondigitalocean.com",
            port=25060,
            user="5037_car",
            password="Pass2025_5037",
            database="5037_car",
            connect_timeout=10,
        )
        return conn
    except mysql.connector.Error as err:
        st.error(f"❌ Database connection failed: {err}")
        return None


conn = get_connection()

if conn and conn.is_connected():
    st.sidebar.success("✅ Connected to SEGUROPAR DB")
else:
    st.sidebar.error("❌ Could not connect to database. Check credentials.")
    st.stop()

# -----------------------------------------------------------------------------
# LOAD DATA FROM VIEW
# -----------------------------------------------------------------------------
@st.cache_data
def load_fraud_view():
    """
    Carga todos los datos de la vista V_FRAUD_ANALYTICS_DASHBOARD.
    Esta vista la vas a usar para los 3 menús.
    """
    query = "SELECT * FROM V_FRAUD_ANALYTICS_DASHBOARD"
    df = pd.read_sql(query, conn)
    return df


df = load_fraud_view()

# Limpiamos nombres de columnas
df.columns = [c.strip() for c in df.columns]

# Se espera que la vista tenga columnas como:
# Claim_ID, Submission_Date, Settlement_Status, Claim_Amount_Requested,
# Fraud_Probability, Is_Fraudulent_Flag, Policyholder_ID, Policyholder_Name,
# Credit_Score, Employment_Status, VIN, Make_Name, Model_Name

# Convertir fechas si es necesario
if "Submission_Date" in df.columns:
    df["Submission_Date"] = pd.to_datetime(df["Submission_Date"], errors="coerce")


def _status_class(status: str) -> str:
    """Devuelve la clase CSS para el pill de estatus (por si quisieras usar HTML)."""
    s = (status or "").lower()
    if "investigation" in s:
        return "pill-investigation"
    if "open" in s:
        return "pill-open"
    if "settled" in s:
        return "pill-settled"
    if "denied" in s:
        return "pill-denied"
    return "pill-generic"


# -----------------------------------------------------------------------------
# SIDEBAR NAVIGATION
# -----------------------------------------------------------------------------
st.sidebar.title("🚗 SEGUROPAR")
st.sidebar.markdown("### Navigation")

tab = st.sidebar.radio(
    "Select a view:",
    (
        "Fraud Analyst",
        "Executive KPIs",
        "Claims Manager",
    ),
)

st.sidebar.markdown("---")
st.sidebar.info(
    "This dashboard uses the **V_FRAUD_ANALYTICS_DASHBOARD** view from your MySQL database."
)
st.sidebar.markdown("Made with ❤️ in Streamlit")

# -----------------------------------------------------------------------------
# FRAUD ANALYST TAB
# -----------------------------------------------------------------------------
if tab == "Fraud Analyst":
    st.markdown(
        '<div class="main-title">⚠️ Fraud Analyst Dashboard</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="subtitle">Prioritized claims queue driven by predictive fraud probabilities from the database.</p>',
        unsafe_allow_html=True,
    )
    st.markdown("---")

    if df.empty:
        st.warning("No data returned from V_FRAUD_ANALYTICS_DASHBOARD.")
        st.stop()

    # --- Controles ---
    col_ctrl1, col_ctrl2 = st.columns([2, 1])

    with col_ctrl1:
        threshold = st.slider(
            "Minimum fraud probability for **high-priority** claims",
            min_value=0.0,
            max_value=1.0,
            value=0.75,
            step=0.01,
        )

    with col_ctrl2:
        if "Credit_Score" in df.columns:
            cs_limit = st.selectbox(
                "Credit score filter",
                options=[
                    ("All scores", None),
                    ("< 700 (Moderate risk)", 700),
                    ("< 600 (High risk)", 600),
                    ("< 550 (Very high risk)", 550),
                ],
                index=0,
                format_func=lambda x: x[0],
            )
            cs_threshold = cs_limit[1]
        else:
            cs_threshold = None

    # --- Filtro de datos ---
    work_df = df.copy()
    work_df = work_df[work_df["Fraud_Probability"] >= threshold]

    if cs_threshold is not None and "Credit_Score" in work_df.columns:
        work_df = work_df[work_df["Credit_Score"] < cs_threshold]

    work_df = work_df.sort_values("Fraud_Probability", ascending=False)

    total_claims = len(df)
    total_high_priority = len(work_df)
    confirmed_fraud = 0
    if "Is_Fraudulent_Flag" in df.columns:
        confirmed_fraud = int(df["Is_Fraudulent_Flag"].fillna(0).astype(int).sum())
    avg_fraud_prob = (
        df["Fraud_Probability"].mean() * 100 if "Fraud_Probability" in df.columns else 0
    )

    # --- KPI cards ---
    k1, k2, k3, k4 = st.columns(4)

    k1.markdown(
        f"""
        <div class="kpi-card" style="border-bottom-color:#ef4444;">
            <div class="kpi-title">High-Priority Claims</div>
            <div class="kpi-value">{total_high_priority}</div>
            <div class="kpi-detail">Fraud probability ≥ {threshold:.2f}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    k2.markdown(
        f"""
        <div class="kpi-card" style="border-bottom-color:#f97316;">
            <div class="kpi-title">Average Fraud Probability</div>
            <div class="kpi-value">{avg_fraud_prob:.1f}%</div>
            <div class="kpi-detail">Across all claims in the system</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    k3.markdown(
        f"""
        <div class="kpi-card" style="border-bottom-color:#b91c1c;">
            <div class="kpi-title">Confirmed Fraud (YTD)</div>
            <div class="kpi-value">{confirmed_fraud}</div>
            <div class="kpi-detail">Is_Fraudulent_Flag = 1</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    k4.markdown(
        f"""
        <div class="kpi-card" style="border-bottom-color:#4f46e5;">
            <div class="kpi-title">Total Claims in View</div>
            <div class="kpi-value">{total_claims}</div>
            <div class="kpi-detail">Rows in V_FRAUD_ANALYTICS_DASHBOARD</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### 🔎 High-priority claims table")

    show_cols = []
    for col_candidate in [
        "Claim_ID",
        "Policyholder_Name",
        "Credit_Score",
        "Make_Name",
        "Model_Name",
        "Claim_Amount_Requested",
        "Fraud_Probability",
        "Settlement_Status",
        "Submission_Date",
    ]:
        if col_candidate in work_df.columns:
            show_cols.append(col_candidate)

    table_df = work_df[show_cols].copy()

    if "Claim_Amount_Requested" in table_df.columns:
        table_df["Claim_Amount_Requested"] = table_df["Claim_Amount_Requested"].round(2)
    if "Fraud_Probability" in table_df.columns:
        table_df["Fraud_Probability"] = (table_df["Fraud_Probability"] * 100).round(1)

    st.dataframe(table_df, use_container_width=True, height=420)

    with st.expander("ℹ️ How to read this table"):
        st.markdown(
            """
            - **High-priority** = claims with high model fraud probability  
            - You can adjust the **fraud threshold** and **credit score** filters above  
            - Use this queue as starting point for manual investigations
            """
        )

# -----------------------------------------------------------------------------
# EXECUTIVE KPIs TAB
# -----------------------------------------------------------------------------
elif tab == "Executive KPIs":
    st.markdown(
        '<div class="main-title">💰 Executive Management Dashboard</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="subtitle">Strategic KPIs for profitability, fraud control, and portfolio quality.</p>',
        unsafe_allow_html=True,
    )
    st.markdown("---")

    if df.empty:
        st.warning("No data returned from V_FRAUD_ANALYTICS_DASHBOARD.")
        st.stop()

    # Métricas básicas
    total_claims = len(df)
    total_requested = (
        df["Claim_Amount_Requested"].sum()
        if "Claim_Amount_Requested" in df.columns
        else 0.0
    )

    by_status = (
        df.groupby("Settlement_Status")["Claim_ID"]
        .count()
        .rename("Count")
        .reset_index()
        if "Settlement_Status" in df.columns
        else pd.DataFrame()
    )
    confirmed_fraud = int(
        df.get("Is_Fraudulent_Flag", pd.Series(dtype=int)).fillna(0).astype(int).sum()
    )
    fraud_rate = (confirmed_fraud / total_claims * 100) if total_claims > 0 else 0
    avg_claim_amount = (total_requested / total_claims) if total_claims > 0 else 0

    # KPI cards
    k1, k2, k3, k4 = st.columns(4)

    k1.markdown(
        f"""
        <div class="kpi-card" style="border-bottom-color:#22c55e;">
            <div class="kpi-title">Total Claims (YTD)</div>
            <div class="kpi-value">{total_claims}</div>
            <div class="kpi-detail">All claims in current analytics view</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    k2.markdown(
        f"""
        <div class="kpi-card" style="border-bottom-color:#16a34a;">
            <div class="kpi-title">Total Claim Value</div>
            <div class="kpi-value">${total_requested:,.0f}</div>
            <div class="kpi-detail">Sum of Claim_Amount_Requested</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    k3.markdown(
        f"""
        <div class="kpi-card" style="border-bottom-color:#ef4444;">
            <div class="kpi-title">Confirmed Fraud Rate</div>
            <div class="kpi-value">{fraud_rate:.1f}%</div>
            <div class="kpi-detail">Is_Fraudulent_Flag = 1 / Total claims</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    k4.markdown(
        f"""
        <div class="kpi-card" style="border-bottom-color:#0ea5e9;">
            <div class="kpi-title">Average Claim Amount</div>
            <div class="kpi-value">${avg_claim_amount:,.0f}</div>
            <div class="kpi-detail">Mean Claim_Amount_Requested</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### 📊 Claim status mix")

    if not by_status.empty:
        st.dataframe(by_status, use_container_width=True, height=250)
    else:
        st.info("Settlement_Status column not found in view – cannot build mix table.")

    # Top high-risk customers: muchos claims + alto valor + alta prob. fraude
    st.markdown("### 🔥 Top high-risk customers (frequency & value)")

    if "Policyholder_Name" in df.columns:
        risk_df = (
            df.groupby("Policyholder_Name")
            .agg(
                Claims=("Claim_ID", "count"),
                Total_Claim_Value=("Claim_Amount_Requested", "sum"),
                Avg_Fraud_Prob=("Fraud_Probability", "mean"),
            )
            .reset_index()
        )
        risk_df["Avg_Fraud_Prob"] = (risk_df["Avg_Fraud_Prob"] * 100).round(1)
        risk_df = risk_df.sort_values(
            ["Claims", "Total_Claim_Value"], ascending=False
        ).head(10)

        st.dataframe(risk_df, use_container_width=True, height=350)
    else:
        st.info(
            "Policyholder_Name column not found in view – cannot build customer ranking."
        )

    with st.expander("ℹ️ Executive interpretation tips"):
        st.markdown(
            """
            - **Fraud rate** gives you a quick sense of effectiveness of controls  
            - The **status mix** shows operational backlog and closure efficiency  
            - **Top high-risk customers** combine high frequency + high value + higher fraud probability  
            """
        )

# -----------------------------------------------------------------------------
# CLAIMS MANAGER TAB
# -----------------------------------------------------------------------------
elif tab == "Claims Manager":
    st.markdown(
        '<div class="main-title">📂 Claims Manager Dashboard</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="subtitle">Operational view for validation queue and aging of open claims.</p>',
        unsafe_allow_html=True,
    )
    st.markdown("---")

    if df.empty:
        st.warning("No data returned from V_FRAUD_ANALYTICS_DASHBOARD.")
        st.stop()

    # Days since submission
    today = pd.Timestamp(datetime.utcnow().date())
    if "Submission_Date" in df.columns:
        df["Days_Since_Submission"] = (today - df["Submission_Date"]).dt.days
    else:
        df["Days_Since_Submission"] = pd.NA

    # Validation queue: high value o estatus sensibles
    high_value_threshold = 20000
    status_for_review = ["Open", "In Investigation", "Denied"]

    queue_df = df.copy()
    if "Claim_Amount_Requested" in queue_df.columns:
        mask_value = queue_df["Claim_Amount_Requested"] >= high_value_threshold
    else:
        mask_value = pd.Series([False] * len(queue_df), index=queue_df.index)

    if "Settlement_Status" in queue_df.columns:
        mask_status = queue_df["Settlement_Status"].isin(status_for_review)
    else:
        mask_status = pd.Series([False] * len(queue_df), index=queue_df.index)

    queue_df = queue_df[mask_value | mask_status].copy()
    queue_df = queue_df.sort_values(
        ["Settlement_Status", "Claim_Amount_Requested"], ascending=[True, False]
    )

    # KPIs
    pending_validation = len(queue_df)
    open_claims = (
        queue_df["Settlement_Status"]
        .str.contains("Open", case=False, na=False)
        .sum()
        if "Settlement_Status" in queue_df.columns
        else 0
    )
    in_investigation = (
        queue_df["Settlement_Status"]
        .str.contains("Investigation", case=False, na=False)
        .sum()
        if "Settlement_Status" in queue_df.columns
        else 0
    )
    avg_days_open = (
        queue_df["Days_Since_Submission"].mean()
        if "Days_Since_Submission" in queue_df.columns
        else None
    )

    c1, c2, c3 = st.columns(3)

    c1.markdown(
        f"""
        <div class="kpi-card" style="border-bottom-color:#facc15;">
            <div class="kpi-title">Claims Pending Validation</div>
            <div class="kpi-value">{pending_validation}</div>
            <div class="kpi-detail">High value or sensitive status (Open / Investigation / Denied)</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c2.markdown(
        f"""
        <div class="kpi-card" style="border-bottom-color:#2563eb;">
            <div class="kpi-title">Open / In Investigation</div>
            <div class="kpi-value">{open_claims + in_investigation}</div>
            <div class="kpi-detail">{open_claims} Open · {in_investigation} In Investigation</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if avg_days_open is not None and not pd.isna(avg_days_open):
        avg_days_str = f"{avg_days_open:.0f} days"
    else:
        avg_days_str = "N/A"

    c3.markdown(
        f"""
        <div class="kpi-card" style="border-bottom-color:#0f766e;">
            <div class="kpi-title">Avg. Age of Validation Queue</div>
            <div class="kpi-value">{avg_days_str}</div>
            <div class="kpi-detail">Days since submission for claims in queue</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Validation queue table
    st.markdown("### ✅ Claims requiring manager validation")

    show_cols = []
    for col_candidate in [
        "Claim_ID",
        "Policyholder_Name",
        "Claim_Amount_Requested",
        "Settlement_Status",
        "Submission_Date",
        "Days_Since_Submission",
        "Credit_Score",
        "Make_Name",
        "Model_Name",
    ]:
        if col_candidate in queue_df.columns:
            show_cols.append(col_candidate)

    queue_table = queue_df[show_cols].copy()
    if "Claim_Amount_Requested" in queue_table.columns:
        queue_table["Claim_Amount_Requested"] = queue_table[
            "Claim_Amount_Requested"
        ].round(2)

    st.dataframe(queue_table, use_container_width=True, height=420)

    with st.expander("ℹ️ Suggested manager actions"):
        st.markdown(
            """
            - Validate **high-value** claims (≥ 20,000) regardless of status  
            - Review **Denied** claims with high amount or high fraud score  
            - Monitor **aging** of Open / In Investigation to avoid backlog  
            """
        )
