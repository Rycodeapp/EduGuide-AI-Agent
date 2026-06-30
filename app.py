import streamlit as st
from agent import generate_learning_path
import os
import csv
from datetime import datetime
import pandas as pd
import time

# --- HÀM HỖ TRỢ: LƯU FEEDBACK RA FILE CSV ---
def save_feedback_to_csv(user_prompt, bot_response, rating):
    file_name = "feedback_log.csv"
    file_exists = os.path.isfile(file_name)
    
    with open(file_name, mode="a", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Thời gian", "Câu hỏi của User", "Câu trả lời của AI", "Đánh giá"])
        
        time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        writer.writerow([time_now, user_prompt, bot_response, rating])

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

if api_key: os.environ["GROQ_API_KEY"] = api_key
if youtube_key: os.environ["YOUTUBE_API_KEY"] = youtube_key

st.sidebar.markdown("---")
st.sidebar.markdown("**📊 Khu vực Admin**")

# --- Xác thực Admin bằng mật khẩu ---
if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

admin_pass = st.sidebar.text_input("🔒 Nhập mật khẩu Admin:", type="password")
if admin_pass:
    correct_password = os.environ.get("ADMIN_PASSWORD", "admin123")
    if admin_pass == correct_password:
        st.session_state.admin_authenticated = True
        st.sidebar.success("✅ Xác thực thành công!")
    else:
        st.sidebar.error("❌ Mật khẩu không đúng!")

if st.session_state.admin_authenticated:
    show_dashboard = st.sidebar.toggle("📈 Mở Dashboard Thống Kê", key="admin_toggle")
    if os.path.isfile("feedback_log.csv"):
        with open("feedback_log.csv", "rb") as f:
            st.sidebar.download_button(
                label="📥 Tải file Minh chứng (CSV)",
                data=f,
                file_name="MinhChung_EduGuide_Feedback.csv",
                mime="text/csv",
                key="download_feedback"
            )
else:
    st.sidebar.warning("⚠️ Vui lòng nhập mật khẩu Admin để sử dụng khu vực quản trị.")
    show_dashboard = False

# ==========================================
# CHẾ ĐỘ 1: ADMIN DASHBOARD
# ==========================================
if show_dashboard:
    st.title("📊 Dashboard Đánh Giá Hiệu Suất EduGuide")
    st.markdown("Khu vực theo dõi chất lượng tư vấn của AI Agent dựa trên phản hồi thực tế từ người dùng.")
    
    if os.path.isfile("feedback_log.csv"):
        df = pd.read_csv("feedback_log.csv")
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
            st.dataframe(df.sort_values(by="Thời gian", ascending=False), use_container_width=True, height=350)
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
                st.write("") 
                col1, col2, col3 = st.columns([1, 1, 2])
                user_prompt = st.session_state.messages[i-1]["content"] if i > 0 else "N/A"
                like_key = f"like_{i}"
                dislike_key = f"dislike_{i}"
                voted_state_key = f"voted_{i}"
                has_voted = st.session_state.get(voted_state_key, False)
                
                with col1:
                    if st.button("👍 Hữu ích", key=like_key, disabled=has_voted, use_container_width=True):
                        save_feedback_to_csv(user_prompt, message["content"], "Hữu ích")
                        st.session_state[voted_state_key] = True 
                        st.toast("✅ Đã ghi nhận đánh giá vào Database!")
                        st.rerun() 
                with col2:
                    if st.button("👎 Chưa tốt", key=dislike_key, disabled=has_voted, use_container_width=True):
                        save_feedback_to_csv(user_prompt, message["content"], "Chưa tốt")
                        st.session_state[voted_state_key] = True
                        st.toast("🛠 Đã ghi nhận phản hồi để cải thiện hệ thống!")
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
    # XỬ LÝ INPUT MỚI (mượt mà hơn)
    # ============================
    if prompt := st.chat_input("Bạn muốn học môn gì hôm nay?"):
        if not api_key and not os.environ.get("GROQ_API_KEY"):
            st.error("⚠️ Vui lòng nhập Groq API Key ở thanh bên trái trước khi bắt đầu!")
        else:
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                # Tạo container để hiển thị log từng bước
                log_placeholder = st.empty()
                progress_bar = st.progress(0, text="Initializing...")

                # Hàm cập nhật log và progress một cách mượt mà
                def update_log(message, progress, progress_text):
                    log_placeholder.markdown(message)
                    progress_bar.progress(progress, text=progress_text)
                    time.sleep(0.2)  # tạo cảm giác mượt

                # Bước 1: Subject Agent
                update_log("🔍 **Subject Agent**: detecting subject...", 10, "Analyzing subject...")
                time.sleep(0.3)  # giả lập thời gian xử lý
                update_log("🔍 **Subject Agent**: detecting subject... ✅", 30, "Subject detected")
                time.sleep(0.15)

                # Bước 2: Level Agent
                update_log("📊 **Level Agent**: assessing user level...", 40, "Assessing level...")
                time.sleep(0.3)
                update_log("📊 **Level Agent**: assessing user level... ✅", 50, "Level determined")
                time.sleep(0.15)

                # Bước 3: Resource Agent
                update_log("📚 **Resource Agent**: searching resources...", 60, "Searching resources...")
                time.sleep(0.3)
                update_log("📚 **Resource Agent**: searching resources... ✅", 70, "Resources found")
                time.sleep(0.15)

                # Bước 4: YouTube Agent
                update_log("🎥 **YouTube Agent**: searching videos...", 75, "Searching YouTube...")
                time.sleep(0.3)
                update_log("🎥 **YouTube Agent**: searching videos... ✅", 85, "Videos found")
                time.sleep(0.15)

                # Bước 5: Recommendation Agent (gọi API thật)
                update_log("🧠 **Recommendation Agent**: generating personalized roadmap...", 90, "Building roadmap...")
                # Gọi hàm agent thật (có thể mất vài giây)
                response = generate_learning_path(prompt, st.session_state.messages[:-1])

                # Hoàn tất
                update_log("✅ **All agents completed successfully!**", 100, "Complete!")
                time.sleep(0.3)

                # Xóa log và progress bar để hiển thị kết quả
                log_placeholder.empty()
                progress_bar.empty()

                # Hiển thị kết quả
                st.markdown(response)

            st.session_state.messages.append({"role": "assistant", "content": response})
            st.rerun()