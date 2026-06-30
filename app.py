import streamlit as st
from agent import generate_learning_path, detect_subject_and_level, search_youtube, search_free_course, load_knowledge_base, get_resources_for_subject
import os
import pandas as pd
import time
import logging
from feedback_db import init_db, save_feedback, get_feedback_data

# Setup logging
logging.basicConfig(level=logging.INFO)

# Khởi tạo database
init_db()

# Cấu hình trang
st.set_page_config(page_title="EduGuide - AI Agent", page_icon="🎓", layout="wide")

# Khởi tạo session state
if "feedback" not in st.session_state:
    st.session_state.feedback = []
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- SIDEBAR CÀI ĐẶT ---
st.sidebar.header("⚙️ Cài đặt Hệ thống")
api_key = st.sidebar.text_input("🔑 Groq API Key:", type="password")
youtube_key = st.sidebar.text_input("🎥 YouTube API Key (tùy chọn):", type="password")

if api_key:
    os.environ["GROQ_API_KEY"] = api_key
if youtube_key:
    os.environ["YOUTUBE_API_KEY"] = youtube_key

st.sidebar.markdown("---")
st.sidebar.markdown("**📊 Khu vực Admin**")

# --- Xác thực Admin ---
if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

admin_pass = st.sidebar.text_input("🔒 Nhập mật khẩu Admin:", type="password")
if admin_pass:
    correct_password = os.environ.get("ADMIN_PASSWORD")
    if correct_password is None:
        st.sidebar.error("⚠️ Chưa cấu hình biến môi trường ADMIN_PASSWORD. Vui lòng đặt nó trước khi chạy.")
        st.stop()
    if admin_pass == correct_password:
        st.session_state.admin_authenticated = True
        st.sidebar.success("✅ Xác thực thành công!")
    else:
        st.sidebar.error("❌ Mật khẩu không đúng!")

if st.session_state.admin_authenticated:
    show_dashboard = st.sidebar.toggle("📈 Mở Dashboard Thống Kê", key="admin_toggle")
    # Nút tải xuống dữ liệu feedback (từ SQLite)
    if st.sidebar.button("📥 Tải file Minh chứng (CSV)"):
        data = get_feedback_data()
        if data:
            df = pd.DataFrame(data, columns=["Thời gian", "Câu hỏi của User", "Câu trả lời của AI", "Đánh giá"])
            csv = df.to_csv(index=False, encoding='utf-8-sig')
            st.sidebar.download_button(
                label="📥 Tải file CSV",
                data=csv,
                file_name="MinhChung_EduGuide_Feedback.csv",
                mime="text/csv"
            )
        else:
            st.sidebar.warning("Chưa có dữ liệu feedback.")
else:
    st.sidebar.warning("⚠️ Vui lòng nhập mật khẩu Admin để sử dụng khu vực quản trị.")
    show_dashboard = False

# ==========================================
# CHẾ ĐỘ 1: ADMIN DASHBOARD
# ==========================================
if show_dashboard:
    st.title("📊 Dashboard Đánh Giá Hiệu Suất EduGuide")
    st.markdown("Khu vực theo dõi chất lượng tư vấn của AI Agent dựa trên phản hồi thực tế từ người dùng.")
    
    data = get_feedback_data()
    if data:
        df = pd.DataFrame(data, columns=["Thời gian", "Câu hỏi của User", "Câu trả lời của AI", "Đánh giá"])
        total_feedback = len(df)
        likes = len(df[df["Đánh giá"] == "Hữu ích"])
        dislikes = len(df[df["Đánh giá"] == "Chưa tốt"])
        
        col1, col2, col3 = st.columns(3)
        col1.metric(label="💬 Tổng số Đánh giá", value=total_feedback)
        col2.metric(label="👍 Phản hồi Hữu ích", value=likes, delta=f"{(likes/total_feedback)*100:.1f}%" if total_feedback>0 else "0%")
        col3.metric(label="👎 Phản hồi Chưa tốt", value=dislikes, delta=f"{(dislikes/total_feedback)*100:.1f}%" if total_feedback>0 else "0%", delta_color="inverse")
        
        st.markdown("---")
        col_chart, col_data = st.columns([1, 2])
        with col_chart:
            st.subheader("Biểu đồ Phân bổ")
            chart_data = pd.DataFrame({
                "Đánh giá": ["Hữu ích", "Chưa tốt"],
                "Số lượng": [likes, dislikes]
            })
            st.bar_chart(chart_data.set_index("Đánh giá"), color=["#4CAF50"])
        with col_data:
            st.subheader("Chi tiết Phản hồi (Mới nhất)")
            st.dataframe(df, use_container_width=True, height=350)
    else:
        st.info("Chưa có dữ liệu đánh giá nào. Hãy quay lại màn hình Chat để trải nghiệm và để lại đánh giá nhé!")

