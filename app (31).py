import streamlit as st
import cv2
import numpy as np
import tempfile
import base64
import os
import requests
from PIL import Image
import io

st.set_page_config(
    page_title="SubClear",
    page_icon="✂️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
#MainMenu,footer,header{visibility:hidden;}
.block-container{padding:1rem 1rem 2rem;}
h1{text-align:center;background:linear-gradient(135deg,#c084fc,#818cf8);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  font-size:1.8rem;margin-bottom:0;}
.sub{text-align:center;color:#64748b;font-size:13px;margin-bottom:1.5rem;}
.stButton>button{width:100%;border-radius:10px;padding:10px;font-weight:600;}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1>✂️ SubClear</h1>", unsafe_allow_html=True)
st.markdown('<p class="sub">Xóa phụ đề video</p>', unsafe_allow_html=True)

def inpaint_frame(frame, mask):
    return cv2.inpaint(frame, mask, inpaintRadius=7, flags=cv2.INPAINT_TELEA)

def process_video(video_path, regions):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    tmp = tempfile.NamedTemporaryFile(suffix="_out.mp4", delete=False).name
    out = cv2.VideoWriter(tmp, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    mask = np.zeros((h, w), dtype=np.uint8)
    for (l, t, r, b) in regions:
        mask[max(0,int(h*t/100)):min(h,int(h*b/100)),
             max(0,int(w*l/100)):min(w,int(w*r/100))] = 255
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    bar = st.progress(0, text="Đang xử lý video...")
    i = 0
    while True:
        ret, frame = cap.read()
        if not ret: break
        out.write(inpaint_frame(frame, mask))
        i += 1
        if total > 0:
            bar.progress(min(i/total, 1.0), text=f"Đang xử lý... {int(i/total*100)}%")
    bar.progress(1.0, text="Hoàn thành!")
    cap.release(); out.release()
    return tmp

def get_frame(video_path):
    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, total // 2))
    ret, frame = cap.read()
    cap.release()
    if not ret: return None
    return Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

# ── Tab ────────────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["✏️ Thủ công", "🔗 URL / Make.com"])

with tab1:
    st.markdown("**Bước 1 — Tải video lên**")
    video_file = st.file_uploader("Chọn video", type=["mp4","mov","avi","mkv"],
                                   label_visibility="collapsed")

    if video_file:
        # Lưu video tạm
        tmp_in = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        tmp_in.write(video_file.read())
        tmp_in.close()

        # Hiện khung hình giữa
        frame = get_frame(tmp_in.name)
        if frame:
            st.markdown("**Bước 2 — Xem khung hình & chọn vùng chữ**")
            st.image(frame, use_column_width=True,
                     caption="Nhìn ảnh để xác định vùng chữ cần xóa")

            st.markdown("**Bước 3 — Kéo thanh để khoanh vùng chữ**")
            st.markdown("Nhìn ảnh trên → kéo thanh cho khung bao đúng vùng chữ:")

            col1, col2 = st.columns(2)
            with col1:
                top   = st.slider("Từ trên (%)",  0, 95, 70, 1)
                left  = st.slider("Từ trái (%)",  0, 95,  5, 1)
            with col2:
                bot   = st.slider("Từ dưới (%)", 5, 100, 88, 1)
                right = st.slider("Từ phải (%)", 5, 100, 95, 1)

            # Vẽ hộp lên ảnh để preview
            if top < bot and left < right:
                import numpy as np
                arr = np.array(frame)
                h_img, w_img = arr.shape[:2]
                y1 = int(h_img * top  / 100)
                y2 = int(h_img * bot  / 100)
                x1 = int(w_img * left / 100)
                x2 = int(w_img * right/ 100)
                preview = arr.copy()
                cv2.rectangle(preview, (x1,y1), (x2,y2), (232,121,249), 3)
                # Tô mờ vùng chọn
                overlay = preview.copy()
                cv2.rectangle(overlay, (x1,y1), (x2,y2), (232,121,249), -1)
                preview = cv2.addWeighted(overlay, 0.2, preview, 0.8, 0)
                st.image(preview, use_column_width=True,
                         caption="Vùng hồng = vùng sẽ bị xóa chữ")

            st.markdown("**Bước 4 — Xóa phụ đề**")
            if st.button("🗑️ Xóa phụ đề", type="primary", use_container_width=True):
                if top >= bot:
                    st.error("Từ trên phải nhỏ hơn Từ dưới!")
                elif left >= right:
                    st.error("Từ trái phải nhỏ hơn Từ phải!")
                else:
                    with st.spinner("Đang xử lý..."):
                        out_path = process_video(tmp_in.name, [(left,top,right,bot)])
                    st.success("✅ Xóa thành công!")
                    with open(out_path, "rb") as f:
                        st.download_button(
                            "⬇️ Tải video đã xóa về",
                            data=f.read(),
                            file_name="subclear_output.mp4",
                            mime="video/mp4",
                            use_container_width=True,
                        )
                    # Hiện preview video
                    st.video(out_path)

with tab2:
    st.markdown("Dán link video từ Make.com hoặc bất kỳ URL nào.")
    url = st.text_input("URL video", placeholder="https://...")
    col1, col2 = st.columns(2)
    with col1:
        top2  = st.slider("Từ trên (%)",  0, 95, 70, 1, key="t2")
        left2 = st.slider("Từ trái (%)",  0, 95,  5, 1, key="l2")
    with col2:
        bot2  = st.slider("Từ dưới (%)", 5, 100, 88, 1, key="b2")
        right2= st.slider("Từ phải (%)", 5, 100, 95, 1, key="r2")

    if st.button("▶️ Tải & Xóa phụ đề", type="primary", use_container_width=True):
        if not url:
            st.error("Nhập URL trước!")
        else:
            with st.spinner("Đang tải video..."):
                try:
                    r = requests.get(url, timeout=60)
                    tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
                    tmp.write(r.content); tmp.close()
                    out_path = process_video(tmp.name, [(left2,top2,right2,bot2)])
                    st.success("✅ Xóa thành công!")
                    with open(out_path, "rb") as f:
                        st.download_button("⬇️ Tải video về", f.read(),
                            "output.mp4", "video/mp4", use_container_width=True)
                    st.video(out_path)
                except Exception as e:
                    st.error(f"Lỗi: {e}")
