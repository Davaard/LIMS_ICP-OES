import streamlit as st
import pandas as pd
import io
import json
import os

# ==========================================
# 0. KONFIGURASI HALAMAN (HARUS PALING ATAS)
# ==========================================
st.set_page_config(page_title="LIMS ICP-OES", page_icon="🧪", layout="wide")

# ==========================================
# FITUR KEAMANAN: PASSWORD LOGIN
# ==========================================
def check_password():
    def password_entered():
        # Mengambil password dari brankas rahasia Streamlit,
        kunci_rahasia = st.secrets.get("password_LIMS", "ICPlims2026")
        
        if st.session_state["password"] == kunci_rahasia:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Hapus password dari memori demi keamanan
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("### 🔒 LIMS ICP-OES - Restricted Access")
        st.text_input("Silakan masukkan password laboratorium:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.markdown("### 🔒 LIMS ICP-OES - Restricted Access")
        st.text_input("Silakan masukkan password laboratorium:", type="password", on_change=password_entered, key="password")
        st.error("😕 Password salah!")
        return False
    return True

# Hentikan eksekusi seluruh kode di bawah jika belum login
if not check_password():
    st.stop() 


# ==========================================
# 1. KONFIGURASI DATA & LIMIT
# ==========================================
DICT_LOGAM = {
    "MIX A": ["Fe", "Mn", "Mo", "Sn", "Ti", "Zn", "Ba", "Cd", "Co", "Cr", "Cu", "Ni", "Pb", "Al"],
    "MIX B": ["Hg", "As", "Se", "Sb"],
    "BORON": ["B"]
}

KOLOM_STANDAR = DICT_LOGAM["MIX A"] + DICT_LOGAM["BORON"] + DICT_LOGAM["MIX B"]

LIMIT_DETEKSI = {
    "Fe": 0.08, "Mn": 0.012, "Mo": 0.01, "Sn": 0.01, "Ti": 0.01, "Zn": 0.02, 
    "Ba": 0.1, "Cd": 0.008, "Co": 0.02, "Cr": 0.059, "Cu": 0.018, "Ni": 0.031, 
    "Pb": 0.03, "Al": 0.01, "B": 0.01, "Hg": 0.0002, "As": 0.002, "Se": 0.01, "Sb": 0.01
}

def get_kategori(logam):
    for kategori, list_logam in DICT_LOGAM.items():
        if logam in list_logam: return kategori
    return "UNKNOWN"

# ==========================================
# 2. SISTEM DATABASE (MEMORI JANGKA PANJANG)
# ==========================================
DB_FILE = "database_lims.json"

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass # Lanjut ke nilai default jika file corrupt/kosong
    return {"data_preparasi": [], "work_order_final": None, "status_selesai": {}}

def save_db():
    db = {
        "data_preparasi": st.session_state.data_preparasi,
        "work_order_final": st.session_state.work_order_final,
        "status_selesai": st.session_state.status_selesai
    }
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=4)

# ==========================================
# 3. INISIALISASI HALAMAN & STATE
# ==========================================
st.title("🧪 LIMS ICP-OES Terintegrasi")
st.markdown("Sistem Manajemen Informasi Laboratorium (Preparasi & Ekstraksi Data Otomatis)")

if "init" not in st.session_state:
    db_awal = load_db()
    st.session_state.data_preparasi = db_awal["data_preparasi"]
    st.session_state.work_order_final = db_awal["work_order_final"]
    st.session_state.status_selesai = db_awal["status_selesai"]
    st.session_state.init = True

tab1, tab2 = st.tabs(["📋 Sesi 1: Preparasi & Work Order", "📈 Sesi 2: Data Ingestion & Report"])

