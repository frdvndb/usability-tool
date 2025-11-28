import streamlit as st
import time
import pandas as pd
from datetime import datetime
from google.oauth2 import service_account
import gspread

# ==========================================
# 1. KONFIGURASI PANDUAN (EDIT BAGIAN INI)
# ==========================================
# Format Kunci: "NOMOR_TUGAS - NOMOR_HALAMAN"
# Silakan ganti kata-katanya sesuai skenario skripsi Anda.

SCENARIO_GUIDE = {
    # --- TUGAS 1 (Misal: Login) ---
    "1-1": "Buka aplikasi, lalu tekan tombol **'Masuk'** (Login).",
    "1-2": "Masukkan Username: **user** dan Password: **123**, lalu tekan Enter.",
    "1-3": "Jika berhasil Login, cari dan tekan menu **'Beranda'**.",
    
    # --- TUGAS 2 (Misal: Transfer) ---
    "2-1": "Di halaman Beranda, tekan menu **'Transfer'**.",
    "2-2": "Masukkan nominal transfer **Rp 50.000**.",
    "2-3": "Tekan tombol **'Kirim'** dan tunggu bukti transfer muncul.",
    
    # --- TUGAS 3 (Misal: Logout) ---
    "3-1": "Tekan icon **Profil** di pojok kanan atas.",
    "3-2": "Scroll ke paling bawah, lalu tekan tombol **'Keluar'** (Logout)."
}

# Teks default jika Anda lupa mengisi nomor halaman tertentu
DEFAULT_TEXT = "Silakan lanjutkan langkah sesuai alur aplikasi."

# ==========================================
# 2. SETUP HALAMAN & CSS
# ==========================================
st.set_page_config(page_title="Usability Guide", page_icon="📱", layout="centered")


# ==========================================
# 3. FUNGSI KONEKSI GOOGLE SHEETS
# ==========================================
def append_to_sheet(new_row_data):
    try:
        # Ambil credentials dari secrets.toml
        gcp_info = dict(st.secrets["gcp_service_account"])
        
        # Fix bug karakter newline pada private key
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
        
        # Upload Data
        worksheet.append_rows(new_row_data)
        return True, ""
    except Exception as e:
        return False, str(e)

# ==========================================
# 4. STATE MANAGEMENT (MEMORI BROWSER)
# ==========================================
if 'is_running' not in st.session_state: st.session_state.is_running = False
if 'current_task_idx' not in st.session_state: st.session_state.current_task_idx = 0
if 'current_page_num' not in st.session_state: st.session_state.current_page_num = 1
if 'last_lap_time' not in st.session_state: st.session_state.last_lap_time = 0
if 'log_data' not in st.session_state: st.session_state.log_data = []

# ==========================================
# 5. SIDEBAR ADMIN (TERSEMBUNYI)
# ==========================================
with st.sidebar:
    st.header("⚙️ Admin Panel")
    st.caption("Atur jumlah halaman per tugas disini. Harus cocok dengan SCENARIO_GUIDE di kode.")
    
    # Default: Tugas 1 (3 hal), Tugas 2 (3 hal), Tugas 3 (2 hal)
    config_input = st.text_input("Config Halaman (cth: 3,3,2)", value="3, 3, 2")
    
    try:
        tasks_config = [int(x.strip()) for x in config_input.split(',') if x.strip().isdigit()]
    except:
        tasks_config = []

# ==========================================
# 6. LOGIKA APLIKASI
# ==========================================
def start_test():
    st.session_state.is_running = True
    st.session_state.current_task_idx = 0
    st.session_state.current_page_num = 1
    st.session_state.log_data = []
    st.session_state.last_lap_time = time.time()

