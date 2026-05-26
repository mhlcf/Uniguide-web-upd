# Tải thư viện cần thiết
import os
import sqlite3
import time
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from groq import Groq

# Đường dẫn gốc tuyệt đối của thư mục chứa app.py
# Đây là chìa khóa để gunicorn trên Render tìm đúng file dù chạy từ thư mục nào
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Khởi tạo Flask Application
app = Flask(__name__, static_folder=BASE_DIR, static_url_path='')

# --- 1. CẤU HÌNH API GROQ CHUYÊN NGHIỆP ---
# Lấy API Key từ Biến môi trường (Environment Variable) - Phương pháp bảo mật chuẩn cho Render/Đám mây
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Dự phòng: Nếu chạy local chưa set env, tự động tìm và nạp từ tệp secrets của streamlit cũ nếu có
if not GROQ_API_KEY:
    try:
        # Đường dẫn mặc định của streamlit secrets local
        secrets_path = os.path.expanduser("~/.streamlit/secrets.toml")
        if os.path.exists(secrets_path):
            with open(secrets_path, "r") as f:
                for line in f:
                    if "GROQ_API_KEY" in line:
                        GROQ_API_KEY = line.split("=")[1].replace('"', '').replace("'", "").strip()
                        break
    except Exception:
        pass

# Khởi tạo Client Groq nếu đã tìm thấy key
client = None
if GROQ_API_KEY:
    client = Groq(api_key=GROQ_API_KEY)


# --- 2. KHỞI TẠO CƠ SỞ DỮ LIỆU SQLITE ---
# Dùng đường dẫn tuyệt đối để Render luôn tìm đúng vị trí file database
DATABASE_FILE = os.path.join(BASE_DIR, 'uniguide_history.db')

