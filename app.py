import streamlit as st
import pandas as pd
import json
import os

st.set_page_config(page_title="Centralizator Tranzactii POS", layout="wide")
st.title("📊 Centralizator Tranzactii POS - PRO")

TID_FILE = "tid_list.json"
COMISION_FILE = "comisioane.json"

# =====================================================
# FUNCTII JSON
# =====================================================

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

# =====================================================
# IMPORT TID CSV
# =====================================================

st.sidebar.header("📥 Import TID-uri (CSV)")

uploaded_tid = st.sidebar.file_uploader("Importa CSV TID", type=["csv"])

if uploaded_tid:
    tid_df = pd.read_csv(uploaded_tid, sep=None, engine="python")
    tid_df.columns = tid_df.columns.str.strip().str.lower()

    tid_col = None
    device_col = None

    for col in tid_df.columns:
        if "terminal" in col or "tid" in col:
            tid_col = col
        if "device" in col or "firma" in col or "client" in col:
            device_col = col

    if tid_col and device_col:
        for _, row in tid_df.iterrows():
            tid_list[str(row[tid_col])] = str(row[device_col])
        save_json(TID_FILE, tid_list)
        st.sidebar.success("TID-uri importate!")
    else:
        st.sidebar.error("Nu am putut detecta coloanele TID si DEVICE.")

# =====================================================
# IMPORT COMISIOANE (SUPORT 2 FORMATE)
# =====================================================

st.sidebar.markdown("---")
st.sidebar.header("💰 Import Comisioane")

uploaded_com = st.sidebar.file_uploader("Importa CSV Comisioane", type=["csv"])

if uploaded_com:
    com_df = pd.read_csv(uploaded_com, sep=None, engine="python", header=None)

    comisioane_temp = {}
    current_client = None

    for _, row in com_df.iterrows():
        values = [str(x).strip() for x in row if pd.notna(x)]

        if len(values) == 0:
            continue

        # FORMAT STANDARD
        if len(values) >= 3 and "%" not in values[1]:
            try:
                client = values[0]
                com_10 = float(values[1].replace(",", "."))
                com_sub10 = float(values[2].replace(",", "."))
                comisioane_temp[client] = {
                    "10+": com_10,
                    "<10": com_sub10
                }
                continue
            except:
                pass

        # FORMAT BANCA (2 randuri)
        if values[0] != "":
            current_client = values[0]

        for val in values:
            if "%" in val:
                procent = float(val.replace("%", "").replace(",", "."))
                if any("mare" in v.lower() or "10" in v for v in values):
                    comisioane_temp.setdefault(current_client, {})["10+"] = procent
                if any("mica" in v.lower() or "sub" in v.lower() for v in values):
                    comisioane_temp.setdefault(current_client, {})["<10"] = procent

    for client, valori in comisioane_temp.items():
        if "10+" in valori and "<10" in valori:
            comisioane[client] = valori

    save_json(COMISION_FILE, comisioane)
    st.sidebar.success("Comisioane importate!")

# =====================================================
# UPLOAD CSV BANCA (ULTRA DETECTARE)
# =====================================================

uploaded_file = st.file_uploader("📂 Incarca fisier CSV banca", type=["csv"])

if uploaded_file:

    df = pd.read_csv(uploaded_file, sep=None, engine="python")
    df.columns = df.columns.str.strip().str.lower()

    # Detectare coloane
    tid_col = None
    amount_col = None
    fee_col = None
    tranz_col = None

    for col in df.columns:
        if "terminal" in col or "tid" in col:
            tid_col = col
        if "amount" in col or "suma" in col or "valoare" in col:
            amount_col = col
        if "fee" in col or "comision" in col:
            fee_col = col
        if "transaction" in col or "tranz" in col:
            tranz_col = col

    if not tid_col or not amount_col or not fee_col:
        st.error("Nu am putut detecta automat coloanele din fisierul bancii.")
        st.write("Coloane detectate:", df.columns.tolist())
        st.stop()

    # Curatare numeric
    for col in [amount_col, fee_col]:
        df[col] = (
            df[col].astype(str)
            .str.replace("-", "", regex=False)
            .str.replace(".", "", regex=False)
            .str.replace(",", ".", regex=False)
        )
        df[col] = pd.to_numeric(df[col], errors="coerce").round(2)

    # Asociere DEVICE
    df["DEVICE_NAME"] = (
        df[tid_col].astype(str)
        .map(tid_list)
        .fillna("NEASOCIAT")
    )

    # Calcul comision setat
    def calc_comision(row):
        device = row["DEVICE_NAME"]
        amt = row[amount_col]

        if device in comisioane:
            if amt >= 10:
                return round(amt * comisioane[device]["10+"] / 100, 2)
            else:
                return round(amt * comisioane[device]["<10"] / 100, 2)

        return round(amt * 1 / 100, 2)

    df["COMISION_CALCULAT"] = df.apply(calc_comision, axis=1)

    # Centralizare
    grouped = df.groupby("DEVICE_NAME").agg(
        TOTAL_TRANS_AMOUNT=(amount_col, "sum"),
        TOTAL_FEE=(fee_col, "sum"),
        TOTAL_COMISION_CALCULAT=("COMISION_CALCULAT", "sum"),
        NR_TRANZACTII=(amount_col, "count")
    ).reset_index().round(2)

    st.subheader("📊 Centralizare per CLIENT")
    st.dataframe(grouped, use_container_width=True)

    # TOTAL GENERAL
    total_trans = grouped["TOTAL_TRANS_AMOUNT"].sum()
    total_fee = grouped["TOTAL_FEE"].sum()
    procent_real = round((total_fee / total_trans) * 100, 2) if total_trans > 0 else 0

    st.markdown("---")
    st.subheader("📌 TOTAL GENERAL ZI")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total tranzactii", f"{total_trans:,.2f}")
    col2.metric("Total comisioane banca", f"{total_fee:,.2f}")
    col3.metric("Procent mediu (%)", f"{procent_real} %")

    # Export
    st.download_button(
        "⬇️ Descarca centralizare",
        grouped.to_csv(index=False, sep=";"),
        "centralizare.csv",
        "text/csv"
    )
