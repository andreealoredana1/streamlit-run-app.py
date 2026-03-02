import streamlit as st
import pandas as pd
import json
import os

st.set_page_config(page_title="Centralizator Tranzactii POS", layout="wide")
st.title("📊 Centralizator Tranzactii POS")

TID_FILE = "tid_list.json"
COMISION_FILE = "comisioane.json"

# =============================
# Functii JSON
# =============================

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
# SIDEBAR - TID URI
# =============================

st.sidebar.header("📥 Import TID-uri (CSV)")

uploaded_tid = st.sidebar.file_uploader("Importa CSV TID", type=["csv"])

if uploaded_tid:
    try:
        tid_df = pd.read_csv(uploaded_tid, sep=None, engine="python")
        tid_df.columns = tid_df.columns.str.strip().str.upper()

        if "TERMINAL_ID" in tid_df.columns and "DEVICE_NAME" in tid_df.columns:
            for _, row in tid_df.iterrows():
                tid_list[str(row["TERMINAL_ID"])] = str(row["DEVICE_NAME"])
            save_json(TID_FILE, tid_list)
            st.sidebar.success(f"{len(tid_df)} TID-uri importate!")
        else:
            st.sidebar.error("Fisierul trebuie sa contina TERMINAL_ID si DEVICE_NAME")

    except Exception as e:
        st.sidebar.error(f"Eroare la citire: {e}")

if tid_list:
    st.sidebar.markdown("### ✏️ Editeaza TID-uri")
    tid_edit_df = pd.DataFrame(
        list(tid_list.items()),
        columns=["TERMINAL_ID", "DEVICE_NAME"]
    )

    search_tid = st.sidebar.text_input("🔍 Cauta TID sau firma")

    if search_tid:
        mask = (
            tid_edit_df["TERMINAL_ID"].str.contains(search_tid, case=False) |
            tid_edit_df["DEVICE_NAME"].str.contains(search_tid, case=False)
        )
        tid_edit_df = tid_edit_df[mask]

    edited_tid_df = st.sidebar.data_editor(
        tid_edit_df,
        num_rows="dynamic",
        use_container_width=True
    )

    if st.sidebar.button("💾 Salveaza TID-uri"):
        edited_tid_df = edited_tid_df.dropna()
        tid_list = dict(zip(
            edited_tid_df["TERMINAL_ID"],
            edited_tid_df["DEVICE_NAME"]
        ))
        save_json(TID_FILE, tid_list)
        st.sidebar.success("TID-uri actualizate!")

# =============================
# SIDEBAR - COMISIOANE
# =============================

st.sidebar.markdown("---")
st.sidebar.header("💰 Comisioane per client (CSV)")

uploaded_com = st.sidebar.file_uploader("Importa CSV Comisioane", type=["csv"])

if uploaded_com:
    try:
        com_df = pd.read_csv(uploaded_com, sep=None, engine="python")
        com_df.columns = com_df.columns.str.strip().str.upper()

        if {"CLIENT", "COMISION_10_PLUS", "COMISION_SUB_10"}.issubset(com_df.columns):
            for _, row in com_df.iterrows():
                comisioane[str(row["CLIENT"])] = {
                    "10+": float(row["COMISION_10_PLUS"]),
                    "<10": float(row["COMISION_SUB_10"])
                }
            save_json(COMISION_FILE, comisioane)
            st.sidebar.success("Comisioane importate!")
        else:
            st.sidebar.error("CSV trebuie sa contina CLIENT, COMISION_10_PLUS, COMISION_SUB_10")

    except Exception as e:
        st.sidebar.error(f"Eroare: {e}")

if comisioane:
    st.sidebar.markdown("### ✏️ Editeaza Comisioane")

    com_edit_df = pd.DataFrame([
        {
            "CLIENT": k,
            "COMISION_10_PLUS": v["10+"],
            "COMISION_SUB_10": v["<10"]
        }
        for k, v in comisioane.items()
    ])

    search_com = st.sidebar.text_input("🔍 Cauta client")

    if search_com:
        com_edit_df = com_edit_df[
            com_edit_df["CLIENT"].str.contains(search_com, case=False)
        ]

    edited_com_df = st.sidebar.data_editor(
        com_edit_df,
        num_rows="dynamic",
        use_container_width=True
    )

    if st.sidebar.button("💾 Salveaza Comisioane"):
        edited_com_df = edited_com_df.dropna()
        comisioane = {
            row["CLIENT"]: {
                "10+": float(row["COMISION_10_PLUS"]),
                "<10": float(row["COMISION_SUB_10"])
            }
            for _, row in edited_com_df.iterrows()
        }
        save_json(COMISION_FILE, comisioane)
        st.sidebar.success("Comisioane actualizate!")

