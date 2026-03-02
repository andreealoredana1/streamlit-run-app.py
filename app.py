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
# BAZA DE DATE SQLITE (COMISIOANE)
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

# =============================
# SIDEBAR - TID
# =============================
st.sidebar.header("🏷 Gestionare TID-uri")

# 🔹 Adaugare manuala
with st.sidebar.form("form_tid"):
    new_tid = st.text_input("TERMINAL_ID")
    new_device = st.text_input("DEVICE_NAME")
    submitted = st.form_submit_button("Adauga TID manual")

    if submitted and new_tid and new_device:
        tid_list[str(new_tid)] = new_device
        save_json(TID_FILE, tid_list)
        st.sidebar.success("TID salvat manual!")

# 🔹 Import din Excel
st.sidebar.markdown("---")
st.sidebar.subheader("📥 Import TID din Excel")

uploaded_tid_file = st.sidebar.file_uploader(
    "Incarca fisier Excel (TERMINAL_ID, DEVICE_NAME)",
    type=["xlsx"]
)

if uploaded_tid_file is not None:
    try:
        tid_excel = pd.read_excel(uploaded_tid_file)

        if "TERMINAL_ID" in tid_excel.columns and "DEVICE_NAME" in tid_excel.columns:

            tid_excel["TERMINAL_ID"] = tid_excel["TERMINAL_ID"].astype(str)
            tid_excel["DEVICE_NAME"] = tid_excel["DEVICE_NAME"].astype(str)

            for _, row in tid_excel.iterrows():
                tid_list[row["TERMINAL_ID"]] = row["DEVICE_NAME"]

            save_json(TID_FILE, tid_list)
            st.sidebar.success(f"Import reusit! {len(tid_excel)} TID-uri salvate.")

        else:
            st.sidebar.error("Fisierul trebuie sa contina: TERMINAL_ID si DEVICE_NAME")

    except Exception as e:
        st.sidebar.error(f"Eroare la citire: {e}")

# =============================
# SIDEBAR - COMISIOANE
# =============================
st.sidebar.markdown("---")
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

# =============================
# UPLOAD CSV BANCA
# =============================
uploaded_file = st.file_uploader("📂 Incarca fisier CSV banca", type=["csv"])

if uploaded_file is not None:

    df = pd.read_csv(uploaded_file, sep=None, engine="python")

    # VALIDARE
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

    # MAPARE AUTOMATA TID -> DEVICE_NAME
    df["TERMINAL_ID"] = df["TERMINAL_ID"].astype(str)
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

    # GRAFIC
    st.markdown("### 📈 Comisioane per client")
    st.bar_chart(
        grouped.set_index("DEVICE_NAME")["TOTAL_FEE"]
    )

    # EXPORT CSV
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
