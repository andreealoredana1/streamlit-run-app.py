import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Centralizator Tranzactii", layout="wide")

st.title("Centralizator Tranzactii POS")

uploaded_file = st.file_uploader(
    "Incarca fisierul CSV de la banca",
    type=["csv"]
)

if uploaded_file is not None:

    # Citire fisier cu detectare automata separator
    try:
        df = pd.read_csv(uploaded_file, sep=None, engine="python")
    except:
        df = pd.read_csv(uploaded_file, sep=";", encoding="latin1")

    # Curatare valori numerice
    if "TRANS_AMOUNT" in df.columns:
        df["TRANS_AMOUNT"] = (
            df["TRANS_AMOUNT"]
            .astype(str)
            .str.replace(".", "", regex=False)
            .str.replace(",", ".", regex=False)
        )
        df["TRANS_AMOUNT"] = pd.to_numeric(df["TRANS_AMOUNT"], errors="coerce")

    if "FEE_AMOUNT" in df.columns:
        df["FEE_AMOUNT"] = (
            df["FEE_AMOUNT"]
            .astype(str)
            .str.replace(".", "", regex=False)
            .str.replace(",", ".", regex=False)
        )
        df["FEE_AMOUNT"] = pd.to_numeric(df["FEE_AMOUNT"], errors="coerce")

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

    st.subheader("Date complete")
    st.dataframe(df_export, use_container_width=True)

    # Grupare dupa DEVICE_NAME
    grouped = df.groupby("DEVICE_NAME").agg(
        TOTAL_TRANS_AMOUNT=("TRANS_AMOUNT", "sum"),
        TOTAL_FEE_AMOUNT=("FEE_AMOUNT", "sum"),
        NR_TRANZACTII=("TRANSACTION_ID", "count"),
        TERMINALE_DISTINCTE=("TERMINAL_ID", "nunique")
    ).reset_index()

    # Calcul medii
    grouped["MEDIA_FEE_PER_TRANZACTIE"] = (
        grouped["TOTAL_FEE_AMOUNT"] / grouped["NR_TRANZACTII"]
    )

    grouped["MEDIA_FEE_PER_TERMINAL"] = (
        grouped["TOTAL_FEE_AMOUNT"] / grouped["TERMINALE_DISTINCTE"]
    )

    st.subheader("Centralizare pe DEVICE_NAME")
    st.dataframe(grouped, use_container_width=True)

    # Export detaliat
    csv_detaliat = df_export.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Descarca fisierul detaliat",
        csv_detaliat,
        "export_detaliat.csv",
        "text/csv"
    )

    # Export centralizat
    csv_centralizat = grouped.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Descarca centralizarea",
        csv_centralizat,
        "centralizare_device_name.csv",
        "text/csv"
    )