def next_step():
    now = time.time()
    duration = now - st.session_state.last_lap_time
    
    idx = st.session_state.current_task_idx
    limit = tasks_config[idx] if idx < len(tasks_config) else 1
    
    # Ambil Input Data
    click_total = st.session_state.get("inp_click", 0)
    click_bad = st.session_state.get("inp_click_bad", 0)
    error_total = st.session_state.get("inp_error", 0)
    status = st.session_state.get("inp_status", "SUKSES")
    
    # Format Data untuk Sheets
    # Kolom: Tugas | Halaman | Status | Durasi | Klik Total | Klik Bad | Error | Waktu
    row = [[
        idx + 1, 
        st.session_state.current_page_num, 
        status, 
        str(round(duration, 2)).replace('.', ','), 
        click_total, 
        click_bad, 
        error_total, 
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ]]
    
    # Kirim ke Cloud
    ok, _ = append_to_sheet(row)
    
    if ok:
        st.toast("✅ Tersimpan ke Google Sheets!", icon="☁️")
    else:
        st.toast("⚠️ Koneksi lambat, tersimpan lokal sementara.", icon="📁")

    # Logika Navigasi (Pindah Halaman / Selesai)
    if st.session_state.current_page_num >= limit:
        st.session_state.current_task_idx += 1
        st.session_state.current_page_num = 1
        
        # Cek apakah semua tugas sudah beres
        if st.session_state.current_task_idx >= len(tasks_config):
            st.session_state.is_running = False
            st.balloons()
    else:
        st.session_state.current_page_num += 1
    
    # Reset Timer
    st.session_state.last_lap_time = now

# ==========================================
# 7. TAMPILAN USER INTERFACE (UI)
# ==========================================
st.title("📱 Usability Testing")

if not st.session_state.is_running:
    # --- HALAMAN DEPAN ---
    st.info("👋 Selamat Datang. Aplikasi ini akan memandu Anda melakukan pengujian langkah demi langkah.")
    st.write("Tekan tombol di bawah jika Anda sudah siap.")
    st.button("🚀 MULAI PANDUAN", on_click=start_test, type="primary", use_container_width=True)

else:
    # --- HALAMAN PENGUJIAN ---
    
    # 1. Tentukan Instruksi yang Mana
    idx = st.session_state.current_task_idx
    page_num = st.session_state.current_page_num
    
    # Kunci dictionary (Misal: "1-1")
    guide_key = f"{idx + 1}-{page_num}"
    
    # Ambil teks panduan
    instruction_text = SCENARIO_GUIDE.get(guide_key, DEFAULT_TEXT)
    
    # 2. Tampilkan Kotak Panduan (Warna Biru)
    st.markdown(f"""
    <div style=" padding: 20px; border-radius: 12px; border-left: 6px solid #007bff; margin-bottom: 25px;">
        <h4 style="margin:0; color: #007bff; font-size: 14px; text-transform: uppercase;">Langkah {page_num}</h4>
        <h2 style="margin-top:5px; margin-bottom:0; font-size: 22px; font-weight: 600;">{instruction_text}</h2>
    </div>
    """, unsafe_allow_html=True)
    
    # 3. Progress Bar Kecil
    total_page = tasks_config[idx] if idx < len(tasks_config) else 99
    st.progress(page_num / total_page, text=f"Progress Tugas {idx + 1}")
    
    st.divider()
    
    # 4. Input Data Observasi
    st.write("**📝 Laporan Pengguna:**")
    col1, col2 = st.columns(2)
    
    with col1:
        st.number_input("Total Klik", min_value=0, key="inp_click")
        st.number_input("Total Error", min_value=0, key="inp_error")
    with col2:
        st.number_input("Klik Tidak Perlu", min_value=0, key="inp_click_bad")
        st.selectbox("Status", ["SUKSES", "GAGAL"], key="inp_status")

    st.write("") # Spasi kosong
    
    # 5. Tombol Lanjut
    st.button("✅ SUDAH, LANJUT LANGKAH BERIKUTNYA", on_click=next_step, type="primary", use_container_width=True)

# --- HALAMAN SELESAI ---
if not st.session_state.is_running and len(st.session_state.log_data) > 0:
    st.success("🎉 Tes Selesai! Terima kasih atas partisipasi Anda.")
    st.caption("Data telah tersimpan otomatis ke sistem.")
    
    if st.button("Mulai Ulang (Responden Baru)"):
        st.session_state.log_data = []
        st.rerun()