# =========================================================================
# ==================== TAB 1: SESI PRA-ICP (WORK ORDER) ===================
# =========================================================================
with tab1:
    st.markdown("### 📥 Input Permintaan Uji")
    with st.form("form_input", clear_on_submit=True):
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1: 
            no_sampel = st.text_input("Nomor Sampel (Contoh: 654.10)")
            
        with col2:
            # Sembunyikan Boron dari dropdown agar tidak memicu auto-select Ba, Pb, Sb
            opsi_tanpa_b = [x for x in KOLOM_STANDAR if x != "B"]
            pilihan_logam = st.multiselect("Pilih Logam (Kecuali Boron)", options=opsi_tanpa_b)
            
        with col3:
            # Kotak centang khusus Boron (sejajar dengan input lainnya)
            st.markdown("<div style='margin-top: 32px;'></div>", unsafe_allow_html=True)
            uji_boron = st.checkbox("🧪 + Boron (B)")
        
        if st.form_submit_button("➕ Tambahkan ke Antrian"):
            # Gabungkan kembali pilihan logam dan Boron
            final_logam = pilihan_logam.copy()
            if uji_boron:
                final_logam.append("B")
                
            if not no_sampel or not final_logam:
                st.error("Nomor sampel dan logam tidak boleh kosong!")
            else:
                st.session_state.data_preparasi.append({"no_sampel": no_sampel, "logam": final_logam})
                save_db() 
                st.success(f"Sampel **{no_sampel}** ditambahkan!")

    if st.session_state.data_preparasi:
        st.markdown("---")
        st.markdown("### 📋 Daftar Antrian Saat Ini")
        df_antrian = pd.DataFrame(st.session_state.data_preparasi)
        st.dataframe(df_antrian, use_container_width=True)
        
        # Fitur Hapus Sampel Spesifik
        with st.expander("🛠️ Koreksi: Hapus Sampel Tertentu dari Antrian"):
            col_del1, col_del2 = st.columns([3, 1])
            with col_del1:
                list_antrian = [item["no_sampel"] for item in st.session_state.data_preparasi]
                sampel_hapus = st.selectbox("Pilih nomor sampel yang ingin dihapus:", options=list_antrian)
            with col_del2:
                st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                if st.button("🗑️ Hapus Sampel", use_container_width=True):
                    st.session_state.data_preparasi = [x for x in st.session_state.data_preparasi if x["no_sampel"] != sampel_hapus]
                    st.session_state.work_order_final = None
                    st.session_state.status_selesai = {}
                    save_db()
                    st.rerun()
        
        st.markdown("### ⚙️ Pengaturan Kapasitas Slot Pengujian")
        if st.checkbox("Gunakan kapasitas slot yang sama untuk semua", value=True):
            slot_mix_a = slot_mix_b = slot_boron = st.number_input("Maks. Sampel per Run", min_value=1, value=40)
        else:
            col_s1, col_s2, col_s3 = st.columns(3)
            with col_s1: slot_mix_a = st.number_input("Maks. MIX A", value=40)
            with col_s2: slot_mix_b = st.number_input("Maks. MIX B", value=40)
            with col_s3: slot_boron = st.number_input("Maks. BORON", value=40)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        col_btn1, col_btn2 = st.columns([1, 4])
        with col_btn1:
            if st.button("🗑️ Kosongkan Seluruh Antrian"):
                st.session_state.data_preparasi = []
                st.session_state.work_order_final = None
                st.session_state.status_selesai = {}
                save_db()
                st.rerun()
                
        with col_btn2:
            tombol_cetak = st.button("💾 Simpan & Cetak Work Order", type="primary")

        if tombol_cetak:
            wm = {"MIX A": [], "MIX B": [], "BORON": []}
            for item in st.session_state.data_preparasi:
                kat_pilih = {"MIX A": [], "MIX B": [], "BORON": []}
                for l in item["logam"]:
                    if get_kategori(l) != "UNKNOWN": kat_pilih[get_kategori(l)].append(l)
                for kat in ["MIX A", "MIX B", "BORON"]:
                    if kat_pilih[kat]: wm[kat].append({"no_sampel": item["no_sampel"], "logam": kat_pilih[kat]})
            
            def pecah(data, uk): return [data[i:i+uk] for i in range(0, len(data), uk)]
            
            st.session_state.work_order_final = {
                "MIX A": pecah(wm["MIX A"], slot_mix_a), "MIX B": pecah(wm["MIX B"], slot_mix_b), "BORON": pecah(wm["BORON"], slot_boron)
            }
            st.session_state.status_selesai = {}
            save_db()
            st.success("✓ Work Order berhasil diperbarui dan dikunci!")

    if st.session_state.work_order_final:
        st.markdown("---")
        st.markdown("### 📝 Tracker Work Order per Running ICP")
        c_a, c_b, c_c = st.columns(3)
        cfg = {"MIX A": ("🔴", c_a), "MIX B": ("🟡", c_b), "BORON": ("🟢", c_c)}

        for k, (ikon, col_render) in cfg.items():
            with col_render:
                st.markdown(f"#### {ikon} ANTRIAN {k}")
                batches = st.session_state.work_order_final[k]
                if not batches: st.info(f"Kosong")
                for i, batch in enumerate(batches):
                    key_run = f"{k}_{i}"
                    if st.session_state.status_selesai.get(key_run, False):
                        with st.expander(f"~~✓ RUN {i+1} (SELESAI)~~"):
                            for w in batch: st.markdown(f"**{w['no_sampel']}** → *{', '.join(w['logam'])}*")
                            if st.button("↩ Batal", key=f"u_{key_run}", use_container_width=True):
                                st.session_state.status_selesai[key_run] = False
                                save_db()
                                st.rerun()
                    else:
                        with st.container(border=True):
                            st.markdown(f"##### ▷ RUN {i+1} ({len(batch)} Sampel)")
                            st.divider() 
                            for w in batch: st.markdown(f"**{w['no_sampel']}** → *{', '.join(w['logam'])}*")
                            if st.button("✓ Selesai", key=f"d_{key_run}", type="primary", use_container_width=True):
                                st.session_state.status_selesai[key_run] = True
                                save_db()
                                st.rerun()