def init_db():
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    # Tạo bảng lưu lịch sử tư vấn nếu chưa tồn tại
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
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    thoi_gian = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('''
        INSERT INTO history (thoi_gian, ten_hoc_sinh, diem, khoi, nganh, nhom_tinh_cach, so_thich)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (thoi_gian, ten, diem, khoi, nganh, tinh_cach, so_thich))
    conn.commit()
    conn.close()

# Chạy hàm khởi tạo database ngay khi chạy server
init_db()


# --- 3. ĐỊNH TUYẾN WEB SERVER (ROUTING) ---

# Trả về trang chủ giao diện Frontend index.html
@app.route('/')
def home():
    index_path = os.path.join(BASE_DIR, 'index.html')
    if os.path.exists(index_path):
        return send_file(index_path)
    else:
        return "<h3>Lỗi: Không tìm thấy tệp tin index.html tại thư mục gốc!</h3>", 404


# --- 4. CÁC API CỦA HỆ THỐNG (REST API ENDPOINTS) ---

# API xử lý tư vấn tuyển sinh thông minh từ AI (Groq Llama-3.3-70b)
@app.route('/api/get_advice', methods=['POST'])
def api_get_advice():
    # Nhận dữ liệu từ request JSON gửi lên từ index.html
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "Dữ liệu yêu cầu không hợp lệ!"}), 400

    name = data.get("name", "").strip()
    score = float(data.get("score", 20.0))
    block = data.get("block", "").strip().upper()
    region = data.get("region", "Miền Bắc")
    holland = data.get("holland", "I")
    passions = data.get("passions", "").strip()
    industry = data.get("industry", "Công nghệ thông tin").strip()

    if not name or not block or not industry:
        return jsonify({"success": False, "error": "Vui lòng nhập đầy đủ các thông tin bắt buộc!"}), 400

    # Lời nhắc chuyên nghiệp nâng cao (Prompt) giống phiên bản app_chinhthuc.py
    prompt = f"""
    Bạn là một chuyên gia tư vấn hướng nghiệp và tuyển sinh đại học hàng đầu tại Việt Nam.
    LƯU Ý TỐI QUAN TRỌNG: BẠN CHỈ ĐƯỢC PHÉP GỢI Ý CÁC TRƯỜNG ĐẠI HỌC CÔNG LẬP. TUYỆT ĐỐI KHÔNG ĐƯA RA BẤT KỲ TRƯỜNG ĐẠI HỌC TƯ THỤC, DÂN LẬP HAY QUỐC TẾ NÀO (Ví dụ: Tuyệt đối KHÔNG gợi ý FPT, RMIT, Hutech, Hoa Sen, Nguyễn Tất Thành, Văn Lang, Hồng Bàng...).

    Hãy phân tích toàn diện hồ sơ của học sinh lớp 12 sau đây:
    - Họ tên học sinh: {name}
    - Điểm thi thử dự kiến: {score} điểm
    - Tổ hợp môn xét tuyển (Khối thi): {block}
    - Ngành học quan tâm: {industry}
    - Khu vực muốn học: {region}
    - Đặc điểm tính cách (Nhóm Holland): {holland}
    - Sở thích/Đam mê cá nhân: {passions}

    YÊU CẦU TRẢ LỜI VÀ TRÌNH BÀY BÁO CÁO CỦA BẠN (CỰC KỲ QUAN TRỌNG):
    Hãy trình bày báo cáo hướng nghiệp thật chuyên nghiệp, dễ hiểu bằng tiếng Việt có cấu trúc đẹp mắt bằng Markdown.
    
    1. **PHẦN 1: ĐÁNH GIÁ TỔNG QUAN HỒ SƠ**:
       Phân tích ngắn gọn (2-3 câu) về mức độ phù hợp giữa năng lực điểm số ({score}), khối thi ({block}), đặc trưng nhóm tính cách Holland ({holland}) cùng những sở thích cá nhân ({passions}) đối với ngành học mục tiêu ({industry}).

    2. **PHẦN 2: CHI TIẾT CÁC GỢI Ý TRƯỜNG THEO TỪNG NHÓM TIERS (5-7 trường Đại học Công lập)**:
       Bạn phải gợi ý danh sách các trường ĐẠI HỌC CÔNG LẬP phù hợp nhất trong khu vực ({region}), được tổ chức rõ ràng thành 3 phần:
       - **NHÓM THỬ THÁCH** (Điểm chuẩn cao hơn điểm {score} của học sinh từ 0.5 đến 1.5 điểm).
       - **NHÓM VỪA SỨC** (Điểm chuẩn ngang bằng hoặc chênh lệch tối thiểu với điểm {score} của học sinh).
       - **NHÓM AN TOÀN** (Điểm chuẩn thấp hơn điểm {score} của học sinh từ 1.5 đến 3 điểm).

       **YÊU CẦU BẮT BUỘC KHI VIẾT**: 
       Ở MỖI NHÓM TIERS (Thử thách, Vừa sức, An toàn), bạn phải liệt kê chi tiết từng trường đại học công lập trong nhóm đó. DƯỚI TÊN MỖI TRƯỜNG HỌC, bạn PHẢI phân tích cụ thể, rõ ràng từng trường một mà không được gộp chung hay viết tóm tắt đại khái. 
       Với MỖI TRƯỜNG ĐẠI HỌC CÔNG LẬP, hãy cung cấp đầy đủ các mục chi tiết sau:
       * **Tên đầy đủ và Tên viết tắt** của trường.
       * **Ước lượng xu hướng điểm chuẩn ngành {industry} trong 3 năm gần nhất** (nêu rõ con số cụ thể cho năm 2023, 2024, 2025).
       * **Đánh giá tỉ lệ chọi & Sức nóng tuyển sinh** của ngành học này tại trường trong những mùa tuyển sinh qua.
       * **Phân tích chiều sâu (Holland & Đam mê)**: Lý giải chi tiết tại sao môi trường đào tạo và triết lý của trường này lại rất thích hợp với đặc trưng tính cách ({holland}) và sở thích cá nhân ({passions}) của học sinh này.
       * **Môi trường học tập & Đời sống câu lạc bộ**: Đánh giá chi tiết cơ sở vật chất, các chương trình liên kết doanh nghiệp, câu lạc bộ học thuật/ngoại khóa nổi bật của trường hỗ trợ cho ngành học {industry}.
    """

    # Gọi AI bằng Groq API
    if not client:
        # Nếu chưa cấu hình API Key, hiển thị cảnh báo hướng dẫn cấu hình
        time.sleep(1.5) # Tạo độ trễ nhẹ cho hiệu ứng tải thật
        return jsonify({
            "success": False, 
            "error": "Chưa tìm thấy khóa bảo mật GROQ_API_KEY của bạn trên máy chủ! Vui lòng cấu hình API Key trong phần Environment Variables trên Render hoặc tạo biến cục bộ để sử dụng."
        }), 500

    max_retries = 3
    ai_advice = ""
    for attempt in range(max_retries):
        try:
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                temperature=0.7,
            )
            ai_advice = chat_completion.choices[0].message.content
            break
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            else:
                return jsonify({"success": False, "error": f"Hệ thống AI hiện đang bận. Chi tiết lỗi: {e}"}), 500

    # Lưu lịch sử tư vấn thành công vào CSDL SQLite để theo dõi báo cáo
    try:
        save_to_db(name, score, block, industry, holland, passions)
    except Exception as e:
        print(f"Lỗi khi lưu SQLite: {e}")

    # Trả kết quả tư vấn về cho Frontend
    return jsonify({
        "success": True,
        "advice": ai_advice
    })


# API lấy toàn bộ danh sách lịch sử học sinh cho Cổng Giáo Viên
@app.route('/api/get_history', methods=['POST'])
def api_get_history():
    data = request.get_json()
    if not data or data.get("password") != "admin123":
        return jsonify({"success": False, "error": "Mật khẩu Cổng Giáo Viên không chính xác!"}), 401

    try:
        conn = sqlite3.connect(DATABASE_FILE)
        # Sử dụng Row để lấy dữ liệu dạng Dictionary tiện lợi
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM history ORDER BY id DESC")
        rows = c.fetchall()
        conn.close()

        # Định dạng dữ liệu trả về cho client
        history_list = []
        for r in rows:
            history_list.append({
                "id": r["id"],
                "date": r["thoi_gian"],
                "name": r["ten_hoc_sinh"],
                "score": r["diem"],
                "block": r["khoi"],
                "industry": r["nganh"],
                "holland": r["nhom_tinh_cach"],
                "passion": r["so_thich"]
            })

        return jsonify({
            "success": True,
            "history": history_list
        })
    except Exception as e:
        return jsonify({"success": False, "error": f"Lỗi đọc CSDL SQLite: {e}"}), 500


# Chạy ứng dụng trực tiếp nếu thực thi file python này
if __name__ == '__main__':
    # Local port 5000 mặc định
    app.run(host='0.0.0.0', port=5000, debug=True)
