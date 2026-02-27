import streamlit as st
import pandas as pd
import json
import os

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
# Sidebar: Adaugare manuala TID
# -----------------------------
st.sidebar.header("➕ Adauga TID manual")
with st.sidebar.form("form_tid"):
    new_tid = st.text_input("TERMINAL_ID")
    new_device = st.text_input("DEVICE_NAME")
    submitted = st.form_submit_button("Adauga")
    if submitted:
        if new_tid and new_device:
            tid_list[new_tid] = new_device
            save_json(TID_FILE, tid_list)
            st.success(f"TID {new_tid} salvat cu DEVICE_NAME {new_device}")

# -----------------------------
# Sidebar: Seteaza comisioane
# -----------------------------
st.sidebar.header("💰 Seteaza comisioane per client")
with st.sidebar.form("form_com"):
    device = st.text_input("DEVICE_NAME pentru comision")
    com_10 = st.number_input("Comision ≥10 RON (%)", min_value=0.0, format="%.2f")
    com_10m = st.number_input("Comision <10 RON (%)", min_value=0.0, format="%.2f")
    submitted_com = st.form_submit_button("Salveaza comision")
    if submitted_com:
        if device:
            comisioane[device] = {"10+": com_10, "<10": com_10m}
            save_json(COMISION_FILE, comisioane)
            st.success(f"Comisioane pentru {device} salvate!")

# -----------------------------
# Sidebar: Administrare TID-uri
# -----------------------------
st.sidebar.header("🛠 Administrare TID-uri existente")
if st.sidebar.button("Editeaza / Sterge TID-uri"):
    st.subheader("Lista TID-uri salvate")
    tid_df = pd.DataFrame(list(tid_list.items()), columns=["TERMINAL_ID", "DEVICE_NAME"])
    edited_df = st.data_editor(
        tid_df,
        num_rows="dynamic",
        use_container_width=True,
        key="editor_tid"
    )
    st.write("✅ Apasa butonul pentru a salva modificarile")
    if st.button("Salveaza TID-uri modificate"):
        tid_list = dict(zip(edited_df["TERMINAL_ID"], edited_df["DEVICE_NAME"]))
        save_json(TID_FILE, tid_list)
        st.success("TID-urile au fost actualizate si salvate cu succes!")

# -----------------------------
# Upload CSV
# -----------------------------
uploaded_file = st.file_uploader("Incarca fisierul CSV de la banca", type=["csv"])
if uploaded_file is not None:
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
                .str.replace(".", "", regex=False)
                .str.replace(",", ".", regex=False)
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

    grouped["TOTAL_TRANS_AMOUNT"] = grouped["TOTAL_TRANS_AMOUNT"].round(2)
    grouped["TOTAL_COMISION"] = grouped["TOTAL_COMISION"].round(2)
    grouped["TOTAL_FEE"] = grouped["TOTAL_FEE"].round(2)

    # -----------------------------
    # Afisare in Streamlit
    # -----------------------------
    st.subheader("📊 Centralizare per client (TID + DEVICE_NAME)")
    st.dataframe(grouped, use_container_width=True)

    # -----------------------------
    # Export CSV detaliat
    # -----------------------------
    csv_detaliat = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Descarca fisierul detaliat",
        csv_detaliat,
        "export_detaliat.csv",
        "text/csv"
    )

    # -----------------------------
    # Export CSV centralizare
    # -----------------------------
    csv_centralizat = grouped.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Descarca centralizarea",
        csv_centralizat,
        "centralizare_clienti.csv",
        "text/csv"
    )
