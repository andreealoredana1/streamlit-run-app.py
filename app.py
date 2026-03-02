import streamlit as st
import pandas as pd
import json
import os
import sqlite3

# -----------------------------
# CONFIG PAGINA
# -----------------------------
st.set_page_config(page_title="Centralizator POS PRO", layout="wide")
st.title("📊 Centralizator Tranzactii POS - PRO")

# -----------------------------
# BAZA DE DATE SQLITE (pentru comisioane)
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
# SIDEBAR - ADAUGARE TID
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
# SIDEBAR - EDITARE COMISIOANE
# -----------------------------
st.sidebar.header("💰 Seteaza / Editeaza Comisioane")

com_df = pd.read_sql("SELECT * FROM comisioane", conn)

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

# -----------------------------
# UPLOAD CSV
# -----------------------------
uploaded_file = st.file_uploader("Incarca fisier CSV banca", type=["csv"])

if uploaded_file is not None:

    df = pd.read_csv(uploaded_file, sep=None, engine="python")

    # VALIDARE COLOANE OBLIGATORII
    required_cols = ["TERMINAL_ID", "TRANS_AMOUNT"]
    missing = [c for c in required_cols if c not in df.columns]

    if missing:
        st.error(f"Lipsesc coloane obligatorii: {missing}")
        st.stop()

    # CURATARE NUMERICA
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
    else:
        df["FEE_AMOUNT"] = 0

    # MAPARE DEVICE_NAME
    df["DEVICE_NAME"] = df["TERMINAL_ID"].map(tid_list).fillna("NEASIGNAT")

    # FILTRARE PE DATA (daca exista)
    if "DATE" in df.columns:
        df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce")
        selected_date = st.date_input(
            "Selecteaza data",
            value=df["DATE"].min()
        )
        df = df[df["DATE"].dt.date == selected_date]

    # CENTRALIZARE PER CLIENT
    grouped = df.groupby("DEVICE_NAME").agg(
        TOTAL_TRANS_AMOUNT=("TRANS_AMOUNT", "sum"),
        TOTAL_FEE=("FEE_AMOUNT", "sum"),
        NR_TRANZACTII=("TRANS_AMOUNT", "count")
    ).reset_index()

    grouped = grouped.round(2)

    st.subheader("📊 Centralizare per client")
    st.dataframe(grouped, use_container_width=True)

    # TOTAL GENERAL
    total_trans = grouped["TOTAL_TRANS_AMOUNT"].sum()
    total_fee = grouped["TOTAL_FEE"].sum()

    procent_real = (total_fee / total_trans * 100) if total_trans != 0 else 0

    st.markdown("---")
    st.subheader("📊 Total General Zi")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Vanzari", f"{total_trans:,.2f} RON")
    col2.metric("Total Comisioane", f"{total_fee:,.2f} RON")
    col3.metric("Procent Mediu Comision", f"{procent_real:.2f} %")

    # GRAFIC STABIL
    st.markdown("### 📈 Comisioane per client")
    st.bar_chart(
        grouped.set_index("DEVICE_NAME")["TOTAL_FEE"]
    )

    # EXPORT CSV (SUPER STABIL)
    st.markdown("### 📥 Export")

    csv_detaliat = df.to_csv(index=False, sep=';').encode('utf-8')
    st.download_button(
        "⬇️ Descarca Detaliat CSV",
        csv_detaliat,
        "detaliat.csv",
        "text/csv"
    )

    csv_centralizat = grouped.to_csv(index=False, sep=';').encode('utf-8')
    st.download_button(
        "⬇️ Descarca Centralizat CSV",
        csv_centralizat,
        "centralizat.csv",
        "text/csv"
    )
