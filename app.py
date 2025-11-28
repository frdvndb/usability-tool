import streamlit as st
import time
import pandas as pd
from datetime import datetime
from google.oauth2 import service_account
import gspread

# ==========================================
# 1. SETUP HALAMAN & CSS
# ==========================================
st.set_page_config(page_title="Usability Guide", page_icon="📱", layout="centered")

# ==========================================
# 2. FUNGSI GOOGLE SHEETS
# ==========================================
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

# ==========================================
# 3. STATE MANAGEMENT
# ==========================================
if 'is_running' not in st.session_state: st.session_state.is_running = False
if 'current_task_idx' not in st.session_state: st.session_state.current_task_idx = 0
if 'current_page_num' not in st.session_state: st.session_state.current_page_num = 1
if 'last_lap_time' not in st.session_state: st.session_state.last_lap_time = 0
if 'log_data' not in st.session_state: st.session_state.log_data = []

# ==========================================
# 4. ADMIN PANEL (DINAMIS)
# ==========================================
with st.sidebar:
    st.header("⚙️ Admin Panel")
    
    # A. CONFIG JUMLAH HALAMAN
    st.subheader("1. Struktur Tugas")
    config_input = st.text_input("Jml Halaman per Tugas (koma)", value="3, 3, 2")
    try:
        tasks_config = [int(x.strip()) for x in config_input.split(',') if x.strip().isdigit()]
    except:
        tasks_config = []

    # B. CONFIG TEKS PANDUAN (SCENARIO GUIDE)
    st.subheader("2. Teks Panduan")
    st.caption("Format per baris -> Tugas-Hal : Instruksi")
    
    # Default Text untuk memudahkan Admin pertama kali
    default_scenario = """1-1 : Buka aplikasi, tekan tombol 'Masuk'.
1-2 : Masukkan User: admin, Pass: 123.
1-3 : Jika berhasil, tekan menu 'Beranda'.
2-1 : Tekan menu 'Transfer'.
2-2 : Masukkan nominal Rp 50.000.
2-3 : Tekan Kirim dan tunggu sukses.
3-1 : Tekan Profil di pojok kanan.
3-2 : Scroll ke bawah dan tekan Logout."""

    scenario_raw = st.text_area("Edit Skenario Disini:", value=default_scenario, height=300)
    
    # Parsing Teks menjadi Dictionary Python
    SCENARIO_GUIDE = {}
    for line in scenario_raw.split('\n'):
        if ':' in line:
            # Memisahkan "1-1" dengan "Instruksinya"
            parts = line.split(':', 1) 
            key = parts[0].strip()
            val = parts[1].strip()
            SCENARIO_GUIDE[key] = val

    st.success(f"Terdeteksi {len(SCENARIO_GUIDE)} langkah instruksi.")

# ==========================================
# 5. LOGIKA APLIKASI
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
    
    # Ambil Input
    click_total = st.session_state.get("inp_click", 0)
    click_bad = st.session_state.get("inp_click_bad", 0)
    error_total = st.session_state.get("inp_error", 0)
    status = st.session_state.get("inp_status", "SUKSES")
    
    # Format Data
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
    if ok: st.toast("✅ Tersimpan!", icon="💾")
    else: st.toast("⚠️ Tersimpan Lokal", icon="ww")

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

# ==========================================
# 6. TAMPILAN USER INTERFACE (UI)
# ==========================================
st.title("📱 Usability Testing")

if not st.session_state.is_running:
    st.info("👋 Selamat Datang. Aplikasi ini akan memandu Anda melakukan pengujian.")
    st.button("🚀 MULAI PANDUAN", on_click=start_test, type="primary", use_container_width=True)

else:
    # 1. Ambil Teks Panduan dari Input Admin
    idx = st.session_state.current_task_idx
    page_num = st.session_state.current_page_num
    
    guide_key = f"{idx + 1}-{page_num}"
    
    # Ambil teks, jika tidak ada di admin panel, pakai teks default
    instruction_text = SCENARIO_GUIDE.get(guide_key, "Lanjutkan langkah sesuai aplikasi.")
    
    # 2. Tampilkan Kotak Panduan
    st.markdown(f"""
    <div style="padding: 20px; border-radius: 12px; border-left: 6px solid #007bff; margin-bottom: 25px;">
        <h4 style="margin:0; color: #007bff; font-size: 14px; text-transform: uppercase;">Langkah {page_num}</h4>
        <h2 style="margin-top:5px; margin-bottom:0; font-size: 22px; font-weight: 600;">{instruction_text}</h2>
    </div>
    """, unsafe_allow_html=True)
    
    # 3. Progress
    total_page = tasks_config[idx] if idx < len(tasks_config) else 99
    st.caption(f"Tugas {idx + 1} | Halaman {page_num} dari {total_page}")
    st.progress(page_num / total_page, text=f"Progress Tugas {idx + 1}")
    
    st.divider()
    
    # 4. Input Data
    st.write("**📝 Laporan Pengguna:**")
    col1, col2 = st.columns(2)
    with col1:
        st.number_input("Total Klik", min_value=0, key="inp_click")
        st.number_input("Total Error", min_value=0, key="inp_error")
    with col2:
        st.number_input("Klik Tidak Perlu", min_value=0, key="inp_click_bad")
        st.selectbox("Status", ["SUKSES", "GAGAL"], key="inp_status")

    st.write("")
    st.button("✅ SUDAH, LANJUT LANGKAH BERIKUTNYA", on_click=next_step, type="primary", use_container_width=True)

# SELESAI
if not st.session_state.is_running and len(st.session_state.log_data) > 0:
    st.success("🎉 Tes Selesai! Terima kasih.")
    if st.button("Mulai Ulang"):
        st.session_state.log_data = []
        st.rerun()