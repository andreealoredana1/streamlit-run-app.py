import streamlit as st
import pandas as pd
import json
import os

# -----------------------------
# Setari pagina
# -----------------------------
st.set_page_config(page_title="Centralizator Tranzactii POS", layout="wide")
st.title("📊 Centralizator Tranzactii POS")

# -----------------------------
# Fisiere persistenta
# -----------------------------
TID_FILE = "tid_list.json"
COMISION_FILE = "comisioane.json"

def load_json(file, default):
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        return default

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

tid_list = load_json(TID_FILE, {})          # TERMINAL_ID -> DEVICE_NAME
comisioane = load_json(COMISION_FILE, {})   # DEVICE_NAME -> {"10+": %, "<10": %}

# -----------------------------
# Sidebar: Navigare
# -----------------------------
st.sidebar.header("⚙️ Meniu Principal")

# -----------------------------
# 1️⃣ Buton incarcare XLSX cu TID-uri
# -----------------------------
st.sidebar.subheader("📁 TID-uri")
uploaded_tid_file = st.sidebar.file_uploader(
    "Incarca XLSX cu TID-uri si DEVICE_NAME",
    type=["xlsx"],
    key="upload_tid_xlsx"
)
if uploaded_tid_file is not None:
    tid_df = pd.read_excel(uploaded_tid_file)
    if "TERMINAL_ID" in tid_df.columns and "DEVICE_NAME" in tid_df.columns:
        tid_new = dict(zip(tid_df["TERMINAL_ID"], tid_df["DEVICE_NAME"]))
        tid_list.update(tid_new)
        save_json(TID_FILE, tid_list)
        st.success(f"{len(tid_new)} TID-uri incarcate si salvate!")
    else:
        st.error("Fisierul XLSX trebuie sa contina coloanele: TERMINAL_ID si DEVICE_NAME")

# -----------------------------
# 2️⃣ Buton incarcare XLSX cu Comisioane
# -----------------------------
st.sidebar.subheader("💰 Comisioane")
uploaded_com_file = st.sidebar.file_uploader(
    "Incarca XLSX cu DEVICE_NAME si comisioane",
    type=["xlsx"],
    key="upload_com_xlsx"
)
if uploaded_com_file is not None:
    com_df = pd.read_excel(uploaded_com_file)
    if {"DEVICE_NAME", "COM_10", "COM_LT10"}.issubset(com_df.columns):
        for _, row in com_df.iterrows():
            comisioane[row["DEVICE_NAME"]] = {"10+": float(row["COM_10"]), "<10": float(row["COM_LT10"])}
        save_json(COMISION_FILE, comisioane)
        st.success(f"{len(com_df)} comisioane incarcate si salvate!")
    else:
        st.error("Fisierul XLSX trebuie sa contina coloanele: DEVICE_NAME, COM_10, COM_LT10")

# -----------------------------
# 3️⃣ Administrare TID-uri existente
# -----------------------------
st.sidebar.subheader("🛠 Administrare TID-uri")
if st.sidebar.button("Editeaza TID-uri existente"):
    tid_df = pd.DataFrame(list(tid_list.items()), columns=["TERMINAL_ID", "DEVICE_NAME"])
    edited_df = st.data_editor(tid_df, num_rows="dynamic", use_container_width=True)
    if st.button("Salveaza modificari TID-uri"):
        tid_list = dict(zip(edited_df["TERMINAL_ID"], edited_df["DEVICE_NAME"]))
        save_json(TID_FILE, tid_list)
        st.success("TID-urile au fost actualizate!")

# -----------------------------
# 4️⃣ Upload CSV tranzactii
# -----------------------------
uploaded_file = st.file_uploader("📂 Incarca fisierul CSV de la banca", type=["csv"])
if uploaded_file is not None:
    # Citire CSV cu separator automat
    try:
        df = pd.read_csv(uploaded_file, sep=None, engine="python")
    except:
        df = pd.read_csv(uploaded_file, sep=";", encoding="latin1")

    # -----------------------------
    # Curatare numeric
    # -----------------------------
    for col in ["TRANS_AMOUNT", "FEE_AMOUNT"]:
        if col in df.columns:
            df[col] = (
                df[col].astype(str)
                .str.replace("-", "", regex=False)
                .str.replace(",", ".", regex=False)
                .str.replace(r"\s", "", regex=True)
            )
            df[col] = pd.to_numeric(df[col], errors="coerce").round(2)

    # -----------------------------
    # Adaugare DEVICE_NAME din lista TID
    # -----------------------------
    df["DEVICE_NAME"] = df["TERMINAL_ID"].map(tid_list).fillna(df.get("DEVICE_NAME", ""))

    # -----------------------------
    # Calcul comision per tranzactie
    # -----------------------------
    def calc_comision(row):
        device = row["DEVICE_NAME"]
        amt = row["TRANS_AMOUNT"]
        if device in comisioane:
            if amt >= 10:
                return round(amt * comisioane[device]["10+"] / 100, 2)
            else:
                return round(amt * comisioane[device]["<10"] / 100, 2)
        else:
            # Comision default daca clientul nu are setari
            if amt >= 10:
                return round(amt * 1 / 100, 2)
            else:
                return round(amt * 2 / 100, 2)

    df["COMISION_CALCULAT"] = df.apply(calc_comision, axis=1)

    # -----------------------------
    # Grupare per TERMINAL_ID + DEVICE_NAME
    # -----------------------------
    grouped = df.groupby(["TERMINAL_ID", "DEVICE_NAME"]).agg(
        TOTAL_TRANS_AMOUNT=("TRANS_AMOUNT", "sum"),
        TOTAL_COMISION=("COMISION_CALCULAT", "sum"),
        NR_TRANZACTII=("TRANSACTION_ID", "count"),
        TOTAL_FEE=("FEE_AMOUNT", "sum")
    ).reset_index()

    # -----------------------------
    # Format numeric cu 2 zecimale
    # -----------------------------
    grouped["TOTAL_TRANS_AMOUNT"] = grouped["TOTAL_TRANS_AMOUNT"].map("{:.2f}".format)
    grouped["TOTAL_COMISION"] = grouped["TOTAL_COMISION"].map("{:.2f}".format)
    grouped["TOTAL_FEE"] = grouped["TOTAL_FEE"].map("{:.2f}".format)

    # -----------------------------
    # Afisare in Streamlit
    # -----------------------------
    st.subheader("📊 Centralizare per client (TID + DEVICE_NAME)")
    st.dataframe(grouped, use_container_width=True)

    # -----------------------------
    # Export CSV detaliat
    # -----------------------------
    csv_detaliat = df.to_csv(index=False, sep=";", encoding="utf-8")
    st.download_button(
        "⬇️ Descarca fisierul detaliat",
        csv_detaliat,
        "export_detaliat.csv",
        "text/csv"
    )

    # -----------------------------
    # Export CSV centralizare
    # -----------------------------
    csv_centralizat = grouped.to_csv(index=False, sep=";", encoding="utf-8")
    st.download_button(
        "⬇️ Descarca centralizarea",
        csv_centralizat,
        "centralizare_clienti.csv",
        "text/csv"
    )
