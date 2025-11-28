import streamlit as st
import time
import pandas as pd
from datetime import datetime
from google.oauth2 import service_account
import gspread
import uuid  # Library untuk membuat ID acak

# ==========================================
# 1. SETUP HALAMAN
# ==========================================
st.set_page_config(
    page_title="Usability Guide", 
    page_icon="📱", 
    layout="centered",
    initial_sidebar_state="collapsed" 
)
# ==========================================
# 2. FUNGSI GOOGLE SHEETS (MODE BATCH)
# ==========================================
def batch_upload_to_sheet(all_data_list):
    """
    Mengirim SEMUA data sekaligus di akhir sesi.
    """
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
        
        # Konversi List of Dicts menjadi List of Lists (Rows)
        rows_to_upload = []
        for record in all_data_list:
            row = [
                record["User ID"],   # <--- KOLOM 1: USER ID
                record["Tugas Ke"],
                record["Halaman Ke"],
                record["Status"],
                str(record["Durasi"]).replace('.', ','),
                record["Klik Total"],
                record["Klik Bad"],
                record["Error"],
                record["Timestamp"]
            ]
            rows_to_upload.append(row)

        # Kirim Semua Sekaligus
        worksheet.append_rows(rows_to_upload)
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

# --- BUAT USER ID DISINI ---
if 'user_id' not in st.session_state:
    # Membuat 8 karakter acak (contoh: a1b2c3d4)
    st.session_state.user_id = str(uuid.uuid4())[:8]

