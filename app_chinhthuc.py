# Tải thư viện
import streamlit as st
import time
import sqlite3
import pandas as pd
from datetime import datetime
from groq import Groq

# --- 1. KHỞI TẠO CƠ SỞ DỮ LIỆU (SQLITE) ---
def init_db():
    conn = sqlite3.connect('uniguide_history.db')
    c = conn.cursor()
    # Tạo bảng lưu lịch sử nếu chưa có
    c.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thoi_gian TEXT,
            ten_hoc_sinh TEXT,
            diem REAL,
            khoi TEXT,
            nganh TEXT,
            nhom_tinh_cach TEXT,
            so_thich TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_to_db(ten, diem, khoi, nganh, tinh_cach, so_thich):
    conn = sqlite3.connect('uniguide_history.db')
    c = conn.cursor()
    thoi_gian = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('''
        INSERT INTO history (thoi_gian, ten_hoc_sinh, diem, khoi, nganh, nhom_tinh_cach, so_thich)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (thoi_gian, ten, diem, khoi, nganh, tinh_cach, so_thich))
    conn.commit()
    conn.close()

# Chạy hàm khởi tạo DB ngay khi app load
init_db()

# --- 2. CẤU HÌNH API GROQ ---
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
client = Groq(api_key=GROQ_API_KEY)

# --- 3. HÀM GỌI AI ĐƯỢC NÂNG CẤP PROMPT (CHỈ LẤY TRƯỜNG CÔNG LẬP) ---
@st.cache_data(ttl=86400, show_spinner=False)
def get_ai_advice(diem, khoi, nganh, khu_vuc, tinh_cach, so_thich):
    prompt = f"""
    Bạn là một chuyên gia tư vấn hướng nghiệp và tuyển sinh đại học hàng đầu tại Việt Nam.
    LƯU Ý TỐI QUAN TRỌNG: BẠN CHỈ ĐƯỢC PHÉP GỢI Ý CÁC TRƯỜNG ĐẠI HỌC CÔNG LẬP. TUYỆT ĐỐI KHÔNG ĐƯA RA BẤT KỲ TRƯỜNG ĐẠI HỌC TƯ THỤC, DÂN LẬP HAY QUỐC TẾ NÀO (Ví dụ: Tuyệt đối KHÔNG gợi ý FPT, RMIT, Hutech, Hoa Sen, Nguyễn Tất Thành, Văn Lang, Hồng Bàng...).

    Hãy phân tích toàn diện hồ sơ của học sinh lớp 12 sau đây:
    - Điểm thi thử dự kiến: {diem} điểm
    - Tổ hợp môn/Thế mạnh: {khoi}
    - Ngành học quan tâm: {nganh}
    - Khu vực muốn học: {khu_vuc}
    - Đặc điểm tính cách (Nhóm Holland): {tinh_cach}
    - Sở thích/Đam mê cá nhân: {so_thich}

    YÊU CẦU TRẢ LỜI CỦA BẠN:
    1. Đánh giá ngắn gọn (2-3 câu) về mức độ phù hợp giữa điểm số, tính cách, sở thích và ngành {nganh}.
    2. Gợi ý một danh sách từ 5-7 trường ĐẠI HỌC CÔNG LẬP và phải đảm bảo rằng các trường này nằm trong khu vực ({khu_vuc}), phân loại rõ ràng thành 3 nhóm: 
       - Nhóm Thử thách (Điểm chuẩn cao hơn {diem} một chút).
       - Nhóm Vừa sức (Điểm chuẩn ngang bằng {diem}).
       - Nhóm An toàn (Điểm chuẩn thấp hơn {diem} một khoảng an toàn).
    3. Với MỖI TRƯỜNG CÔNG LẬP, cung cấp thông tin sau:
       - Tên trường đầy đủ.
       - Xu hướng điểm chuẩn trong 3 năm gần nhất (ví dụ: 24.5 - 25.2 - 26.0).
       - Đánh giá tỉ lệ chọi/sức nóng của ngành này tại trường đó trong 3 năm qua,nêu cụ thể các con số.
       - Phân tích chi tiết: Tại sao trường này lại phù hợp với tính cách ({tinh_cach}) và sở thích ({so_thich}) của bạn học sinh này.
       - Đánh giá môi trường học tập, phong trào ngoại khóa và cơ sở vật chất.
    """
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile", 
                temperature=0.7, 
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2) 
                continue
            else:
                return f"⚠️ **Hệ thống AI hiện đang bận.**\n\nChi tiết lỗi: {e}"

# --- CẤU HÌNH GIAO DIỆN ---
st.set_page_config(page_title="EduAI - Tư Vấn Chọn Trường", page_icon="🎓", layout="wide")

# Khởi tạo session state
if 'quiz_done' not in st.session_state:
    st.session_state.quiz_done = False
if 'nganh_goi_y' not in st.session_state:
    st.session_state.nganh_goi_y = ""
if 'nhom_tinh_cach' not in st.session_state:
    st.session_state.nhom_tinh_cach = ""

st.title("🎓 Hệ thống UniGuide: Cá nhân hóa hướng nghiệp cùng AI")

# Thiết kế Tab bao gồm Tab cho Giáo viên
tab1, tab2, tab3 = st.tabs(["🧩 Trắc nghiệm & Phân tích chuyên sâu", "🎯 Nhập trực tiếp (Đã có định hướng)", "📊 Cổng Giáo Viên"])

# --- TAB 1: BÀI TEST MỞ RỘNG (Gộp trắc nghiệm & Sở thích) ---
with tab1:
    st.subheader("Bước 1: Khám phá bản thân qua Bài test Holland (Mở rộng)")
    st.markdown("Đánh giá mức độ yêu thích của bạn (1: Rất ghét ➡️ 5: Rất thích)")

    # Mở rộng lên 24 câu hỏi bao quát 6 nhóm
    cau_hoi = [
        {"cau": "1. Sửa chữa máy móc, thiết bị, xe cộ.", "nhom": "Thực tế (R)"},
        {"cau": "2. Làm việc ngoài trời, vận động thể chất.", "nhom": "Thực tế (R)"},
        {"cau": "3. Chế tạo đồ thủ công, lắp ráp linh kiện.", "nhom": "Thực tế (R)"},
        {"cau": "4. Chăm sóc cây cối, động vật.", "nhom": "Thực tế (R)"},
        
        {"cau": "5. Làm thí nghiệm khoa học, hóa học.", "nhom": "Nghiên cứu (I)"},
        {"cau": "6. Giải các bài toán logic, lập trình máy tính.", "nhom": "Nghiên cứu (I)"},
        {"cau": "7. Đọc sách tìm hiểu nguyên lý vũ trụ, tự nhiên.", "nhom": "Nghiên cứu (I)"},
        {"cau": "8. Phân tích dữ liệu để tìm ra quy luật.", "nhom": "Nghiên cứu (I)"},
        
        {"cau": "9. Vẽ tranh, thiết kế đồ họa, chụp ảnh.", "nhom": "Nghệ thuật (A)"},
        {"cau": "10. Chơi nhạc cụ, ca hát hoặc diễn xuất.", "nhom": "Nghệ thuật (A)"},
        {"cau": "11. Sáng tác thơ văn, viết truyện, viết blog.", "nhom": "Nghệ thuật (A)"},
        {"cau": "12. Thích phong cách thời trang độc lạ, tự do.", "nhom": "Nghệ thuật (A)"},
        
        {"cau": "13. Lắng nghe, chia sẻ và tư vấn tâm lý cho bạn bè.", "nhom": "Xã hội (S)"},
        {"cau": "14. Tham gia chiến dịch tình nguyện, từ thiện.", "nhom": "Xã hội (S)"},
        {"cau": "15. Thích dạy kèm, hướng dẫn người khác học bài.", "nhom": "Xã hội (S)"},
        {"cau": "16. Chăm sóc người ốm, người cao tuổi.", "nhom": "Xã hội (S)"},
        
        {"cau": "17. Lãnh đạo một nhóm, làm lớp trưởng/bí thư.", "nhom": "Kinh doanh (E)"},
        {"cau": "18. Bán hàng, kinh doanh online kiếm tiền.", "nhom": "Kinh doanh (E)"},
        {"cau": "19. Tranh luận, thuyết phục người khác đồng ý với mình.", "nhom": "Kinh doanh (E)"},
        {"cau": "20. Lên kế hoạch tổ chức các sự kiện, dạ hội.", "nhom": "Kinh doanh (E)"},
        
        {"cau": "21. Ghi chép thu chi, quản lý tiền bạc rõ ràng.", "nhom": "Nghiệp vụ (C)"},
        {"cau": "22. Sắp xếp hồ sơ, giấy tờ, góc học tập siêu gọn gàng.", "nhom": "Nghiệp vụ (C)"},
        {"cau": "23. Nhập liệu, sử dụng Excel, Word thành thạo.", "nhom": "Nghiệp vụ (C)"},
        {"cau": "24. Làm việc theo một quy trình, luật lệ có sẵn.", "nhom": "Nghiệp vụ (C)"}
    ]

    with st.form("quiz_form"):
        # Chia 2 cột để list câu hỏi đỡ dài
        col_q1, col_q2 = st.columns(2)
        diem_chon = {}
        for i, q in enumerate(cau_hoi):
            if i < 12:
                with col_q1: diem_chon[f"{q['nhom']}_{i}"] = st.slider(q['cau'], 1, 5, 3, key=f"q_{i}")
            else:
                with col_q2: diem_chon[f"{q['nhom']}_{i}"] = st.slider(q['cau'], 1, 5, 3, key=f"q_{i}")
        
        submit_quiz = st.form_submit_button("🔍 Phân tích tính cách")

    if submit_quiz:
        tong_diem = {'Thực tế (R)': 0, 'Nghiên cứu (I)': 0, 'Nghệ thuật (A)': 0, 'Xã hội (S)': 0, 'Kinh doanh (E)': 0, 'Nghiệp vụ (C)': 0}
        for key, score in diem_chon.items():
            nhom = key.split("_")[0]
            tong_diem[nhom] += score
            
        nhom_cao_nhat = max(tong_diem, key=tong_diem.get)
        goi_y = {
            'Thực tế (R)': 'Cơ khí, Điện tử, Xây dựng, Nông - Lâm nghiệp, Giao thông vận tải, Logistics',
            'Nghiên cứu (I)': 'Công nghệ thông tin, Khoa học dữ liệu, Y - Dược, Công nghệ sinh học, Vật lý',
            'Nghệ thuật (A)': 'Thiết kế đồ họa, Kiến trúc, Truyền thông đa phương tiện, Đạo diễn, Ngôn ngữ',
            'Xã hội (S)': 'Tâm lý học, Sư phạm, Quản trị nhân sự, Công tác xã hội, Điều dưỡng',
            'Kinh doanh (E)': 'Quản trị kinh doanh, Marketing, Luật Kinh tế, Tài chính, Bất động sản',
            'Nghiệp vụ (C)': 'Kế toán, Kiểm toán, Quản trị văn phòng, Hệ thống thông tin quản lý'
        }
        
        st.session_state.nhom_tinh_cach = nhom_cao_nhat
        st.session_state.nganh_goi_y = goi_y[nhom_cao_nhat]
        st.session_state.quiz_done = True

    if st.session_state.quiz_done:
        st.success(f"🎉 Hệ thống phân tích bạn thuộc nhóm: **{st.session_state.nhom_tinh_cach}**")
        st.info(f"💡 Nhóm ngành lý tưởng: {st.session_state.nganh_goi_y}")
        
        st.markdown("### Bước 2: Bổ sung thông tin & Lấy gợi ý trường")
        with st.container(border=True):
            ten_hs = st.text_input("Tên của bạn (Để giáo viên hỗ trợ sau này):", placeholder="VD: Nguyễn Văn A - Lớp 12A1")
            
            c_info1, c_info2 = st.columns(2)
            with c_info1:
                diem_q = st.number_input("Điểm thi thử hiện tại", min_value=0.0, max_value=30.0, value=20.0)
                khoi_q = st.text_input("Khối thi (VD: A00, D01)", value="A01")
            with c_info2:
                nganh_q = st.text_input("Ngành muốn AI phân tích sâu", value=st.session_state.nganh_goi_y.split(',')[0])
                khu_vuc_q = st.selectbox("Khu vực học", ["Miền Bắc", "Miền Trung", "Miền Nam"])
            
            so_thich_q = st.text_area("Kể thêm về sở thích, đam mê cá nhân hoặc hoạt động ngoại khóa của bạn (Càng chi tiết AI gợi ý càng chuẩn):", 
                                      placeholder="VD: Mình thích chơi game chiến thuật, hay tham gia CLB tranh biện và rất thích đọc sách lịch sử...")

            if st.button("✨ Để AI Lên Danh Sách Trường Ngay", type="primary"):
                if ten_hs == "":
                    st.warning("Vui lòng nhập tên của bạn nhé!")
                else:
                    with st.spinner('AI đang tổng hợp lịch sử điểm chuẩn 3 năm và tỉ lệ chọi...'):
                        ket_qua_quiz = get_ai_advice(diem_q, khoi_q, nganh_q, khu_vuc_q, st.session_state.nhom_tinh_cach, so_thich_q)
                        
                        # Lưu lịch sử vào CSDL
                        save_to_db(ten_hs, diem_q, khoi_q, nganh_q, st.session_state.nhom_tinh_cach, so_thich_q)
                        
                        with st.expander("📝 DANH SÁCH TRƯỜNG ĐẠI HỌC DÀNH RIÊNG CHO BẠN", expanded=True):
                            st.markdown(ket_qua_quiz)

# --- TAB 2: ĐÃ CÓ ĐỊNH HƯỚNG ---
with tab2:
    st.subheader("Dành cho học sinh không cần làm bài test tính cách")
    t2_col1, t2_col2 = st.columns(2)
    with t2_col1:
        t2_ten = st.text_input("Họ và Tên:", key="t2_ten")
        t2_diem = st.number_input("Điểm thi thử", min_value=0.0, max_value=30.0, value=24.0, step=0.1, key="t2_diem")
        t2_khoi = st.text_input("Khối thi", value="D01", key="t2_khoi")
    with t2_col2:
        t2_nganh = st.text_input("Ngành học mong muốn", key="t2_nganh")
        t2_khu_vuc = st.selectbox("Khu vực", ["Miền Bắc", "Miền Trung", "Miền Nam"], key="t2_kv")
        t2_tinh_cach = st.selectbox("Bạn tự đánh giá mình thuộc nhóm người nào?", 
                                    ["Thực tế - Thích kỹ thuật", "Nghiên cứu - Logic", "Nghệ thuật - Sáng tạo", 
                                     "Xã hội - Thích giao tiếp", "Kinh doanh - Lãnh đạo", "Nghiệp vụ - Cẩn thận"])
    
    t2_sothich = st.text_area("Đam mê/Sở thích nổi bật:", key="t2_st")
    
    if st.button("🚀 Gợi ý trường", type="primary", key="btn_tab2"):
        if t2_nganh and t2_ten:
            with st.spinner('AI đang quét dữ liệu điểm chuẩn 3 năm...'):
                ket_qua = get_ai_advice(t2_diem, t2_khoi, t2_nganh, t2_khu_vuc, t2_tinh_cach, t2_sothich)
                save_to_db(t2_ten, t2_diem, t2_khoi, t2_nganh, t2_tinh_cach, t2_sothich)
                with st.expander("📝 XEM KẾT QUẢ CỦA AI", expanded=True):
                    st.markdown(ket_qua)
        else:
            st.warning("Vui lòng điền đủ Tên và Ngành học!")

# --- TAB 3: CỔNG QUẢN LÝ DÀNH CHO GIÁO VIÊN ---
with tab3:
    st.subheader("📊 Bảng điều khiển dành cho Giáo viên Hướng nghiệp")
    st.markdown("Giáo viên có thể theo dõi nguyện vọng, định hướng tính cách của học sinh để có phương án tư vấn trực tiếp tốt hơn.")
    
    # Tạo mật khẩu đơn giản để khóa Tab này
    mk_gv = st.text_input("Nhập mật khẩu giáo viên", type="password")
    
    if mk_gv == "admin123":
        st.success("Đăng nhập thành công!")
        # Đọc dữ liệu từ SQLite
        conn = sqlite3.connect('uniguide_history.db')
        df = pd.read_sql_query("SELECT * FROM history ORDER BY id DESC", conn)
        conn.close()
        
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            
            # Tính năng tải file Excel (CSV)
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 Tải dữ liệu báo cáo (CSV)",
                data=csv,
                file_name='Thong_ke_huong_nghiep_hoc_sinh.csv',
                mime='text/csv',
            )
        else:
            st.info("Chưa có học sinh nào sử dụng hệ thống.")