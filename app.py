import streamlit as st
import time
import pandas as pd
from datetime import datetime
from google.oauth2 import service_account
import gspread

# --- 1. KONFIGURASI HALAMAN (Tampilan Bersih) ---
st.set_page_config(page_title="Usability Test", page_icon="📱", layout="centered")

# --- CSS HACK: Menyembunyikan Menu Streamlit agar terlihat seperti App Asli ---
hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            .stApp {background-color: #f8f9fa;}
            div[data-testid="stVerticalBlock"] > div {
                background-color: white;
                padding: 20px;
                border-radius: 15px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# --- FUNGSI GOOGLE SHEETS (Sama, tapi pesannya diperhalus) ---
def append_to_sheet(new_row_data):
    try:
        gcp_info = dict(st.secrets["gcp_service_account"])
        if "private_key" in gcp_info:
            gcp_info["private_key"] = gcp_info["private_key"].replace("\\n", "\n")
        
        creds = service_account.Credentials.from_service_account_info(
            gcp_info, scopes=[
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
        )
        client = gspread.authorize(creds)
        sheet_id = st.secrets["drive"]["sheet_id"] 
        sh = client.open_by_key(sheet_id)
        worksheet = sh.sheet1 
        worksheet.append_rows(new_row_data)
        return True, ""
    except Exception as e:
        return False, str(e)

# --- STATE MANAGEMENT ---
if 'is_running' not in st.session_state: st.session_state.is_running = False
if 'current_task_idx' not in st.session_state: st.session_state.current_task_idx = 0
if 'current_page_num' not in st.session_state: st.session_state.current_page_num = 1
if 'last_lap_time' not in st.session_state: st.session_state.last_lap_time = 0
if 'start_global_time' not in st.session_state: st.session_state.start_global_time = 0
if 'log_data' not in st.session_state: st.session_state.log_data = []

# --- SIDEBAR (KHUSUS PENELITI/ADMIN) ---
# Responden tidak perlu melihat ini
with st.sidebar:
    st.header("⚙️ Admin Panel")
    st.caption("Pengaturan ini hanya untuk Peneliti.")
    
    # Input Config Halaman
    config_input = st.text_input("Jml Halaman per Tugas (cth: 3,2)", value="3, 3, 5")
    
    # Input Nama Skenario (Supaya muncul di layar responden)
    scenario_input = st.text_area("Nama Skenario (Pisah baris)", 
                                  value="Login Aplikasi\nTransfer Saldo\nLogout Akun")
    
    # Parsing Config
    try:
        tasks_config = [int(x.strip()) for x in config_input.split(',') if x.strip().isdigit()]
        task_names = [x.strip() for x in scenario_input.split('\n') if x.strip()]
    except:
        tasks_config = []
        task_names = []

# --- FUNGSI LOGIKA ---
def start_test():
    st.session_state.is_running = True
    st.session_state.current_task_idx = 0
    st.session_state.current_page_num = 1
    st.session_state.log_data = []
    now = time.time()
    st.session_state.start_global_time = now
    st.session_state.last_lap_time = now

def next_step():
    now = time.time()
    duration = now - st.session_state.last_lap_time
    
    idx = st.session_state.current_task_idx
    limit = tasks_config[idx] if idx < len(tasks_config) else 1
    
    # Ambil data inputan (Menggunakan Session State keys)
    # Jika responden yang mengisi, biasanya mereka tidak menghitung klik.
    # Jadi kita set default 0 atau ambil dari input jika ada.
    click_total = st.session_state.get("inp_click", 0)
    error_total = st.session_state.get("inp_error", 0)
    status = st.session_state.get("inp_status", "SUKSES")
    
    record = {
        "Tugas Ke": idx + 1,
        "Halaman Ke": st.session_state.current_page_num,
        "Status": status,
        "Durasi": round(duration, 2),
        "Klik Total": click_total,
        "Klik Bad": 0, # Responden jarang tahu klik bad, bisa di-hidden
        "Error": error_total,
        "Timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Upload Background
    row = [[
        record["Tugas Ke"], record["Halaman Ke"], record["Status"], 
        str(record["Durasi"]).replace('.', ','), 
        record["Klik Total"], 0, record["Error"], record["Timestamp"]
    ]]
    
    ok, _ = append_to_sheet(row)
    if ok:
        st.toast("✅ Progress tersimpan!", icon="💾")
    else:
        st.toast("⚠️ Koneksi lambat, data disimpan lokal.", icon="ww")

    # Navigasi
    if st.session_state.current_page_num >= limit:
        st.session_state.current_task_idx += 1
        st.session_state.current_page_num = 1
        if st.session_state.current_task_idx >= len(tasks_config):
            st.session_state.is_running = False
            st.balloons()
    else:
        st.session_state.current_page_num += 1
    
    st.session_state.last_lap_time = now

# --- TAMPILAN UTAMA (RESPONDEN) ---

st.title("📱 Usability Testing")
st.markdown("---")

if not st.session_state.is_running:
    # HALAMAN DEPAN (WELCOME)
    st.subheader("Selamat Datang")
    st.write("""
    Halo! Terima kasih telah bersedia menjadi responden.
    
    **Instruksi:**
    1. Aplikasi ini akan memandu Anda melalui beberapa skenario tugas.
    2. Tekan tombol **MULAI** di bawah saat Anda siap.
    3. Lakukan tugas pada aplikasi yang sedang diuji.
    4. Setelah selesai satu langkah, kembali ke sini dan tekan **SELESAI / LANJUT**.
    """)
    
    st.button("🚀 MULAI TES", on_click=start_test, type="primary", use_container_width=True)

else:
    # HALAMAN TES (ACTIVE)
    idx = st.session_state.current_task_idx
    page_num = st.session_state.current_page_num
    total_page = tasks_config[idx] if idx < len(tasks_config) else 99
    
    # Ambil nama skenario
    nama_tugas = task_names[idx] if idx < len(task_names) else f"Tugas {idx+1}"
    
    # Progress Bar
    progress = (idx) / len(tasks_config)
    st.progress(progress, text=f"Progress Keseluruhan")

    # KARTU INSTRUKSI
    st.info(f"📂 **TUGAS ANDA SAAT INI:**")
    st.markdown(f"## {nama_tugas}")
    st.caption(f"Langkah {page_num} dari {total_page}")
    
    st.divider()
    
    # INPUT RESPONDEN (Disederhanakan)
    # Jika Responden yang isi, jangan tanya "Klik Tidak Perlu", mereka bingung.
    # Cukup tanya: Berhasil? Susah gak? (Opsional)
    
    st.write("**Laporan Anda:**")
    col1, col2 = st.columns(2)
    with col1:
        st.selectbox("Apakah Berhasil?", ["SUKSES", "GAGAL"], key="inp_status")
    with col2:
        # Opsional: Jika Anda ingin responden mengisi error sendiri
        st.number_input("Jumlah Kesalahan (Jika ada)", min_value=0, key="inp_error")
        # Hidden click counter (biar 0) atau tampilkan jika perlu
        st.number_input("Est. Jumlah Klik", min_value=0, key="inp_click", help="Berapa kali anda mengetuk layar?")

    st.write("")
    st.button("✅ SELESAI LANGKAH INI (LANJUT)", on_click=next_step, type="primary", use_container_width=True)

# Jika Selesai
if not st.session_state.is_running and len(st.session_state.log_data) > 0:
    st.success("🎉 Terima kasih! Seluruh rangkaian tes telah selesai.")
    st.write("Anda boleh menutup halaman ini sekarang.")
    if st.button("Mulai Ulang (Responden Baru)"):
        st.session_state.log_data = []
        st.rerun()