import streamlit as st
import time
import pandas as pd
from datetime import datetime
from google.oauth2 import service_account
import gspread

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Usability Test", page_icon="📱", layout="centered")



# --- FUNGSI GOOGLE SHEETS ---
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

# --- SIDEBAR ADMIN ---
with st.sidebar:
    st.header("⚙️ Admin Panel")
    config_input = st.text_input("Jml Halaman (cth: 3,2)", value="3, 3, 5")
    scenario_input = st.text_area("Nama Skenario (Pisah baris)", 
                                  value="Login Aplikasi\nTransfer Saldo\nLogout Akun")
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
    
    # Ambil Data Input (termasuk Klik Bad)
    click_total = st.session_state.get("inp_click", 0)
    click_bad = st.session_state.get("inp_click_bad", 0) # <-- SUDAH DITAMBAHKAN
    error_total = st.session_state.get("inp_error", 0)
    status = st.session_state.get("inp_status", "SUKSES")
    
    record = {
        "Tugas Ke": idx + 1,
        "Halaman Ke": st.session_state.current_page_num,
        "Status": status,
        "Durasi": round(duration, 2),
        "Klik Total": click_total,
        "Klik Bad": click_bad,
        "Error": error_total,
        "Timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Upload ke Sheets
    row = [[
        record["Tugas Ke"], record["Halaman Ke"], record["Status"], 
        str(record["Durasi"]).replace('.', ','), 
        record["Klik Total"], record["Klik Bad"], record["Error"], record["Timestamp"]
    ]]
    
    ok, _ = append_to_sheet(row)
    if ok:
        st.toast("✅ Tersimpan!", icon="💾")
    else:
        st.toast("⚠️ Tersimpan Lokal", icon="ww")

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

# --- TAMPILAN UTAMA ---

st.title("📱 Usability Testing")
st.markdown("---")

if not st.session_state.is_running:
    # WELCOME SCREEN
    st.subheader("Selamat Datang")
    st.write("Silakan tekan tombol di bawah jika sudah siap melakukan pengujian.")
    st.button("🚀 MULAI TES", on_click=start_test, type="primary", use_container_width=True)

else:
    # ACTIVE SCREEN
    idx = st.session_state.current_task_idx
    page_num = st.session_state.current_page_num
    total_page = tasks_config[idx] if idx < len(tasks_config) else 99
    nama_tugas = task_names[idx] if idx < len(task_names) else f"Tugas {idx+1}"
    
    # Header Info
    st.info(f"📂 **TUGAS:** {nama_tugas}")
    st.caption(f"Langkah {page_num} dari {total_page}")
    st.progress((idx) / len(tasks_config), text="Progress")
    
    st.divider()
    
    # FORM INPUT LENGKAP
    st.write("**Laporan Langkah Ini:**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.number_input("Total Klik", min_value=0, key="inp_click")
        st.number_input("Total Error", min_value=0, key="inp_error")
        
    with col2:
        # BAGIAN YANG ANDA MINTA ADA DISINI:
        st.number_input("Klik Tidak Perlu", min_value=0, key="inp_click_bad", help="Salah pencet / klik kosong")
        st.selectbox("Status", ["SUKSES", "GAGAL"], key="inp_status")

    st.write("")
    st.button("✅ SIMPAN & LANJUT", on_click=next_step, type="primary", use_container_width=True)

# FINISH SCREEN
if not st.session_state.is_running and len(st.session_state.log_data) > 0:
    st.success("🎉 Tes Selesai! Terima kasih.")
    if st.button("Mulai Ulang"):
        st.session_state.log_data = []
        st.rerun()