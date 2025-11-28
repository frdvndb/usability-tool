import streamlit as st
import time
import pandas as pd
from datetime import datetime
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

st.set_page_config(page_title="Usability Logger (Debug Mode)", page_icon="🔧")

# --- BAGIAN 1: FUNGSI DIAGNOSA & UPLOAD ---
def get_drive_service():
    try:
        # Ambil credentials
        gcp_info = dict(st.secrets["gcp_service_account"])
        
        # Bersihkan spasi yang mungkin tidak sengaja terbawa
        if "private_key" in gcp_info:
            gcp_info["private_key"] = gcp_info["private_key"].replace("\\n", "\n")
        
        creds = service_account.Credentials.from_service_account_info(
            gcp_info, scopes=['https://www.googleapis.com/auth/drive']
        )
        return build('drive', 'v3', credentials=creds), None
    except Exception as e:
        return None, str(e)

def cek_koneksi_folder():
    service, error = get_drive_service()
    if error:
        return False, f"Gagal Login Robot: {error}"
    
    # Ambil Folder ID dan bersihkan spasi
    folder_id = st.secrets["drive"]["folder_id"].strip() 
    
    try:
        # Coba mengintip metadata folder
        folder = service.files().get(
            fileId=folder_id, 
            fields="name, capabilities",
            supportsAllDrives=True
        ).execute()
        
        # Cek apakah robot punya izin tulis?
        bisa_edit = folder.get('capabilities', {}).get('canAddChildren', False)
        nama_folder = folder.get('name')
        
        if not bisa_edit:
            return False, f"Robot bisa melihat folder '{nama_folder}', TAPI STATUSNYA HANYA 'VIEWER'. Harap ubah ke 'EDITOR'."
        
        return True, f"SUKSES! Robot terhubung ke folder: **{nama_folder}** (Izin: Editor)"
        
    except Exception as e:
        return False, f"Robot TIDAK BISA menemukan folder ID **{folder_id}**. Pastikan ID benar dan sudah di-share ke email robot."

def upload_to_drive(df, filename):
    service, error = get_drive_service()
    if error: return False, error
    
    folder_id = st.secrets["drive"]["folder_id"].strip()
    
    try:
        csv_buffer = io.BytesIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)

        file_metadata = {
            'name': filename,
            'parents': [folder_id] # Ini kunci agar tidak masuk ke root robot
        }

        media = MediaIoBaseUpload(csv_buffer, mimetype='text/csv')
        
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id',
            supportsAllDrives=True
        ).execute()

        return True, file.get('id')
    except Exception as e:
        return False, str(e)

# --- BAGIAN 2: TAMPILAN DIAGNOSA (Hanya Muncul di Atas) ---
st.title("🔧 Mode Perbaikan Koneksi")

# Tombol Cek
if st.button("🔍 CEK KONEKSI GOOGLE DRIVE SEKARANG"):
    with st.spinner("Sedang menghubungi Google..."):
        sukses, pesan = cek_koneksi_folder()
        if sukses:
            st.success(pesan)
        else:
            st.error(pesan)
            st.warning("Pastikan ID Folder di secrets.toml tidak ada spasi di depan/belakang.")
            # Tampilkan Email untuk memudahkan copy-paste ulang
            try:
                email = st.secrets["gcp_service_account"]["client_email"]
                st.info(f"Email Robot: `{email}` (Pastikan email ini di-invite)")
            except:
                pass

st.divider()

# --- BAGIAN 3: APLIKASI UTAMA (Original) ---
# (Logika aplikasi Anda berjalan normal di bawah ini)

if 'log_data' not in st.session_state: st.session_state.log_data = []
if 'is_running' not in st.session_state: st.session_state.is_running = False
if 'tasks_config' not in st.session_state: st.session_state.tasks_config = []
if 'current_task_idx' not in st.session_state: st.session_state.current_task_idx = 0
if 'current_page_num' not in st.session_state: st.session_state.current_page_num = 1
if 'last_lap_time' not in st.session_state: st.session_state.last_lap_time = 0
if 'start_global_time' not in st.session_state: st.session_state.start_global_time = 0

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
    
    new_record = {
        "Tugas Ke": current_idx + 1,
        "Halaman Ke": st.session_state.current_page_num,
        "Status": st.session_state.input_status,
        "Durasi": round(duration, 2),
        "Klik Total": st.session_state.input_click_total,
        "Klik Bad": st.session_state.input_click_bad,
        "Error": st.session_state.input_error,
        "Timestamp": datetime.now().strftime('%H:%M:%S')
    }
    st.session_state.log_data.append(new_record)
    
    if st.session_state.current_page_num >= limit:
        st.session_state.current_task_idx += 1
        st.session_state.current_page_num = 1
        if st.session_state.current_task_idx >= len(st.session_state.tasks_config):
            st.session_state.is_running = False
            
            # AUTO UPLOAD
            with st.spinner('Upload ke Drive...'):
                df_final = pd.DataFrame(st.session_state.log_data)
                fname = f"Usability_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv"
                ok, msg = upload_to_drive(df_final, fname)
                if ok:
                    st.balloons()
                    st.success(f"✅ Tersimpan di Drive! (ID: {msg})")
                else:
                    st.error(f"Gagal Upload: {msg}")
    else:
        st.session_state.current_page_num += 1
    st.session_state.last_lap_time = now

# UI UTAMA
if not st.session_state.is_running:
    with st.expander("Konfigurasi & Mulai", expanded=True):
        st.text_input("Config Halaman", value="1, 1", key="config_input") # Default kecil buat tes
        st.button("MULAI OBSERVASI", on_click=start_observation, type="primary")
else:
    task_now = st.session_state.current_task_idx + 1
    page_now = st.session_state.current_page_num
    st.info(f"TUGAS {task_now} | Halaman {page_now}")
    
    col1, col2 = st.columns(2)
    with col1:
        st.number_input("Total Klik", key="input_click_total", min_value=0)
        st.number_input("Total Error", key="input_error", min_value=0)
    with col2:
        st.number_input("Klik Tidak Perlu", key="input_click_bad", min_value=0)
        st.selectbox("Status", ["SUKSES", "GAGAL"], key="input_status")
        
    st.button("NEXT ➡️", on_click=save_and_next, type="primary")