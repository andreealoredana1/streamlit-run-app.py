import streamlit as st
import pandas as pd

st.set_page_config(page_title="Centralizator Tranzactii", layout="wide")

st.title("📊 Centralizator Tranzactii POS")

# Upload fisier principal
uploaded_file = st.file_uploader("Incarca fisierul CSV de la banca", type=["csv"])

# Upload lista terminale
terminal_file = st.file_uploader("Incarca lista TERMINAL_ID (optional)", type=["csv", "xlsx"])

if uploaded_file:

    df = pd.read_csv(uploaded_file)

    # Curatare coloane numerice
    df["TRANS_AMOUNT"] = pd.to_numeric(df["TRANS_AMOUNT"], errors="coerce")
    df["FEE_AMOUNT"] = pd.to_numeric(df["FEE_AMOUNT"], errors="coerce")

    # Daca exista lista de terminale
    if terminal_file:
        if terminal_file.name.endswith(".csv"):
            terminals_df = pd.read_csv(terminal_file)
        else:
            terminals_df = pd.read_excel(terminal_file)

        terminal_list = terminals_df["TERMINAL_ID"].astype(str).tolist()
        df = df[df["TERMINAL_ID"].astype(str).isin(terminal_list)]

        st.success(f"Filtrare aplicata pentru {len(terminal_list)} terminale")

    # Grupare
    grouped = df.groupby("TERMINAL_ID").agg(
        TOTAL_TRANS_AMOUNT=("TRANS_AMOUNT", "sum"),
        TOTAL_FEE_AMOUNT=("FEE_AMOUNT", "sum"),
        NR_TRANZACTII=("FEE_AMOUNT", "count"),
        MEDIA_FEE_AMOUNT=("FEE_AMOUNT", "mean")
    ).reset_index()

    st.subheader("Rezultate centralizate")
    st.dataframe(grouped, use_container_width=True)

    # Total general
    st.subheader("Total General")
    total_trans = grouped["TOTAL_TRANS_AMOUNT"].sum()
    total_fee = grouped["TOTAL_FEE_AMOUNT"].sum()

    col1, col2 = st.columns(2)
    col1.metric("Total TRANS_AMOUNT", f"{total_trans:,.2f}")
    col2.metric("Total FEE_AMOUNT", f"{total_fee:,.2f}")

    # Export
    csv = grouped.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Descarca rezultatele",
        csv,
        "centralizator_rezultate.csv",
        "text/csv",
    )

# Citire automata separator
stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8"))
df = pd.read_csv(stringio, sep=None, engine="python")



  
        stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8"))
        df = pd.read_csv(stringio, sep=None, engine="python")
    
        
            stringio = io.StringIO(uploaded_file.getvalue().decode("utf-16"))
            df = pd.read_csv(stringio, sep=";")
     
            df = pd.read_csv(uploaded_file, sep=";", encoding="latin1")
