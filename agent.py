import json
import os
import urllib.parse
import logging
from groq import Groq
from prompts import get_system_prompt
from googleapiclient.discovery import build

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_groq_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY chưa được đặt.")
    return Groq(api_key=api_key)

def load_knowledge_base():
    with open('resources.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def search_youtube(query, level="beginner", max_results=3):
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key: return None
    try:
        level_str = "beginner" if not level else level.lower()
        search_query = f"{query} {level_str} course tutorial"
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
        logger.error(f"Lỗi YouTube: {e}")
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

def detect_subject_and_level(conversation_context):
    """
    Gộp sub-agent nhận diện môn học và trình độ.
    Trả về tuple (subject, level)
    """
    try:
        client = get_groq_client()
        system_prompt = """
Bạn là trợ lý AI chuyên phân tích ngữ cảnh hội thoại.
Nhiệm vụ: Từ đoạn hội thoại dưới đây, hãy trích xuất:
1. Môn học mà người dùng muốn học (chỉ một cụm từ tiếng Anh ngắn gọn, ví dụ: 'Machine Learning', 'Python', 'Web Development').
2. Trình độ của người dùng (Beginner, Intermediate, Advanced) dựa trên những gì họ nói.

Trả về kết quả dưới dạng:
Subject: <môn học>
Level: <trình độ>

Nếu không thể xác định, hãy để là "Unknown".
"""
        user_msg = f"Đoạn hội thoại:\n{conversation_context}\n\nOutput:"
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg}
            ],
            temperature=0.0,
            max_tokens=30
        )
        response_text = completion.choices[0].message.content.strip()
        # parse
        lines = response_text.split('\n')
        subject = None
        level = None
        for line in lines:
            if line.lower().startswith("subject:"):
                subject = line.split(":", 1)[1].strip()
            elif line.lower().startswith("level:"):
                level = line.split(":", 1)[1].strip()
        # Xác thực
        if level not in ["Beginner", "Intermediate", "Advanced"]:
            level = None
        if subject == "Unknown" or not subject or len(subject) > 50:
            subject = None
        return subject, level
    except Exception as e:
        logger.error(f"Lỗi detect subject/level: {e}")
        return None, None

def get_resources_for_subject(subject, kb):
    """Lọc KB theo subject, trả về dictionary"""
    if not subject:
        return {}
    subject_lower = subject.lower()
    keywords = subject_lower.split()
    filtered = {}
    for key, value in kb.items():
        key_lower = key.replace("_", " ").lower()
        # Nếu bất kỳ từ khóa nào xuất hiện trong key hoặc ngược lại
        if any(kw in key_lower for kw in keywords) or any(word in subject_lower for word in key_lower.split()):
            filtered[key] = value
    return filtered

def generate_learning_path(user_input, chat_history=[]):
    try:
        recent_history = chat_history[-4:] 
        history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in recent_history])
        conversation_context = f"{history_str}\nuser: {user_input}"
        
        # Detect subject & level
        subject, level = detect_subject_and_level(conversation_context)
        
        kb = load_knowledge_base()
        filtered_kb = get_resources_for_subject(subject, kb) if subject else {}
        
        # Nếu không có tài nguyên nào và đã có subject -> thông báo
        if not filtered_kb and subject:
            sample_keys = list(kb.keys())[:5]
            sample_list = ", ".join([f"**{k.replace('_', ' ').title()}**" for k in sample_keys])
            return f"Xin lỗi, tôi chưa có tài liệu cho môn học **{subject}**. Bạn có thể thử các môn sau: {sample_list} hoặc hỏi một môn khác."
        
        # Nếu không có subject và không có level -> yêu cầu thông tin thêm
        if not subject and not level:
            return "Xin chào! Tôi là EduGuide. Bạn muốn học môn gì và ở trình độ nào (Beginner, Intermediate, Advanced)? Hãy cho tôi biết để tôi có thể tư vấn chính xác nhé!"
        
        # Nếu có subject nhưng thiếu level -> hỏi
        if subject and not level:
            return f"Tôi hiểu bạn muốn học về **{subject}**. Bạn đang ở trình độ nào: Beginner, Intermediate hay Advanced? Hãy cho tôi biết để tôi gợi ý lộ trình phù hợp."
        
        # Đã có đủ thông tin -> tạo prompt
        kb_string = json.dumps(filtered_kb, indent=2, ensure_ascii=False)
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
            max_tokens=2048
        )
        response = completion.choices[0].message.content
        
        # Thêm YouTube và MOOCs
        if subject and level:
            videos = search_youtube(subject, level)
            mooc_links = search_free_course(subject, level)
            if videos:
                response += f"\n\n---\n### ▶️ Kênh YouTube Khuyến nghị (Từ khóa: *{subject}*, trình độ: *{level}*):\n" + "\n".join(f"- {link}" for link in videos)
            if mooc_links:
                response += f"\n\n### 🌐 Công cụ tìm khóa học Miễn phí (Từ khóa: *{subject}*, trình độ: *{level}*):\n" + "\n".join(f"- {link}" for link in mooc_links)
        
        return response
        
    except Exception as e:
        logger.error(f"Lỗi hệ thống: {e}", exc_info=True)
        return f"❌ Lỗi hệ thống: {str(e)}"