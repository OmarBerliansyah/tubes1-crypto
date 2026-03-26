import cv2 

def load_video(path):
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        return None, 0, 0, 0
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    frames = []
    while True:
        ret, frame = cap.read()
        if not ret: 
            break
        frames.append(frame)
    cap.release()
    return frames, w, h, fps

def save_video(frames, w, h, fps, path):
    out = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*'FFV1'), fps, (w, h))
    for f in frames: out.write(f)
    out.release()