# =============================
# UPLOAD CSV BANCA
# =============================

uploaded_file = st.file_uploader("📂 Incarca fisierul CSV de la banca", type=["csv"])

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file, sep=None, engine="python")
    except:
        df = pd.read_csv(uploaded_file, sep=";", encoding="latin1")

    for col in ["TRANS_AMOUNT", "FEE_AMOUNT"]:
        if col in df.columns:
            df[col] = (
                df[col].astype(str)
                .str.replace("-", "", regex=False)
                .str.replace(".", "", regex=False)
                .str.replace(",", ".", regex=False)
            )
            df[col] = pd.to_numeric(df[col], errors="coerce").round(2)

    df["DEVICE_NAME"] = df["TERMINAL_ID"].astype(str).map(tid_list).fillna("NEASOCIAT")

    def calc_comision(row):
        device = row["DEVICE_NAME"]
        amt = row["TRANS_AMOUNT"]
        if device in comisioane:
            if amt >= 10:
                return round(amt * comisioane[device]["10+"] / 100, 2)
            else:
                return round(amt * comisioane[device]["<10"] / 100, 2)
        else:
            return round(amt * 1 / 100, 2)

    df["COMISION_CALCULAT"] = df.apply(calc_comision, axis=1)

    # =============================
    # CENTRALIZARE PER CLIENT
    # =============================

    grouped = df.groupby("DEVICE_NAME").agg(
        TOTAL_TRANS_AMOUNT=("TRANS_AMOUNT", "sum"),
        TOTAL_FEE=("FEE_AMOUNT", "sum"),
        TOTAL_COMISION_CALCULAT=("COMISION_CALCULAT", "sum"),
        NR_TRANZACTII=("TRANS_AMOUNT", "count")
    ).reset_index()

    grouped = grouped.round(2)

    st.subheader("📊 Centralizare per CLIENT")
    st.dataframe(grouped, use_container_width=True)

    # =============================
    # TOTAL GENERAL
    # =============================

    total_trans = grouped["TOTAL_TRANS_AMOUNT"].sum()
    total_fee = grouped["TOTAL_FEE"].sum()

    procent_real = 0
    if total_trans > 0:
        procent_real = round((total_fee / total_trans) * 100, 2)

    st.markdown("---")
    st.subheader("📌 TOTAL GENERAL ZI")

    col1, col2, col3 = st.columns(3)

    col1.metric("Total tranzactii (RON)", f"{total_trans:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    col2.metric("Total comisioane banca (RON)", f"{total_fee:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    col3.metric("Procent mediu comision (%)", f"{procent_real} %")

    # =============================
    # EXPORT DETALIAT
    # =============================

    df_export = df.copy()
    for col in ["TRANS_AMOUNT", "FEE_AMOUNT", "COMISION_CALCULAT"]:
        df_export[col] = df_export[col].apply(lambda x: f"{x:.2f}".replace(".", ","))

    csv_detaliat = df_export.to_csv(index=False, sep=";")

    st.download_button(
        "⬇️ Descarca fisier detaliat",
        csv_detaliat,
        "export_detaliat.csv",
        "text/csv"
    )

    # =============================
    # EXPORT CENTRALIZAT
    # =============================

    grouped_export = grouped.copy()
    for col in ["TOTAL_TRANS_AMOUNT", "TOTAL_FEE", "TOTAL_COMISION_CALCULAT"]:
        grouped_export[col] = grouped_export[col].apply(lambda x: f"{x:.2f}".replace(".", ","))

    csv_centralizat = grouped_export.to_csv(index=False, sep=";")

    st.download_button(
        "⬇️ Descarca centralizare",
        csv_centralizat,
        "centralizare_clienti.csv",
        "text/csv"
    )
