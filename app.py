import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Centralizator Tranzactii", layout="wide")
st.title("📊 Centralizator Tranzactii POS")

# Upload fisier principal
uploaded_file = st.file_uploader(
    "Incarca fisierul CSV de la banca",
    type=["csv"]
)

# Upload lista terminale optional
terminal_file = st.file_uploader(
    "Incarca lista TERMINAL_ID (optional)",
    type=["csv", "xlsx"]
)

if uploaded_file is not None:

    # Citire fisier robusta
    try:
        df = pd.read_csv(uploaded_file, sep=None, engine="python")
    except:
        df = pd.read_csv(uploaded_file, sep=";", encoding="latin1")

    # Curatare TRANS_AMOUNT
    if "TRANS_AMOUNT" in df.columns:
        df["TRANS_AMOUNT"] = (
            df["TRANS_AMOUNT"]
            .astype(str)
            .str.replace(".", "", regex=False)   # scoate punct mii
            .str.replace(",", ".", regex=False)  # transforma zecimale
        )
        df["TRANS_AMOUNT"] = pd.to_numeric(df["TRANS_AMOUNT"], errors="coerce")

    # Curatare FEE_AMOUNT
    if "FEE_AMOUNT" in df.columns:
        df["FEE_AMOUNT"] = (
            df["FEE_AMOUNT"]
            .astype(str)
            .str.replace("-", "", regex=False)   # scoate minus
            .str.replace(".", "", regex=False)   # scoate punct mii
            .str.replace(",", ".", regex=False)  # transforma zecimale
        )
        df["FEE_AMOUNT"] = pd.to_numeric(df["FEE_AMOUNT"], errors="coerce")

    # Filtrare dupa lista terminale daca exista
    if terminal_file is not None:
        if terminal_file.name.endswith(".csv"):
            terminals_df = pd.read_csv(terminal_file)
        else:
            terminals_df = pd.read_excel(terminal_file)

        terminal_list = terminals_df["TERMINAL_ID"].astype(str).tolist()
        df = df[df["TERMINAL_ID"].astype(str).isin(terminal_list)]
        st.success(f"Filtrare aplicata pentru {len(terminal_list)} terminale")

    # Selectam exact coloanele dorite
    coloane_export = [
        "TERMINAL_ID", "DEVICE_NAME", "DEVICE_CITY", "TRANSACTION_ID",
        "TRANS_DATE", "POSTING_DATE", "TRANS_AMOUNT", "CASHBACK_AMOUNT",
        "TRANS_CURR", "TARGET_TYPE", "TRANS_TYPE", "MESSAGE_TYPE",
        "REQUEST_CATEGORY", "CARD_NUMBER", "AUTH_CODE", "RET_REF_NUMBER",
        "FEE_AMOUNT", "FEE_CURRENCY", "CARD_PRODUCT_TYPE", "CARD_TYPE",
        "INSTL_NO", "INSTL_FEE_PERC", "CARD_ORGANIZATION", "ACCOUNT_NO"
    ]
    df_export = df[[col for col in coloane_export if col in df.columns]]

    st.subheader("📄 Date complete")
    st.dataframe(df_export, use_container_width=True)

    # Grupare per TERMINAL_ID + DEVICE_NAME
    grouped = df.groupby(
        ["TERMINAL_ID", "DEVICE_NAME"]
    ).agg(
        TRANS_AMOUNT=("TRANS_AMOUNT", "sum"),
        FEE_AMOUNT=("FEE_AMOUNT", "sum")
    ).reset_index()

    # Calcul medie comision per client
    grouped["MEDIE_COMISION"] = (grouped["FEE_AMOUNT"] / grouped["TRANS_AMOUNT"])

    # Rotunjire valori
    grouped["TRANS_AMOUNT"] = grouped["TRANS_AMOUNT"].round(2)
    grouped["FEE_AMOUNT"] = grouped["FEE_AMOUNT"].round(2)
    grouped["MEDIE_COMISION"] = grouped["MEDIE_COMISION"].round(4)

    st.subheader("📊 Centralizare per TERMINAL_ID + DEVICE_NAME")
    st.dataframe(grouped, use_container_width=True)

    # Export detaliat
    csv_detaliat = df_export.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Descarca fisierul detaliat",
        csv_detaliat,
        "export_detaliat.csv",
        "text/csv"
    )

    # Export centralizare
    csv_centralizat = grouped.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Descarca centralizarea",
        csv_centralizat,
        "centralizare_terminal_device.csv",
        "text/csv"
    )
