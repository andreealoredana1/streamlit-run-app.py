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
# Sidebar: TAB-uri vizuale
# -----------------------------
st.sidebar.header("⚙️ Navigare Secțiuni")
tab = st.sidebar.radio("Selectează secțiunea", ["📁 TID-uri", "💰 Comisioane", "📊 Tranzacții"])

# -----------------------------
# TAB 1: TID-uri
# -----------------------------
if tab == "📁 TID-uri":
    st.subheader("📁 Administrare TID-uri")

    # Upload XLSX TID-uri
    uploaded_tid_file = st.file_uploader(
        "Încarcă XLSX cu TID-uri și DEVICE_NAME",
        type=["xlsx"]
    )
    if uploaded_tid_file is not None:
        try:
            tid_df = pd.read_excel(uploaded_tid_file)
            if "TERMINAL_ID" in tid_df.columns and "DEVICE_NAME" in tid_df.columns:
                tid_new = dict(zip(tid_df["TERMINAL_ID"], tid_df["DEVICE_NAME"]))
                tid_list.update(tid_new)
                save_json(TID_FILE, tid_list)
                st.success(f"{len(tid_new)} TID-uri încărcate și salvate cu succes!")
            else:
                st.error("Fișierul XLSX trebuie să conțină coloanele: TERMINAL_ID și DEVICE_NAME")
        except ImportError:
            st.error("Nu ai instalat openpyxl. Rulează: pip install openpyxl")

    # Administrare TID-uri existente
    tid_df_view = pd.DataFrame(list(tid_list.items()), columns=["TERMINAL_ID", "DEVICE_NAME"])
    edited_df = st.data_editor(
        tid_df_view,
        num_rows="dynamic",
        use_container_width=True
    )
    if st.button("Salvează modificările TID"):
        tid_list = dict(zip(edited_df["TERMINAL_ID"], edited_df["DEVICE_NAME"]))
        save_json(TID_FILE, tid_list)
        st.success("TID-urile au fost actualizate și salvate cu succes!")

# -----------------------------
# TAB 2: Comisioane
# -----------------------------
elif tab == "💰 Comisioane":
    st.subheader("💰 Setare Comisioane per client")

    uploaded_com_file = st.file_uploader(
        "Încarcă XLSX cu DEVICE_NAME și comisioane",
        type=["xlsx"]
    )
    if uploaded_com_file is not None:
        try:
            com_df = pd.read_excel(uploaded_com_file)
            if {"DEVICE_NAME", "COM_10", "COM_LT10"}.issubset(com_df.columns):
                for _, row in com_df.iterrows():
                    comisioane[row["DEVICE_NAME"]] = {"10+": float(row["COM_10"]), "<10": float(row["COM_LT10"])}
                save_json(COMISION_FILE, comisioane)
                st.success(f"{len(com_df)} comisioane încărcate și salvate cu succes!")
            else:
                st.error("Fisierul XLSX trebuie să conțină coloanele: DEVICE_NAME, COM_10, COM_LT10")
        except ImportError:
            st.error("Nu ai instalat openpyxl. Rulează: pip install openpyxl")

    # Editare manuală comisioane
    com_df_view = pd.DataFrame([
        {"DEVICE_NAME": k, "COM_10": v["10+"], "COM_LT10": v["<10"]}
        for k, v in comisioane.items()
    ])
    edited_com = st.data_editor(
        com_df_view,
        num_rows="dynamic",
        use_container_width=True
    )
    if st.button("Salvează modificările comisioane"):
        comisioane = {row["DEVICE_NAME"]: {"10+": float(row["COM_10"]), "<10": float(row["COM_LT10"])} for _, row in edited_com.iterrows()}
        save_json(COMISION_FILE, comisioane)
        st.success("Comisioanele au fost actualizate și salvate cu succes!")

# -----------------------------
# TAB 3: Tranzactii
# -----------------------------
elif tab == "📊 Tranzacții":
    st.subheader("📊 Upload CSV Tranzacții")

    uploaded_file = st.file_uploader("Încarcă fișierul CSV de la bancă", type=["csv"])
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file, sep=None, engine="python")
        except:
            df = pd.read_csv(uploaded_file, sep=";", encoding="latin1")

        # Curățare numeric
        for col in ["TRANS_AMOUNT", "FEE_AMOUNT"]:
            if col in df.columns:
                df[col] = (
                    df[col].astype(str)
                    .str.replace("-", "", regex=False)
                    .str.replace(".", "", regex=False)
                    .str.replace(",", ".", regex=False)
                )
                df[col] = pd.to_numeric(df[col], errors="coerce").round(2)

        # Adăugare DEVICE_NAME din TID-uri
        df["DEVICE_NAME"] = df["TERMINAL_ID"].map(tid_list).fillna(df.get("DEVICE_NAME", ""))

        # Calcul comision per tranzactie
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

        # Grupare per TERMINAL_ID + DEVICE_NAME
        grouped = df.groupby(["TERMINAL_ID", "DEVICE_NAME"]).agg(
            TOTAL_TRANS_AMOUNT=("TRANS_AMOUNT", "sum"),
            TOTAL_COMISION=("COMISION_CALCULAT", "sum"),
            NR_TRANZACTII=("TRANSACTION_ID", "count"),
            TOTAL_FEE=("FEE_AMOUNT", "sum")
        ).reset_index()

        grouped["TOTAL_TRANS_AMOUNT"] = grouped["TOTAL_TRANS_AMOUNT"].round(2)
        grouped["TOTAL_COMISION"] = grouped["TOTAL_COMISION"].round(2)
        grouped["TOTAL_FEE"] = grouped["TOTAL_FEE"].round(2)

        st.subheader("📊 Centralizare per client (TID + DEVICE_NAME)")
        st.dataframe(grouped, use_container_width=True)

        # Export CSV detaliat
        csv_detaliat = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Descarcă fișierul detaliat",
            csv_detaliat,
            "export_detaliat.csv",
            "text/csv"
        )

        # Export CSV centralizare
        csv_centralizat = grouped.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Descarcă centralizarea",
            csv_centralizat,
            "centralizare_clienti.csv",
            "text/csv"
        )
