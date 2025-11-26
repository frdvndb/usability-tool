import streamlit as st
import time
import pandas as pd
from datetime import datetime

# --- Konfigurasi Halaman Website ---
st.set_page_config(page_title="Usability Logger", page_icon="⏱️")

# --- Judul ---
st.title("⏱️ Usability Observation Tool")

# --- Inisialisasi Session State (Ingatan Browser) ---
# Streamlit butuh ini agar data tidak hilang saat tombol diklik
if 'log_data' not in st.session_state:
    st.session_state.log_data = []
if 'is_running' not in st.session_state:
    st.session_state.is_running = False
if 'tasks_config' not in st.session_state:
    st.session_state.tasks_config = []
if 'current_task_idx' not in st.session_state:
    st.session_state.current_task_idx = 0
if 'current_page_num' not in st.session_state:
    st.session_state.current_page_num = 1
if 'last_lap_time' not in st.session_state:
    st.session_state.last_lap_time = 0
if 'start_global_time' not in st.session_state:
    st.session_state.start_global_time = 0

# --- FUNGSI UTAMA ---

def start_observation():
    try:
        raw = st.session_state.config_input
        # Parsing konfigurasi "3, 3, 5"
        configs = [int(x.strip()) for x in raw.split(',') if x.strip().isdigit()]
        if not configs:
            st.error("Format salah! Harap masukkan angka.")
            return
        
        # Set State Awal
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
        st.error(f"Error: {e}")

def save_and_next():
    now = time.time()
    duration = now - st.session_state.last_lap_time
    total_elapsed = now - st.session_state.start_global_time
    
    current_idx = st.session_state.current_task_idx
    limit = st.session_state.tasks_config[current_idx]
    
    # Simpan Data
    new_record = {
        "Tugas Ke": current_idx + 1,
        "Halaman Ke": st.session_state.current_page_num,
        "Status": st.session_state.input_status,
        "Durasi (Detik)": round(duration, 2),
        "Klik Total": st.session_state.input_click_total,
        "Klik Tidak Perlu": st.session_state.input_click_bad,
        "Total Error": st.session_state.input_error,
        "Total Berjalan": round(total_elapsed, 2),
        "Timestamp": datetime.now().strftime('%H:%M:%S')
    }
    st.session_state.log_data.append(new_record)
    
    # Logika Pindah Halaman/Tugas
    if st.session_state.current_page_num >= limit:
        # Pindah Tugas
        st.session_state.current_task_idx += 1
        st.session_state.current_page_num = 1
        
        # Cek Selesai
        if st.session_state.current_task_idx >= len(st.session_state.tasks_config):
            st.session_state.is_running = False
            st.balloons() # Efek balon saat selesai
            st.success("PENGUJIAN SELESAI! Silakan download data di bawah.")
    else:
        # Lanjut Halaman
        st.session_state.current_page_num += 1
        
    # Reset Waktu Lap
    st.session_state.last_lap_time = now

# --- TAMPILAN UI ---

if not st.session_state.is_running:
    # Tampilan Awal (Setup)
    if len(st.session_state.log_data) > 0:
        st.info("Pengujian sebelumnya selesai. Data ada di bawah.")
        
    with st.expander("Konfigurasi Awal", expanded=True):
        st.text_input("Susunan Halaman (cth: 5, 2, 3)", value="3, 3, 4, 3, 5", key="config_input")
        st.button("MULAI OBSERVASI", on_click=start_observation, type="primary")

else:
    # Tampilan Saat Berjalan (Timer & Input)
    
    # Info Tugas
    task_now = st.session_state.current_task_idx + 1
    page_now = st.session_state.current_page_num
    total_page = st.session_state.tasks_config[st.session_state.current_task_idx]
    
    st.markdown(f"### 📝 TUGAS {task_now} | Halaman {page_now} dari {total_page}")
    
    # Timer Display (Static Refresh)
    # Catatan: Di web, live timer (ticking) membebani browser. 
    # Kita tampilkan waktu mulai lap agar user tahu timer sedang berjalan.
    elapsed_so_far = time.time() - st.session_state.last_lap_time
    st.info(f"⏳ Timer sedang berjalan... (Durasi akan dihitung tepat saat tombol Next ditekan)")

    # Input Form
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            st.number_input("✅ Klik Total", min_value=0, value=0, key="input_click_total")
            st.number_input("❌ Total Error", min_value=0, value=0, key="input_error")
        with col2:
            st.number_input("⚠️ Klik Tidak Perlu", min_value=0, value=0, key="input_click_bad")
            st.selectbox("Status Tugas", ["SUKSES", "GAGAL"], key="input_status")
            
        st.button("SIMPAN & LANJUT ➡️", on_click=save_and_next, type="primary", use_container_width=True)

# --- AREA DOWNLOAD DATA ---
if st.session_state.log_data:
    st.divider()
    st.subheader("📂 Data Hasil Observasi")
    
    df = pd.DataFrame(st.session_state.log_data)
    st.dataframe(df)
    
    # Tombol Download CSV
    csv_data = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download File Excel (CSV)",
        data=csv_data,
        file_name=f"UsabilityResult_{datetime.now().strftime('%H%M%S')}.csv",
        mime='text/csv',
    )