import streamlit as st
import pandas as pd
import json
import os
import matplotlib.pyplot as plt

st.set_page_config(page_title="Centralizator POS ENTERPRISE", layout="wide")
st.title("🏦 Centralizator Tranzactii POS - ENTERPRISE")

TID_FILE = "tid_list.json"
COMISION_FILE = "comisioane.json"

# ===============================
# JSON LOAD/SAVE
# ===============================

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

# ===============================
# IMPORT TID
# ===============================

st.sidebar.header("📥 Import TID-uri")

uploaded_tid = st.sidebar.file_uploader("CSV TID", type=["csv"])

if uploaded_tid:
    tid_df = pd.read_csv(uploaded_tid, sep=None, engine="python")
    tid_df.columns = tid_df.columns.str.lower()

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
        st.sidebar.error("Coloane TID / DEVICE lipsa.")

# ===============================
# IMPORT COMISIOANE
# ===============================

st.sidebar.markdown("---")
st.sidebar.header("💰 Import Comisioane")

uploaded_com = st.sidebar.file_uploader("CSV Comisioane", type=["csv"])

if uploaded_com:
    com_df = pd.read_csv(uploaded_com, sep=None, engine="python", header=None)

    current_client = None

    for _, row in com_df.iterrows():
        values = [str(x).strip() for x in row if pd.notna(x)]
        if not values:
            continue

        if len(values) >= 3 and "%" not in values[1]:
            try:
                comisioane[values[0]] = {
                    "10+": float(values[1].replace(",", ".")),
                    "<10": float(values[2].replace(",", "."))
                }
                continue
            except:
                pass

        if values[0] != "":
            current_client = values[0]

        for val in values:
            if "%" in val:
                procent = float(val.replace("%", "").replace(",", "."))
                if "mare" in " ".join(values).lower():
                    comisioane.setdefault(current_client, {})["10+"] = procent
                if "mica" in " ".join(values).lower():
                    comisioane.setdefault(current_client, {})["<10"] = procent

    save_json(COMISION_FILE, comisioane)
    st.sidebar.success("Comisioane importate!")

# ===============================
# UPLOAD CSV BANCA
# ===============================

uploaded_file = st.file_uploader("📂 Incarca fisier CSV banca", type=["csv"])

if uploaded_file:

    df = pd.read_csv(uploaded_file, sep=None, engine="python")
    df.columns = df.columns.str.lower()

    tid_col = next((c for c in df.columns if "terminal" in c or "tid" in c), None)
    amount_col = next((c for c in df.columns if "amount" in c or "suma" in c), None)
    fee_col = next((c for c in df.columns if "fee" in c or "comision" in c), None)
    date_col = next((c for c in df.columns if "date" in c or "data" in c), None)

    if not tid_col or not amount_col or not fee_col:
        st.error("Nu pot detecta coloanele necesare.")
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

    # ALERTA daca banca ia mai mult
    if (df["DIFERENTA"] > 0.01).any():
        st.error("⚠️ ATENTIE: Exista tranzactii unde banca a luat mai mult!")
    else:
        st.success("✔ Comisioanele sunt corecte.")

    # CENTRALIZARE
    grouped = df.groupby("CLIENT").agg(
        TOTAL_TRANZACTII=(amount_col, "sum"),
        TOTAL_FEE_BANCA=(fee_col, "sum"),
        TOTAL_COMISION_CALCULAT=("COMISION_CALCULAT", "sum"),
        TOTAL_DIFERENTA=("DIFERENTA", "sum"),
        NR_TRANZACTII=(amount_col, "count")
    ).reset_index().round(2)

    st.subheader("📊 Centralizare per CLIENT")
    st.dataframe(grouped, use_container_width=True)

    # TOTAL GENERAL
    total_tr = grouped["TOTAL_TRANZACTII"].sum()
    total_fee = grouped["TOTAL_FEE_BANCA"].sum()
    procent_real = round((total_fee / total_tr) * 100, 2) if total_tr > 0 else 0

    st.markdown("---")
    st.subheader("📌 TOTAL GENERAL")

    c1, c2, c3 = st.columns(3)
    c1.metric("Total tranzactii", f"{total_tr:,.2f}")
    c2.metric("Total comisioane banca", f"{total_fee:,.2f}")
    c3.metric("Procent mediu real", f"{procent_real}%")

    # GRAFIC
    st.subheader("📈 Grafic Comisioane per Client")
    fig, ax = plt.subplots()
    ax.bar(grouped["CLIENT"], grouped["TOTAL_FEE_BANCA"])
    ax.set_xticklabels(grouped["CLIENT"], rotation=45, ha="right")
    st.pyplot(fig)

    # ISTORIC PE ZI (daca exista data)
    if date_col:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        daily = df.groupby(df[date_col].dt.date)[fee_col].sum()

        st.subheader("📅 Comisioane pe zile")
        fig2, ax2 = plt.subplots()
        ax2.plot(daily.index, daily.values)
        st.pyplot(fig2)

    # EXPORT
    st.download_button(
        "⬇️ Descarca centralizare",
        grouped.to_csv(index=False, sep=";"),
        "centralizare_enterprise.csv",
        "text/csv"
    )
