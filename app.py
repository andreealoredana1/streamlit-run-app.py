import streamlit as st
import pandas as pd
import json
import os

st.set_page_config(page_title="Centralizator POS", layout="wide")
st.title("📊 Centralizator Tranzactii POS")

TID_FILE = "tid_list.json"
COMISION_FILE = "comisioane.json"

# =========================
# Load / Save JSON
# =========================

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

# =========================
# IMPORT TID DIN CSV
# =========================

st.sidebar.header("📥 Import TID-uri (CSV)")

uploaded_tid = st.sidebar.file_uploader("Fisier CSV TID", type=["csv"])

if uploaded_tid:
    try:
        tid_df = pd.read_csv(uploaded_tid, sep=None, engine="python")
        tid_df.columns = tid_df.columns.str.lower()

        tid_col = next((c for c in tid_df.columns if "terminal" in c or "tid" in c), None)
        device_col = next((c for c in tid_df.columns if "device" in c or "client" in c or "firma" in c), None)

        if tid_col and device_col:
            for _, row in tid_df.iterrows():
                tid_list[str(row[tid_col])] = str(row[device_col])
            save_json(TID_FILE, tid_list)
            st.sidebar.success("TID-uri importate cu succes!")
        else:
            st.sidebar.error("Fisierul trebuie sa contina TERMINAL_ID si DEVICE_NAME")

    except Exception as e:
        st.sidebar.error(f"Eroare la citire: {e}")

# =========================
# IMPORT COMISIOANE CSV
# =========================

st.sidebar.markdown("---")
st.sidebar.header("💰 Import Comisioane (CSV)")

uploaded_com = st.sidebar.file_uploader("Fisier CSV Comisioane", type=["csv"])

if uploaded_com:
    try:
        com_df = pd.read_csv(uploaded_com, sep=None, engine="python")
        com_df.columns = com_df.columns.str.lower()

        client_col = next((c for c in com_df.columns if "client" in c), None)
        plus_col = next((c for c in com_df.columns if "10" in c), None)
        sub_col = next((c for c in com_df.columns if "sub" in c or "<" in c), None)

        if client_col and plus_col and sub_col:
            for _, row in com_df.iterrows():
                comisioane[str(row[client_col])] = {
                    "10+": float(str(row[plus_col]).replace(",", ".")),
                    "<10": float(str(row[sub_col]).replace(",", "."))
                }
            save_json(COMISION_FILE, comisioane)
            st.sidebar.success("Comisioane importate!")
        else:
            st.sidebar.error("CSV trebuie sa contina CLIENT, COMISION_10_PLUS, COMISION_SUB_10")

    except Exception as e:
        st.sidebar.error(f"Eroare la citire: {e}")

# =========================
# UPLOAD CSV BANCA
# =========================

st.markdown("---")
uploaded_file = st.file_uploader("📂 Incarca fisier CSV banca", type=["csv"])

if uploaded_file:

    try:
        df = pd.read_csv(uploaded_file, sep=None, engine="python")
        df.columns = df.columns.str.lower()

        tid_col = next((c for c in df.columns if "terminal" in c or "tid" in c), None)
        amount_col = next((c for c in df.columns if "amount" in c or "suma" in c), None)
        fee_col = next((c for c in df.columns if "fee" in c or "comision" in c), None)

        if not tid_col or not amount_col or not fee_col:
            st.error("Nu pot detecta coloanele TERMINAL_ID, TRANS_AMOUNT sau FEE_AMOUNT")
            st.stop()

        # Curatare numere
        for col in [amount_col, fee_col]:
            df[col] = (
                df[col].astype(str)
                .str.replace("-", "", regex=False)
                .str.replace(".", "", regex=False)
                .str.replace(",", ".", regex=False)
            )
            df[col] = pd.to_numeric(df[col], errors="coerce").round(2)

        # Asociere client
        df["CLIENT"] = df[tid_col].astype(str).map(tid_list).fillna("NEASOCIAT")

        # Calcul comision teoretic
        def calc(row):
            client = row["CLIENT"]
            amt = row[amount_col]

            if client in comisioane:
                if amt >= 10:
                    return round(amt * comisioane[client]["10+"] / 100, 2)
                else:
                    return round(amt * comisioane[client]["<10"] / 100, 2)

            return round(amt * 1 / 100, 2)

        df["COMISION_CALCULAT"] = df.apply(calc, axis=1)
        df["DIFERENTA"] = (df[fee_col] - df["COMISION_CALCULAT"]).round(2)

        # CENTRALIZARE PER CLIENT
        grouped = df.groupby("CLIENT").agg(
            TOTAL_TRANS_AMOUNT=(amount_col, "sum"),
            TOTAL_FEE_BANCA=(fee_col, "sum"),
            TOTAL_COMISION_CALCULAT=("COMISION_CALCULAT", "sum"),
            TOTAL_DIFERENTA=("DIFERENTA", "sum"),
            NR_TRANZACTII=(amount_col, "count")
        ).reset_index().round(2)

        st.subheader("📊 Centralizare per CLIENT")
        st.dataframe(grouped, use_container_width=True)

        # TOTAL GENERAL
        total_trans = grouped["TOTAL_TRANS_AMOUNT"].sum()
        total_fee = grouped["TOTAL_FEE_BANCA"].sum()

        procent_real = round((total_fee / total_trans) * 100, 2) if total_trans > 0 else 0

        st.markdown("---")
        st.subheader("📌 TOTAL GENERAL")

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Tranzactii", f"{total_trans:,.2f}")
        col2.metric("Total Comisioane Banca", f"{total_fee:,.2f}")
        col3.metric("Procent Mediu Real", f"{procent_real}%")

        # ALERTA
        if grouped["TOTAL_DIFERENTA"].sum() > 0.01:
            st.error("⚠️ ATENTIE: Banca a luat mai mult decat comisionul setat!")
        else:
            st.success("✔ Comisioanele sunt corecte.")

        # EXPORT
        st.download_button(
            "⬇️ Descarca centralizare",
            grouped.to_csv(index=False, sep=";"),
            "centralizare.csv",
            "text/csv"
        )

    except Exception as e:
        st.error(f"Eroare la procesare: {e}")
