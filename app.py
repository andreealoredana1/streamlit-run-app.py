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
# Sidebar: Navigare butoane mari
# -----------------------------
st.sidebar.header("⚙️ Meniu Principal")

if st.sidebar.button("➕ Adauga TID manual", key="btn_add_tid"):
    st.subheader("➕ Adauga TID manual")
    new_tid = st.text_input("TERMINAL_ID")
    new_device = st.text_input("DEVICE_NAME")
    if st.button("Salveaza TID"):
        if new_tid and new_device:
            tid_list[new_tid] = new_device
            save_json(TID_FILE, tid_list)
            st.success(f"TID {new_tid} salvat cu DEVICE_NAME {new_device}")

if st.sidebar.button("💰 Seteaza comisioane per client", key="btn_set_com"):
    st.subheader("💰 Seteaza comisioane per client")
    device = st.text_input("DEVICE_NAME pentru comision")
    com_10 = st.number_input("Comision ≥10 RON (%)", min_value=0.0, format="%.2f")
    com_10m = st.number_input("Comision <10 RON (%)", min_value=0.0, format="%.2f")
    if st.button("Salveaza comision"):
        if device:
            comisioane[device] = {"10+": com_10, "<10": com_10m}
            save_json(COMISION_FILE, comisioane)
            st.success(f"Comisioane pentru {device} salvate!")

if st.sidebar.button("🛠 Administrare TID-uri existente", key="btn_manage_tid"):
    st.subheader("🛠 Administrare TID-uri existente")
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
# Sidebar: Upload XLSX TID-uri
# -----------------------------
st.sidebar.header("📁 Incarca lista TID-uri XLSX")
uploaded_tid_file = st.sidebar.file_uploader(
    "Incarca fisier XLSX cu TID-uri",
    type=["xlsx"],
    key="upload_tid"
)
if uploaded_tid_file is not None:
    tid_df = pd.read_excel(uploaded_tid_file)
    if "TERMINAL_ID" in tid_df.columns and "DEVICE_NAME" in tid_df.columns:
        tid_new = dict(zip(tid_df["TERMINAL_ID"], tid_df["DEVICE_NAME"]))
        tid_list.update(tid_new)
        save_json(TID_FILE, tid_list)
        st.success(f"{len(tid_new)} TID-uri incarcate si salvate cu succes!")
    else:
        st.error("Fisierul XLSX trebuie sa contina coloanele: TERMINAL_ID si DEVICE_NAME")