# ==========================================
# CHẾ ĐỘ 2: GIAO DIỆN CHATBOT
# ==========================================
else:
    st.title("🎓 EduGuide: Trợ lý lộ trình học tập IT by P&M")
    st.markdown("Nhập môn học và trình độ của bạn (Ví dụ: *Tôi muốn học Python* hoặc *Tài liệu Thuật toán mức độ Intermediate*).")
    
    # Hiển thị lịch sử chat
    for i, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant" and i == len(st.session_state.messages) - 1:
                # Chỉ hiển thị nút đánh giá và tải cho tin nhắn cuối cùng
                col1, col2, col3 = st.columns([1, 1, 2])
                user_prompt = st.session_state.messages[i-1]["content"] if i > 0 else "N/A"
                like_key = f"like_{i}"
                dislike_key = f"dislike_{i}"
                voted_state_key = f"voted_{i}"
                has_voted = st.session_state.get(voted_state_key, False)
                
                with col1:
                    if st.button("👍 Hữu ích", key=like_key, disabled=has_voted, use_container_width=True):
                        save_feedback(user_prompt, message["content"], "Hữu ích")
                        st.session_state[voted_state_key] = True 
                        st.toast("✅ Đã ghi nhận đánh giá!")
                        st.rerun()
                with col2:
                    if st.button("👎 Chưa tốt", key=dislike_key, disabled=has_voted, use_container_width=True):
                        save_feedback(user_prompt, message["content"], "Chưa tốt")
                        st.session_state[voted_state_key] = True
                        st.toast("🛠 Đã ghi nhận phản hồi để cải thiện!")
                        st.rerun()
                with col3:
                    st.download_button(
                        label="📥 Tải lộ trình (.md)",
                        data=message["content"],
                        file_name="LoTrinhHocTap_EduGuide.md",
                        mime="text/markdown",
                        use_container_width=True
                    )

    # ============================
    # XỬ LÝ INPUT MỚI (với progress bar thực tế)
    # ============================
    if prompt := st.chat_input("Bạn muốn học môn gì hôm nay?"):
        if not api_key and not os.environ.get("GROQ_API_KEY"):
            st.error("⚠️ Vui lòng nhập Groq API Key ở thanh bên trái trước khi bắt đầu!")
        else:
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                # Tạo container để hiển thị tiến trình
                status_placeholder = st.empty()
                progress_bar = st.progress(0, text="Bắt đầu...")
                
                # Bước 1: Detect subject và level
                status_placeholder.info("🔍 Đang xác định môn học và trình độ...")
                progress_bar.progress(10, text="Đang phân tích...")
                recent_history = st.session_state.messages[:-1]
                history_str = "\n".join([f"{m['role']}: {m['content']}" for m in recent_history[-4:]])
                context = f"{history_str}\nuser: {prompt}"
                subject, level = detect_subject_and_level(context)
                time.sleep(0.2)  # tạo cảm giác xử lý
                
                # Kiểm tra nếu thiếu thông tin
                if not subject or not level:
                    # Có thể xử lý riêng hoặc để generate_learning_path trả về câu hỏi
                    # Nhưng ta vẫn gọi hàm chính để nhận phản hồi
                    pass
                
                status_placeholder.info("📚 Đang tìm tài nguyên phù hợp...")
                progress_bar.progress(40, text="Đang tìm sách và khóa học...")
                time.sleep(0.2)
                
                status_placeholder.info("🧠 Đang tạo lộ trình học tập...")
                progress_bar.progress(70, text="Đang sinh lời khuyên...")
                # Gọi hàm generate (sẽ bao gồm cả YouTube và MOOCs)
                response = generate_learning_path(prompt, st.session_state.messages[:-1])
                time.sleep(0.2)
                
                status_placeholder.success("✅ Hoàn tất!")
                progress_bar.progress(100, text="Xong!")
                time.sleep(0.3)
                # Xóa status và progress bar để hiển thị kết quả
                status_placeholder.empty()
                progress_bar.empty()
                
                # Hiển thị kết quả
                st.markdown(response)
                
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.rerun()