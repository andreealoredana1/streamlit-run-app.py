import streamlit as st
import pandas as pd
import json
import os

st.set_page_config(page_title="Centralizator POS", layout="wide")
st.title("📊 Centralizator Tranzactii POS")

TID_FILE = "tid_list.json"
COMISION_FILE = "comisioane.json"

# =========================
# LOAD / SAVE JSON
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

# =====================================================
# 🔵 TID SECTION
# =====================================================

st.sidebar.header("📥 Import / Editeaza TID-uri")

uploaded_tid = st.sidebar.file_uploader("Import CSV TID", type=["csv"], key="tid")

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
            st.sidebar.success("TID-uri importate!")
        else:
            st.sidebar.error("CSV trebuie sa contina TERMINAL_ID si DEVICE_NAME")
    except Exception as e:
        st.sidebar.error(f"Eroare: {e}")

if st.sidebar.checkbox("Vezi / Editeaza TID-uri"):
    tid_df = pd.DataFrame(list(tid_list.items()), columns=["TERMINAL_ID", "DEVICE_NAME"])
    edited_tid = st.sidebar.data_editor(tid_df, num_rows="dynamic")

    if st.sidebar.button("Salveaza TID-uri"):
        tid_list = dict(zip(
            edited_tid["TERMINAL_ID"].astype(str),
            edited_tid["DEVICE_NAME"].astype(str)
        ))
        save_json(TID_FILE, tid_list)
        st.sidebar.success("TID-uri salvate!")

# =====================================================
# 🏦 UPLOAD CSV BANCA
# =====================================================

st.markdown("---")
uploaded_file = st.file_uploader("📂 Incarca fisier CSV banca", type=["csv"])

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file, sep=None, engine="python")

        # 🔵 AFISARE ORIGINAL
        st.subheader("📄 Fisier Original (nemodificat)")
        st.dataframe(df, use_container_width=True)

        # ===============================
        # CALCUL PE COPIE
        # ===============================

        calc_df = df.copy()
        calc_df.columns = calc_df.columns.str.lower()

        tid_col = next((c for c in calc_df.columns if "terminal" in c or "tid" in c), None)
        amount_col = next((c for c in calc_df.columns if "amount" in c or "trans" in c), None)
        fee_col = next((c for c in calc_df.columns if "fee" in c), None)

        if not tid_col or not amount_col or not fee_col:
            st.error("Nu pot detecta coloanele TERMINAL / TRANS_AMOUNT / FEE")
            st.stop()

        # Curatare doar pentru calcul
        for col in [amount_col, fee_col]:
            calc_df[col] = (
                calc_df[col]
                .astype(str)
                .str.replace("-", "", regex=False)
                .str.replace(".", "", regex=False)
                .str.replace(",", ".", regex=False)
            )
            calc_df[col] = pd.to_numeric(calc_df[col], errors="coerce")

        # Asociere CLIENT din TID
        calc_df["CLIENT"] = calc_df[tid_col].astype(str).map(tid_list).fillna("NEASOCIAT")

        # ===============================
        # TOTAL PER CLIENT
        # ===============================

        grouped = calc_df.groupby("CLIENT").agg(
            TOTAL_TRANS_AMOUNT=(amount_col, "sum"),
            TOTAL_FEE=(fee_col, "sum")
        ).reset_index()

        grouped["PROCENT_REAL_%"] = (
            (grouped["TOTAL_FEE"] / grouped["TOTAL_TRANS_AMOUNT"]) * 100
        ).round(2)

        grouped = grouped.round(2)

        st.markdown("---")
        st.subheader("📊 Total TRANS_AMOUNT + Procent Real per Client")
        st.dataframe(grouped, use_container_width=True)

        # ===============================
        # TOTAL GENERAL
        # ===============================

        total_trans = grouped["TOTAL_TRANS_AMOUNT"].sum()
        total_fee = grouped["TOTAL_FEE"].sum()

        procent_general = round((total_fee / total_trans) * 100, 2) if total_trans > 0 else 0

        st.markdown("---")
        st.subheader("📌 TOTAL GENERAL ZI")

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Tranzactii", f"{total_trans:,.2f}")
        col2.metric("Total Fee", f"{total_fee:,.2f}")
        col3.metric("Procent Mediu Real", f"{procent_general}%")

        # ===============================
        # EXPORT CENTRALIZARE
        # ===============================

        st.download_button(
            "⬇️ Descarca Centralizare",
            grouped.to_csv(index=False, sep=";"),
            "centralizare.csv",
            "text/csv"
        )

    except Exception as e:
        st.error(f"Eroare la procesare: {e}")