# ==========================================
# 4. ADMIN PANEL
# ==========================================
with st.sidebar:
    st.header("⚙️ Admin Panel")
    
    # Tampilkan ID User saat ini (Untuk dicatat peneliti jika perlu)
    st.info(f"🆔 **User ID:** `{st.session_state.user_id}`")
    
    st.divider()

    # A. CONFIG JUMLAH HALAMAN
    st.subheader("1. Struktur Tugas")
    config_input = st.text_input("Jml Halaman per Tugas (koma)", value="3, 3, 4, 3, 5")
    try:
        tasks_config = [int(x.strip()) for x in config_input.split(',') if x.strip().isdigit()]
    except:
        tasks_config = []

    # B. CONFIG TEKS PANDUAN
    st.subheader("2. Teks Panduan")
    st.caption("Format per baris -> Tugas-Hal : Instruksi")
    
    default_scenario = """1-1 : Pengguna mengklik tombol Masuk.
1-2 : Pengguna memasukkan nomor telepon atau email.
1-3 : Pengguna mengklik tombol Masuk, lalu memasukkan PIN.
2-1 : Pastikan berada di Halaman Fitur (Klik tombol fitur di bagian bawah). Klik ikon 'Cari Nakes'.
2-2 : Masukkan kata kunci nakes pada kolom pencarian.
2-3 : Pengguna memilih tenaga kesehatan.
3-1 : Kembali ke Halaman Fitur (Tekan panah kiri atas sampai kembali). Klik ikon 'Sertifikat Vaksin'.
3-2 : Pengguna mengklik Vaksin & Imunisasi Lainnya.
3-3 : Pengguna mengklik salah satu laporan vaksin jika ada.
3-4 : Pengguna mengunduh sertifikat.
4-1 : Kembali ke Halaman Fitur (Tekan panah kiri atas sampai kembali). Klik ikon 'Indeks Massa Tubuh'.
4-2 : Pengguna mengklik tombol Tambah Data Baru.
4-3 : Masukkan data pada kolom, lalu klik tombol Simpan.
5-1 : Kembali ke Halaman Fitur (Tekan panah kiri atas sampai kembali). Klik ikon 'Tiket Pemeriksaan'.
5-2 : Klik Daftar (jika perlu), pilih jadwal, lalu klik Selanjutnya.
5-3 : Klik alamat biru yang berada di atas kolom pencarian.
5-4 : Pilih lokasi dan klik tombol Simpan.
5-5 : Masukkan kata kunci tempat kesehatan, lalu pilih salah satu tempat."""

    scenario_raw = st.text_area("Edit Skenario Disini:", value=default_scenario, height=400)
    
    SCENARIO_GUIDE = {}
    for line in scenario_raw.split('\n'):
        if ':' in line:
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
    
    # 1. SIMPAN KE MEMORI SEMENTARA (LOKAL)
    record = {
        "User ID": st.session_state.user_id, # <--- User ID dimasukkan disini
        "Tugas Ke": idx + 1,
        "Halaman Ke": st.session_state.current_page_num,
        "Status": status,
        "Durasi": round(duration, 2),
        "Klik Total": click_total,
        "Klik Bad": click_bad,
        "Error": error_total,
        "Timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    st.session_state.log_data.append(record)
    st.toast(f"Langkah {st.session_state.current_page_num} Disimpan (Lokal)", icon="📥")

    # 2. NAVIGASI
    if st.session_state.current_page_num >= limit:
        st.session_state.current_task_idx += 1
        st.session_state.current_page_num = 1
        
        # 3. CEK FINISH (Jika ini tugas terakhir)
        if st.session_state.current_task_idx >= len(tasks_config):
            st.session_state.is_running = False
            
            # --- UPLOAD MASSAL (BATCH) DISINI ---
            with st.spinner("Sedang mengirim semua data ke Google Sheets..."):
                ok, msg = batch_upload_to_sheet(st.session_state.log_data)
                
                if ok:
                    st.balloons()
                    st.success("✅ SEMUA DATA BERHASIL DIKIRIM KE GOOGLE SHEETS!")
                else:
                    st.error(f"Gagal kirim ke Cloud: {msg}")
                    st.warning("Jangan tutup halaman! Silakan download manual di bawah.")
            # ------------------------------------
    else:
        st.session_state.current_page_num += 1
    
    st.session_state.last_lap_time = now

# ==========================================
# 6. TAMPILAN USER INTERFACE (UI)
# ==========================================
st.title("📱 Usability Testing")

if not st.session_state.is_running:
    st.info("👋 Selamat Datang. Aplikasi ini akan memandu Anda melakukan pengujian.")
    st.caption(f"ID Sesi Anda: {st.session_state.user_id}")
    st.button("🚀 MULAI PANDUAN", on_click=start_test, type="primary", use_container_width=True)

else:
    # 1. Teks Panduan
    idx = st.session_state.current_task_idx
    page_num = st.session_state.current_page_num
    
    guide_key = f"{idx + 1}-{page_num}"
    instruction_text = SCENARIO_GUIDE.get(guide_key, "Lanjutkan langkah sesuai aplikasi.")
    
    # 2. Kotak Panduan
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
    st.button("✅LANJUT", on_click=next_step, type="primary", use_container_width=True)

# ==========================================
# 7. SCREEN SELESAI & DOWNLOAD
# ==========================================
if not st.session_state.is_running and len(st.session_state.log_data) > 0:
    st.success("🎉 Tes pertama atau kedua selesai! Terima kasih.")
    st.caption(f"User ID: {st.session_state.user_id}")
    st.caption("Data telah dikirim secara otomatis.")
    
    st.divider()
    st.subheader("📥 Download File (Manual)")
    
    df_finish = pd.DataFrame(st.session_state.log_data)
    csv_finish = df_finish.to_csv(index=False).encode('utf-8')
    
    # Nama file mengandung User ID
    st.download_button(
        label="Download CSV (Excel)",
        data=csv_finish,
        file_name=f"Hasil_{st.session_state.user_id}.csv",
        mime="text/csv",
        type="primary"
    )

    # st.divider()
    # if st.button("Mulai Ulang (Responden Baru)"):
    #     # Reset data dan generate ID baru
    #     st.session_state.log_data = []
    #     del st.session_state.user_id 
    #     st.rerun()