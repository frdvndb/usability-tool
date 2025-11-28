import streamlit as st
import time
import pandas as pd
from datetime import datetime
from google.oauth2 import service_account
import gspread # Library khusus untuk Google Sheets

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Usability Logger (Sheets)", page_icon="📊")

# --- FUNGSI KONEKSI KE GOOGLE SHEETS ---
def append_to_sheet(new_row_data):
    """
    Fungsi ini mengirim data baris per baris ke Google Sheets
    tanpa memakan kuota penyimpanan Robot.
    """
    try:
        # 1. Ambil Credentials dari Secrets
        # Menggunakan .get() atau dict() agar aman
        gcp_info = dict(st.secrets["gcp_service_account"])
        
        # Perbaikan Bug "\n" pada Private Key
        if "private_key" in gcp_info:
            gcp_info["private_key"] = gcp_info["private_key"].replace("\\n", "\n")
        
        # 2. Autentikasi Scope (Izin)
        creds = service_account.Credentials.from_service_account_info(
            gcp_info, scopes=[
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
        )
        
        # 3. Login ke GSpread Client
        client = gspread.authorize(creds)
        
        # 4. Buka Spreadsheet Berdasarkan ID
        sheet_id = st.secrets["drive"]["sheet_id"] 
        sh = client.open_by_key(sheet_id)
        
        # Pilih Halaman Pertama (Sheet1)
        worksheet = sh.sheet1 
        
        # 5. Tambahkan Baris Baru (Append)
        worksheet.append_rows(new_row_data)
        
        return True, "Sukses"
    except Exception as e:
        return False, str(e)

# --- JUDUL APLIKASI ---
st.title("📊 Usability Logger -> Google Sheets")

# --- INISIALISASI STATE (MEMORY) ---
if 'log_data' not in st.session_state: st.session_state.log_data = []
if 'is_running' not in st.session_state: st.session_state.is_running = False
if 'tasks_config' not in st.session_state: st.session_state.tasks_config = []
if 'current_task_idx' not in st.session_state: st.session_state.current_task_idx = 0
if 'current_page_num' not in st.session_state: st.session_state.current_page_num = 1
if 'last_lap_time' not in st.session_state: st.session_state.last_lap_time = 0
if 'start_global_time' not in st.session_state: st.session_state.start_global_time = 0

# --- FUNGSI LOGIKA: MULAI ---
def start_observation():
    try:
        raw = st.session_state.config_input
        # Parsing input "3, 2, 5" menjadi list [3, 2, 5]
        configs = [int(x.strip()) for x in raw.split(',') if x.strip().isdigit()]
        
        if not configs:
            st.error("Format konfigurasi salah! Masukkan angka dipisah koma.")
            return
        
        # Reset Variable
        st.session_state.tasks_config = configs
        st.session_state.is_running = True
        st.session_state.current_task_idx = 0
        st.session_state.current_page_num = 1
        st.session_state.log_data = []
        
        # Mulai Waktu
        now = time.time()
        st.session_state.start_global_time = now
        st.session_state.last_lap_time = now
        
    except Exception as e:
        st.error(f"Error memulai: {e}")

# --- FUNGSI LOGIKA: SIMPAN & LANJUT ---
def save_and_next():
    now = time.time()
    # Hitung Durasi
    duration = now - st.session_state.last_lap_time
    total_elapsed = now - st.session_state.start_global_time
    
    current_idx = st.session_state.current_task_idx
    limit = st.session_state.tasks_config[current_idx]
    
    # Siapkan Data Record (Dict untuk lokal)
    record = {
        "Tugas Ke": current_idx + 1,
        "Halaman Ke": st.session_state.current_page_num,
        "Status": st.session_state.input_status,
        "Durasi": round(duration, 2),
        "Klik Total": st.session_state.input_click_total,
        "Klik Bad": st.session_state.input_click_bad,
        "Error": st.session_state.input_error,
        "Timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    st.session_state.log_data.append(record)
    
    # --- AUTO UPLOAD KE SHEETS ---
    # Ubah format menjadi List of List [[col1, col2, ...]] sesuai urutan kolom Sheet
    row_to_upload = [[
        record["Tugas Ke"],
        record["Halaman Ke"],
        record["Status"],
        str(record["Durasi"]).replace('.', ','), # Opsional: ganti titik jadi koma jika Excel Indo
        record["Klik Total"],
        record["Klik Bad"],
        record["Error"],
        record["Timestamp"]
    ]]
    
    # Kirim Data
    ok, msg = append_to_sheet(row_to_upload)
    
    if not ok:
        # Tampilkan error lengkap dalam kotak merah besar
        st.error("TERJADI ERROR SAAT MENYIMPAN KE SHEETS:")
        st.code(msg, language="text") # Ini akan menampilkan detail teknisnya
    else:
        # Tampilkan notifikasi kecil (Toast) agar tidak mengganggu
        st.toast(f"✅ Data Tugas {current_idx+1}-Hal {st.session_state.current_page_num} tersimpan!", icon="☁️")

    # --- LOGIKA PINDAH HALAMAN ---
    if st.session_state.current_page_num >= limit:
        # Pindah Tugas
        st.session_state.current_task_idx += 1
        st.session_state.current_page_num = 1
        
        # Cek Apakah Semua Tugas Selesai?
        if st.session_state.current_task_idx >= len(st.session_state.tasks_config):
            st.session_state.is_running = False
            st.balloons()
            st.success("🏁 PENGUJIAN SELESAI! Semua data sudah masuk ke Google Sheets.")
    else:
        # Lanjut Halaman Berikutnya
        st.session_state.current_page_num += 1
        
    # Reset Timer Lap
    st.session_state.last_lap_time = now

# --- TAMPILAN USER INTERFACE (UI) ---

if not st.session_state.is_running:
    # --- UI SETUP ---
    with st.expander("⚙️ Konfigurasi & Mulai", expanded=True):
        st.caption("Masukkan jumlah halaman per tugas. Contoh: `3, 3, 5` artinya Tugas 1 (3 hal), Tugas 2 (3 hal), dst.")
        st.text_input("Susunan Halaman", value="3, 3, 4, 3, 5", key="config_input")
        st.button("MULAI OBSERVASI ▶️", on_click=start_observation, type="primary")
        
    # Tampilkan Data Lokal jika ada sisa sesi sebelumnya
    if st.session_state.log_data:
        st.divider()
        st.write("Data sesi terakhir (Backup Lokal):")
        st.dataframe(pd.DataFrame(st.session_state.log_data))

else:
    # --- UI BERJALAN ---
    task_now = st.session_state.current_task_idx + 1
    page_now = st.session_state.current_page_num
    total_page_current = st.session_state.tasks_config[st.session_state.current_task_idx]
    
    # Header Info
    st.info(f"📝 **SEDANG BERJALAN: TUGAS {task_now}** | Halaman {page_now} dari {total_page_current}")
    
    # Input Form (Layout 2 Kolom)
    with st.container(border=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.number_input("✅ Total Klik", min_value=0, value=0, key="input_click_total")
            st.number_input("❌ Total Error", min_value=0, value=0, key="input_error")
            
        with col2:
            st.number_input("⚠️ Klik Tidak Perlu", min_value=0, value=0, key="input_click_bad")
            st.selectbox("Status Tugas", ["SUKSES", "GAGAL"], key="input_status")
            
        st.write("") # Spacer
        st.button("SIMPAN & LANJUT ➡️", on_click=save_and_next, type="primary", use_container_width=True)

# --- BACKUP DOWNLOAD ---
if len(st.session_state.log_data) > 0:
    st.divider()
    with st.expander("📂 Download Backup Manual (CSV)"):
        df = pd.DataFrame(st.session_state.log_data)
        st.dataframe(df)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "Download CSV",
            csv,
            f"Backup_Usability_{datetime.now().strftime('%H%M%S')}.csv",
            "text/csv"
        )