import streamlit as st
import pandas as pd
import json
import os

# =============================
# CONFIGURARE PAGINA
# =============================

st.set_page_config(page_title="Centralizator Tranzactii POS", layout="wide")
st.title("📊 Centralizator Tranzactii POS")

# =============================
# FISIERE PERSISTENTA
# =============================

TID_FILE = "tid_list.json"
COMISION_FILE = "comisioane.json"

def load_json(file, default):
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

tid_list = load_json(TID_FILE, {})
comisioane = load_json(COMISION_FILE, {})

# =============================
# SIDEBAR - IMPORT TID INTELIGENT
# =============================

st.sidebar.header("📥 Import TID (format liber)")

uploaded_tid = st.sidebar.file_uploader(
    "Incarca fisier CSV cu TID-uri",
    type=["csv"]
)

if uploaded_tid:
    try:
        tid_df = pd.read_csv(uploaded_tid, sep=None, engine="python")

        # Curatare nume coloane
        tid_df.columns = (
            tid_df.columns
            .str.strip()
            .str.lower()
            .str.replace(" ", "")
            .str.replace("_", "")
        )

        # Detectare coloane
        possible_tid_cols = [
            col for col in tid_df.columns
            if "terminal" in col or "tid" in col or "cod" in col
        ]

        possible_name_cols = [
            col for col in tid_df.columns
            if "device" in col or "firma" in col or "nume" in col or "client" in col or "societate" in col
        ]

        if possible_tid_cols and possible_name_cols:

            tid_col = possible_tid_cols[0]
            name_col = possible_name_cols[0]

            tid_df[tid_col] = tid_df[tid_col].astype(str)
            tid_df[name_col] = tid_df[name_col].astype(str)

            for _, row in tid_df.iterrows():
                tid_list[row[tid_col]] = row[name_col]

            save_json(TID_FILE, tid_list)

            st.sidebar.success(f"{len(tid_df)} TID-uri importate cu succes!")

        else:
            st.sidebar.error("Nu am putut identifica automat coloanele.")

    except Exception as e:
        st.sidebar.error(f"Eroare la citire: {e}")

# =============================
# SIDEBAR - ADAUGARE MANUALA TID
# =============================

st.sidebar.header("➕ Adauga TID manual")

with st.sidebar.form("form_tid"):
    new_tid = st.text_input("TERMINAL_ID")
    new_device = st.text_input("DEVICE_NAME")
    submitted = st.form_submit_button("Salveaza")

    if submitted and new_tid and new_device:
        tid_list[new_tid] = new_device
        save_json(TID_FILE, tid_list)
        st.sidebar.success("TID salvat!")

# =============================
# SIDEBAR - SETARE COMISIOANE
# =============================

st.sidebar.header("💰 Seteaza / Editeaza comisioane")

with st.sidebar.form("form_com"):
    device = st.text_input("DEVICE_NAME")
    com_10 = st.number_input("Comision ≥10 RON (%)", min_value=0.0)
    com_sub10 = st.number_input("Comision <10 RON (%)", min_value=0.0)
    save_com = st.form_submit_button("Salveaza")

    if save_com and device:
        comisioane[device] = {
            "10+": com_10,
            "<10": com_sub10
        }
        save_json(COMISION_FILE, comisioane)
        st.sidebar.success("Comision salvat!")

# =============================
# UPLOAD CSV BANCA
# =============================

uploaded_file = st.file_uploader("Incarca fisier CSV banca", type=["csv"])

if uploaded_file:

    try:
        df = pd.read_csv(uploaded_file, sep=None, engine="python")
    except:
        df = pd.read_csv(uploaded_file, sep=";", encoding="latin1")

    # Curatare valori numerice
    for col in ["TRANS_AMOUNT", "FEE_AMOUNT"]:
        if col in df.columns:
            df[col] = (
                df[col].astype(str)
                .str.replace("-", "", regex=False)
                .str.replace(".", "", regex=False)
                .str.replace(",", ".", regex=False)
            )
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Mapare firma
    df["TERMINAL_ID"] = df["TERMINAL_ID"].astype(str)
    df["DEVICE_NAME"] = df["TERMINAL_ID"].map(tid_list).fillna("NEASOCIAT")

    # Calcul comision
    def calc_comision(row):
        device = row["DEVICE_NAME"]
        amt = row["TRANS_AMOUNT"]

        if device in comisioane:
            if amt >= 10:
                return round(amt * comisioane[device]["10+"] / 100, 2)
            else:
                return round(amt * comisioane[device]["<10"] / 100, 2)
        else:
            if amt >= 10:
                return round(amt * 1 / 100, 2)
            else:
                return round(amt * 2 / 100, 2)

    df["COMISION_CALCULAT"] = df.apply(calc_comision, axis=1)

    # =============================
    # CENTRALIZARE PER CLIENT
    # =============================

    grouped = df.groupby("DEVICE_NAME").agg(
        TOTAL_TRANS_AMOUNT=("TRANS_AMOUNT", "sum"),
        TOTAL_FEE=("FEE_AMOUNT", "sum"),
        TOTAL_COMISION_CALCULAT=("COMISION_CALCULAT", "sum")
    ).reset_index()

    grouped = grouped.round(2)

    st.subheader("📊 Centralizare per client")
    st.dataframe(grouped, use_container_width=True)

    # =============================
    # TOTAL GENERAL
    # =============================

    total_trans = grouped["TOTAL_TRANS_AMOUNT"].sum()
    total_fee = grouped["TOTAL_FEE"].sum()

    procent_real = round((total_fee / total_trans) * 100, 2) if total_trans > 0 else 0

    st.markdown("---")
    st.subheader("📈 TOTAL GENERAL ZI")

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Tranzactii", f"{total_trans:,.2f} RON")
    col2.metric("Total Comisioane Banca", f"{total_fee:,.2f} RON")
    col3.metric("Procent Real Comision", f"{procent_real}%")

    # =============================
    # EXPORT CSV
    # =============================

    grouped_export = grouped.copy()

    for col in ["TOTAL_TRANS_AMOUNT", "TOTAL_FEE", "TOTAL_COMISION_CALCULAT"]:
        grouped_export[col] = grouped_export[col].apply(
            lambda x: f"{x:.2f}".replace(".", ",")
        )

    csv_export = grouped_export.to_csv(index=False, sep=";")

    st.download_button(
        "⬇️ Descarca centralizare CSV",
        csv_export,
        "centralizare_clienti.csv",
        "text/csv"
    )
