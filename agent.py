import json
import os
import urllib.parse
from groq import Groq
from prompts import get_system_prompt
from googleapiclient.discovery import build

def get_groq_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY chưa được đặt.")
    return Groq(api_key=api_key)

def load_knowledge_base():
    with open('resources.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def search_youtube(query, max_results=3):
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key: return None
    try:
        search_query = f"{query} beginner full course tutorial" 
        youtube = build('youtube', 'v3', developerKey=api_key)
        request = youtube.search().list(q=search_query, part='snippet', maxResults=max_results, type='video')
        response = request.execute()
        items = response.get('items', [])
        if not items: return None
        results = []
        for item in items:
            video_id = item['id']['videoId']
            title = item['snippet']['title']
            link = f"https://www.youtube.com/watch?v={video_id}"
            results.append(f"[{title}]({link})")
        return results
    except Exception as e:
        print(f"Lỗi YouTube: {e}")
        return None

def search_free_course(subject, level):
    if not subject: return None
    level_str = level if level else "beginner"
    query_coursera = urllib.parse.quote(f"{subject} {level_str} free")
    query_edx = urllib.parse.quote(f"{subject}")
    query_fcc = urllib.parse.quote(f"{subject}")
    links = [
        f"[🎓 Tìm khóa **{subject}** trên Coursera (Chọn chế độ 'Audit' để học miễn phí)](https://www.coursera.org/search?query={query_coursera})",
        f"[🏛️ Khóa học **{subject}** trên edX (Harvard, MIT...)](https://www.edx.org/search?q={query_edx})",
        f"[💻 Bài tập thực hành **{subject}** trên freeCodeCamp](https://www.freecodecamp.org/news/search/?query={query_fcc})"
    ]
    return links

def detect_subject_by_ai(conversation_context):
    """Sub-Agent 1: Nhận diện Môn học từ NGỮ CẢNH HỘI THOẠI"""
    try:
        client = get_groq_client()
        system_prompt = """Nhiệm vụ: Đọc đoạn hội thoại, trả về DUY NHẤT 1 cụm từ khóa tiếng Anh môn học IT đang được nhắc đến. 
VD: "Làm sao code web" -> Web development"""
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant", 
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Đoạn hội thoại:\n{conversation_context}\n\nOutput:"}
            ],
            temperature=0.0, max_tokens=10
        )
        res = completion.choices[0].message.content.strip().replace("Output:", "").replace('"', '').strip()
        if "NONE" in res.upper() or res == "" or len(res) > 30: return None
        return res
    except: return None

def detect_level_by_ai(conversation_context):
    """Sub-Agent 2: Nhận diện Trình độ từ NGỮ CẢNH HỘI THOẠI"""
    try:
        client = get_groq_client()
        system_prompt = """Nhiệm vụ: Phân loại trình độ người dùng từ đoạn hội thoại. Trả về 1 trong 4 từ: Beginner, Intermediate, Advanced, UNKNOWN."""
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant", 
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Đoạn hội thoại:\n{conversation_context}\n\nOutput:"}
            ],
            temperature=0.0, max_tokens=10
        )
        res = completion.choices[0].message.content.strip().replace("Output:", "").strip()
        if res not in ["Beginner", "Intermediate", "Advanced"]: return None
        return res
    except: return None
    
# Đã nâng cấp hàm: Thêm tham số chat_history
def generate_learning_path(user_input, chat_history=[]):
    try:
        recent_history = chat_history[-4:] 
        history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in recent_history])
        conversation_context = f"{history_str}\nuser: {user_input}"
        
        # Gọi Sub-Agent phân tích
        subject = detect_subject_by_ai(conversation_context)
        level = detect_level_by_ai(conversation_context)
        
        kb = load_knowledge_base()
        
        # ==========================================
        # 🔥 TỐI ƯU HÓA TOKEN CHỐNG SẬP API
        # ==========================================
        filtered_kb = {}
        # Nếu đã nhận diện được môn học, chỉ trích xuất đúng môn đó từ JSON
        if subject:
            # So khớp tương đối từ khóa với các key trong JSON
            subject_lower = subject.lower()
            for key, value in kb.items():
                if key.replace("_", " ") in subject_lower or subject_lower in key.replace("_", " "):
                    filtered_kb[key] = value
                    break
                    
        # Nếu không tìm thấy hoặc chưa có subject, đành gửi file trống hoặc toàn bộ
        if not filtered_kb and not subject:
            filtered_kb = kb 
            
        kb_string = json.dumps(filtered_kb, indent=2, ensure_ascii=False)
        # ==========================================
        
        system_prompt = get_system_prompt(kb_string, subject, level)
        client = get_groq_client()
        
        messages = [{"role": "system", "content": system_prompt}]
        for msg in recent_history:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_input})
        
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.3,
            max_tokens=1024
        )
        response = completion.choices[0].message.content


        # 4. CHỈ tích hợp YouTube/Khóa học nếu CÓ ĐỦ Môn và Trình độ
        if subject and level:
            videos = search_youtube(subject)
            mooc_links = search_free_course(subject, level)
            if videos:
                response += f"\n\n---\n### ▶️ Kênh YouTube Khuyến nghị (Từ khóa: *{subject}*):\n" + "\n".join(f"- {link}" for link in videos)
            if mooc_links:
                response += f"\n\n### 🌐 Công cụ tìm khóa học Miễn phí (Từ khóa: *{subject}*):\n" + "\n".join(f"- {link}" for link in mooc_links)
                
        return response
    except Exception as e:
        return f"❌ Lỗi hệ thống: {str(e)}"