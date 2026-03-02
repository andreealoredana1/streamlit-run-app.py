import streamlit as st
import pandas as pd
import json
import os
import sqlite3
from io import BytesIO
import plotly.express as px

# -----------------------------
# PAROLA ACCES
# -----------------------------
def check_password():
    def password_entered():
        if st.session_state["password"] == "admin123":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Parola", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Parola", type="password", on_change=password_entered, key="password")
        st.error("Parola gresita")
        return False
    else:
        return True

if not check_password():
    st.stop()

# -----------------------------
# CONFIG PAGINA
# -----------------------------
st.set_page_config(page_title="Centralizator POS PRO", layout="wide")
st.title("📊 Centralizator Tranzactii POS - PRO")

# -----------------------------
# BAZA DE DATE SQLITE
# -----------------------------
conn = sqlite3.connect("centralizator.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS comisioane (
    device_name TEXT PRIMARY KEY,
    com_10 REAL,
    com_10m REAL
)
""")
conn.commit()

# -----------------------------
# FISIER TID JSON
# -----------------------------
TID_FILE = "tid_list.json"

def load_json(file, default):
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

tid_list = load_json(TID_FILE, {})

# -----------------------------
# SIDEBAR TID
# -----------------------------
st.sidebar.header("➕ Adauga TID")
with st.sidebar.form("form_tid"):
    new_tid = st.text_input("TERMINAL_ID")
    new_device = st.text_input("DEVICE_NAME")
    submitted = st.form_submit_button("Adauga")

    if submitted and new_tid and new_device:
        tid_list[new_tid] = new_device
        save_json(TID_FILE, tid_list)
        st.sidebar.success("TID salvat!")

# -----------------------------
# SIDEBAR COMISIOANE (EDITABILE)
# -----------------------------
st.sidebar.header("💰 Seteaza / Editeaza Comisioane")

com_df = pd.read_sql("SELECT * FROM comisioane", conn)

if not com_df.empty:
    edited_com_df = st.sidebar.data_editor(
        com_df,
        num_rows="dynamic",
        use_container_width=True
    )

    if st.sidebar.button("Salveaza Comisioane"):
        c.execute("DELETE FROM comisioane")
        for _, row in edited_com_df.iterrows():
            c.execute(
                "INSERT INTO comisioane VALUES (?, ?, ?)",
                (row["device_name"], row["com_10"], row["com_10m"])
            )
        conn.commit()
        st.sidebar.success("Comisioane actualizate!")
else:
    st.sidebar.info("Nu exista comisioane salvate.")

# -----------------------------
# UPLOAD CSV
# -----------------------------
uploaded_file = st.file_uploader("Incarca fisier CSV banca", type=["csv"])

if uploaded_file is not None:

    df = pd.read_csv(uploaded_file, sep=None, engine="python")

    # -----------------------------
    # VALIDARE COLOANE
    # -----------------------------
    required_cols = ["TERMINAL_ID", "TRANS_AMOUNT"]
    missing = [c for c in required_cols if c not in df.columns]

    if missing:
        st.error(f"Lipsesc coloane obligatorii: {missing}")
        st.stop()

    # -----------------------------
    # CURATARE NUMERICA
    # -----------------------------
    for col in ["TRANS_AMOUNT", "FEE_AMOUNT"]:
        if col in df.columns:
            df[col] = (
                df[col].astype(str)
                .str.replace(".", "", regex=False)
                .str.replace(",", ".", regex=False)
            )
            df[col] = pd.to_numeric(df[col], errors="coerce").round(2)

    # FEE fara minus
    if "FEE_AMOUNT" in df.columns:
        df["FEE_AMOUNT"] = df["FEE_AMOUNT"].abs()

    # -----------------------------
    # MAPARE DEVICE_NAME
    # -----------------------------
    df["DEVICE_NAME"] = df["TERMINAL_ID"].map(tid_list).fillna("NEASIGNAT")

    # -----------------------------
    # FILTRARE DATA (daca exista)
    # -----------------------------
    if "DATE" in df.columns:
        df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce")
        selected_date = st.date_input(
            "Selecteaza data",
            value=df["DATE"].min()
        )
        df = df[df["DATE"].dt.date == selected_date]

    # -----------------------------
    # CENTRALIZARE PER CLIENT
    # -----------------------------
    grouped = df.groupby("DEVICE_NAME").agg(
        TOTAL_TRANS_AMOUNT=("TRANS_AMOUNT", "sum"),
        TOTAL_FEE=("FEE_AMOUNT", "sum"),
        NR_TRANZACTII=("TRANS_AMOUNT", "count")
    ).reset_index()

    grouped = grouped.round(2)

    st.subheader("📊 Centralizare per client")
    st.dataframe(grouped, use_container_width=True)

    # -----------------------------
    # TOTAL GENERAL
    # -----------------------------
    total_trans = grouped["TOTAL_TRANS_AMOUNT"].sum()
    total_fee = grouped["TOTAL_FEE"].sum()

    procent_real = (total_fee / total_trans * 100) if total_trans != 0 else 0

    st.markdown("---")
    st.subheader("📊 Total General Zi")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Vanzari", f"{total_trans:,.2f} RON")
    col2.metric("Total Comisioane", f"{total_fee:,.2f} RON")
    col3.metric("Procent Mediu Comision", f"{procent_real:.2f} %")

    # -----------------------------
    # GRAFIC INTERACTIV
    # -----------------------------
    fig = px.bar(
        grouped,
        x="DEVICE_NAME",
        y="TOTAL_FEE",
        title="Comisioane per client"
    )

    st.plotly_chart(fig, use_container_width=True)

    # -----------------------------
    # EXPORT EXCEL
    # -----------------------------
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Detaliat')
        grouped.to_excel(writer, index=False, sheet_name='Centralizat')

    st.download_button(
        "⬇️ Descarca Excel complet",
        data=output.getvalue(),
        file_name="centralizator_pos_pro.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
