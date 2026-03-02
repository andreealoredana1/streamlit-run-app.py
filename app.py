# =============================
# SIDEBAR - IMPORT TID INTELIGENT
# =============================

st.sidebar.header("📥 Import TID (format liber)")

uploaded_tid = st.sidebar.file_uploader(
    "Incarca fisier CSV cu TID-uri",
    type=["csv"]
)

if uploaded_tid:
    try:
        # Detectare automata separator
        tid_df = pd.read_csv(uploaded_tid, sep=None, engine="python")

        # Curatare nume coloane
        tid_df.columns = (
            tid_df.columns
            .str.strip()
            .str.lower()
            .str.replace(" ", "")
            .str.replace("_", "")
        )

        # Detectare coloana TID
        possible_tid_cols = [
            col for col in tid_df.columns
            if "terminal" in col or "tid" in col or "cod" in col
        ]

        # Detectare coloana DEVICE_NAME
        possible_name_cols = [
            col for col in tid_df.columns
            if "device" in col or "firma" in col or "nume" in col or "client" in col or "societate" in col
        ]

        if possible_tid_cols and possible_name_cols:

            tid_col = possible_tid_cols[0]
            name_col = possible_name_cols[0]

            tid_df[tid_col] = tid_df[tid_col].astype(str)
            tid_df[name_col] = tid_df[name_col].astype(str)

            for _, row in tid_df.iterrows():
                tid_list[row[tid_col]] = row[name_col]

            save_json(TID_FILE, tid_list)

            st.sidebar.success(
                f"Import reusit! {len(tid_df)} TID-uri salvate automat."
            )

        else:
            st.sidebar.error(
                "Nu am putut identifica automat coloanele pentru TID si Nume firma."
            )

    except Exception as e:
        st.sidebar.error(f"Eroare la citire: {e}")
