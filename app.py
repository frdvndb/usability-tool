import streamlit as st
import time
import pandas as pd
from datetime import datetime
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# --- Konfigurasi Halaman ---
st.set_page_config(page_title="Usability Logger + Drive", page_icon="⏱️")

# --- FUNGSI GOOGLE DRIVE UPLOAD ---
def upload_to_drive(df, filename):
    try:
        # 1. Ambil Secrets
        gcp_info = dict(st.secrets["gcp_service_account"]) # Pakai dict() agar aman
        folder_id = st.secrets["drive"]["folder_id"]

        # Debugging: Cek apakah ID Folder terbaca
        if not folder_id:
            return False, "Folder ID di secrets.toml KOSONG!"

        # Fix Newline pada Private Key
        if "private_key" in gcp_info:
            gcp_info["private_key"] = gcp_info["private_key"].replace("\\n", "\n")
        
        creds = service_account.Credentials.from_service_account_info(
            gcp_info, scopes=['https://www.googleapis.com/auth/drive']
        )
        
        service = build('drive', 'v3', credentials=creds)

        # 2. Siapkan File
        csv_buffer = io.BytesIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)

        # 3. Metadata File (PENTING: Parents harus list)
        file_metadata = {
            'name': filename,
            'parents': [folder_id]  # <--- Ini yang memaksa file masuk ke folder Anda
        }

        # 4. Upload dengan supportsAllDrives=True
        media = MediaIoBaseUpload(csv_buffer, mimetype='text/csv')
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id',
            supportsAllDrives=True  # Tambahan agar lebih kompatibel
        ).execute()

        return True, file.get('id')

    except Exception as e:
        return False, str(e)

# --- JUDUL & STATE ---
st.title("⏱️ Usability Tool (+ Auto Upload)")

if 'log_data' not in st.session_state: st.session_state.log_data = []
if 'is_running' not in st.session_state: st.session_state.is_running = False
if 'tasks_config' not in st.session_state: st.session_state.tasks_config = []
if 'current_task_idx' not in st.session_state: st.session_state.current_task_idx = 0
if 'current_page_num' not in st.session_state: st.session_state.current_page_num = 1
if 'last_lap_time' not in st.session_state: st.session_state.last_lap_time = 0
if 'start_global_time' not in st.session_state: st.session_state.start_global_time = 0

# --- FUNGSI LOGIKA UTAMA ---

def start_observation():
    try:
        raw = st.session_state.config_input
        configs = [int(x.strip()) for x in raw.split(',') if x.strip().isdigit()]
        if not configs:
            st.error("Format salah!")
            return
        
        st.session_state.tasks_config = configs
        st.session_state.is_running = True
        st.session_state.current_task_idx = 0
        st.session_state.current_page_num = 1
        st.session_state.log_data = []
        
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
    
    # Simpan Data ke Memory
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
    
    # Logika Pindah
    if st.session_state.current_page_num >= limit:
        st.session_state.current_task_idx += 1
        st.session_state.current_page_num = 1
        
        # --- CEK JIKA SEMUA TUGAS SELESAI ---
        if st.session_state.current_task_idx >= len(st.session_state.tasks_config):
            st.session_state.is_running = False
            
            # --- AUTO UPLOAD KE DRIVE ---
            with st.spinner('Sedang mengupload ke Google Drive...'):
                df_final = pd.DataFrame(st.session_state.log_data)
                nama_file = f"Usability_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv"
                
                # Panggil fungsi upload
                success, msg = upload_to_drive(df_final, nama_file)
                
                if success:
                    st.balloons()
                    st.success(f"✅ Data BERHASIL disimpan ke Google Drive!\nID File: {msg}")
                else:
                    st.error(f"⚠️ Gagal upload ke Drive: {msg}")
                    st.warning("Tapi jangan khawatir, data masih bisa didownload manual di bawah.")
                    
    else:
        st.session_state.current_page_num += 1
        
    st.session_state.last_lap_time = now

# --- TAMPILAN UI ---

if not st.session_state.is_running:
    if len(st.session_state.log_data) > 0:
        st.info("Sesi sebelumnya selesai.")
        
    with st.expander("Konfigurasi Awal", expanded=True):
        st.text_input("Susunan Halaman (cth: 5, 2)", value="3, 3, 4, 3, 5", key="config_input")
        st.button("MULAI OBSERVASI", on_click=start_observation, type="primary")

else:
    task_now = st.session_state.current_task_idx + 1
    page_now = st.session_state.current_page_num
    total_page = st.session_state.tasks_config[st.session_state.current_task_idx]
    
    st.markdown(f"### 📝 TUGAS {task_now} | Halaman {page_now} dari {total_page}")
    st.info(f"⏳ Timer sedang berjalan...")

    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            st.number_input("✅ Klik Total", min_value=0, value=0, key="input_click_total")
            st.number_input("❌ Total Error", min_value=0, value=0, key="input_error")
        with col2:
            st.number_input("⚠️ Klik Tidak Perlu", min_value=0, value=0, key="input_click_bad")
            st.selectbox("Status Tugas", ["SUKSES", "GAGAL"], key="input_status")
            
        st.button("SIMPAN & LANJUT ➡️", on_click=save_and_next, type="primary", use_container_width=True)

# --- DOWNLOAD MANUAL (BACKUP) ---
if st.session_state.log_data:
    st.divider()
    df = pd.DataFrame(st.session_state.log_data)
    csv_data = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Manual (CSV)",
        data=csv_data,
        file_name=f"UsabilityResult_{datetime.now().strftime('%H%M%S')}.csv",
        mime='text/csv',
    )