# =========================================================================
# =================== TAB 2: SESI PASCA-ICP (DATA INGESTION) ==============
# =========================================================================
with tab2:
    st.markdown("### 🚀 Unggah Data Mentah (Raw CSV) dari ICPEsolution")
    
    wo_data = st.session_state.work_order_final
    
    if not wo_data:
        st.warning("⚠️ Work Order kosong! Harap selesaikan Sesi 1 terlebih dahulu.")
    else:
        file_csvs = st.file_uploader("Upload SATU atau LEBIH file CSV hasil running", type=["csv"], accept_multiple_files=True)
        
        if file_csvs:
            with st.spinner("Memproses seluruh file CSV..."):
                try:
                    all_dfs = []
                    for f_csv in file_csvs:
                        df_raw = pd.read_csv(f_csv, header=None, on_bad_lines='skip', low_memory=False)
                        df_unk = df_raw[df_raw[1] == "UNK"].copy()
                        
                        df_unk[9] = pd.to_numeric(df_unk[9], errors='coerce') # Filter Kolom 9 (Optimum)
                        df_opt = df_unk[df_unk[9] == 1].copy()
                        
                        df_clean = df_opt[[2, 6, 11]].copy()
                        df_clean.columns = ["No_Sampel", "Logam", "Konsentrasi"]
                        df_clean["Konsentrasi"] = pd.to_numeric(df_clean["Konsentrasi"], errors='coerce')
                        df_pivot = df_clean.pivot_table(index="No_Sampel", columns="Logam", values="Konsentrasi", aggfunc='first')
                        all_dfs.append(df_pivot)
                    
                    df_combined = pd.concat(all_dfs)
                    df_combined = df_combined.groupby(df_combined.index).first() 
                    
                    wo_flat = {}
                    for kat, batches in wo_data.items():
                        for batch in batches:
                            for item in batch:
                                s = str(item["no_sampel"])
                                if s not in wo_flat: wo_flat[s] = set()
                                wo_flat[s].update(item["logam"])
                    
                    # ========================================================
                    # PEMISAHAN LOGIKA: FINAL REPORT (KETAT) & GSHEET (BEBAS)
                    # ========================================================
                    
                    # 1. Siapkan kerangka GSheet (Ambil semua sampel, termasuk Blanko/blk)
                    df_raw_gsheet = pd.DataFrame(index=df_combined.index)
                    for sampel in df_combined.index:
                        for logam in df_combined.columns:
                            df_raw_gsheet.at[sampel, logam] = df_combined.at[sampel, logam]
                    
                    # 2. Siapkan kerangka Final Report (Hanya ambil yang ada di Work Order)
                    sampel_yg_diproses = [s for s in df_combined.index if str(s) in wo_flat]
                    df_final = pd.DataFrame(index=sampel_yg_diproses)
                    
                    for sampel in sampel_yg_diproses:
                        logam_diminta = wo_flat.get(str(sampel), set())
                        for logam in df_combined.columns:
                            if logam in logam_diminta:
                                nilai = df_combined.at[sampel, logam]
                                limit = LIMIT_DETEKSI.get(logam, 0)
                                
                                if pd.isna(nilai):
                                    df_final.at[sampel, logam] = "N/A"
                                elif nilai < limit:
                                    # UBAH TITIK JADI KOMA KHUSUS TEKS (< LIMIT)
                                    limit_str = str(limit).replace('.', ',')
                                    df_final.at[sampel, logam] = f"<{limit_str}"
                                else:
                                    df_final.at[sampel, logam] = round(nilai, 4)
                    
                    kolom_tersedia = [k for k in KOLOM_STANDAR if k in df_final.columns]
                    df_final = df_final[kolom_tersedia]
                    
                    st.success(f"✓ Berhasil mengekstrak {len(df_final)} Sampel dari {len(file_csvs)} file CSV.")
                    st.markdown("### 📊 Preview Data")
                    st.dataframe(df_final, use_container_width=True)
                    
                    # ----------------------------------------------------
                    # ALGORITMA PENYUSUNAN 2 JENIS EXCEL (FINAL & GSHEET)
                    # ----------------------------------------------------
                    
                    # 1. Excel Laporan Akhir (PDF Format)
                    buffer_final = io.BytesIO()
                    with pd.ExcelWriter(buffer_final, engine='xlsxwriter') as writer:
                        df_final.to_excel(writer, sheet_name='Reported Result')
                        
                    # 2. Excel Raw Data (GSheet Format) - 3 Sheet Terpisah
                    buffer_raw = io.BytesIO()
                    with pd.ExcelWriter(buffer_raw, engine='xlsxwriter') as writer:
                        for kategori, logam_list in DICT_LOGAM.items():
                            available_metals = [l for l in logam_list if l in df_raw_gsheet.columns]
                            
                            if not available_metals: # Jika kosong, buat sheet kosong
                                df_sheet = pd.DataFrame(columns=['No', 'Sampel'] + logam_list)
                            else:
                                df_mix = df_raw_gsheet[available_metals].copy()
                                df_mix = df_mix.dropna(how='all') # Buang baris yang kosong semua di mix ini
                                df_mix = df_mix.reindex(columns=logam_list) # Urutkan presisi sesuai GSheet
                                
                                # Tambahkan kolom No & Sampel di depan
                                df_mix.insert(0, 'Sampel', df_mix.index)
                                df_mix.insert(0, 'No', range(1, len(df_mix) + 1))
                                df_sheet = df_mix
                                
                            df_sheet.to_excel(writer, sheet_name=kategori, index=False)
                    
                    # TAMPILAN 2 TOMBOL DOWNLOAD
                    st.markdown("### 📥 Download Hasil Ekstraksi")
                    col_dl1, col_dl2 = st.columns(2)
                    with col_dl1:
                        st.download_button(
                            label="⬇️ Excel Laporan Akhir (Cetak PDF)",
                            data=buffer_final.getvalue(),
                            file_name="Final_Report_ICP.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            type="primary",
                            use_container_width=True
                        )
                    with col_dl2:
                        st.download_button(
                            label="⬇️ Excel Raw Data (Upload ke GSheet Lab)",
                            data=buffer_raw.getvalue(),
                            file_name="Raw_GSheet_ICP.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            type="secondary",
                            use_container_width=True
                        )
                        
                except Exception as e:
                    st.error(f"Gagal memproses data. Pastikan format CSV sesuai. Error: {e}")