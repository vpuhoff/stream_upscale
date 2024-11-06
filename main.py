import cv2
import ffmpeg
import subprocess
import numpy as np

# Путь к waifu2x-ncnn-vulkan CLI
waifu2x_path = "/path/to/waifu2x-ncnn-vulkan"

# URL-адреса для входного и выходного RTSP-потоков
input_rtsp_url = "rtsp://input_stream_url"
output_rtsp_url = "rtsp://output_stream_url"

# Частота обработки кадров (например, обрабатываем каждый 5-й кадр)
process_every_n_frames = 5

def upscale_frame_with_waifu2x(frame):
    # Сохраняем временный файл для передачи в waifu2x
    cv2.imwrite("temp_frame.png", frame)
    
    # Запускаем waifu2x через командную строку
    subprocess.run([
        waifu2x_path, "-i", "temp_frame.png", "-o", "temp_frame_upscaled.png",
        "-s", "2"  # Коэффициент увеличения, 2 означает удвоение разрешения
    ])
    
    # Загружаем обработанное изображение
    upscaled_frame = cv2.imread("temp_frame_upscaled.png")
    return upscaled_frame

# Открываем RTSP-поток
cap = cv2.VideoCapture(input_rtsp_url)

# Получаем свойства исходного потока
fps = cap.get(cv2.CAP_PROP_FPS)
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

# Конфигурация вывода через FFmpeg
output_process = (
    ffmpeg
    .input('pipe:', format='rawvideo', pix_fmt='bgr24', s=f"{width*2}x{height*2}", r=fps)
    .output(output_rtsp_url, vcodec='libx264', pix_fmt='yuv420p', preset='fast', f='rtsp')
    .run_async(pipe_stdin=True)
)

frame_count = 0
last_upscaled_frame = None
try:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Пропускаем кадры, если не нужно их обрабатывать
        if frame_count % process_every_n_frames == 0:
            # Обрабатываем кадр с помощью waifu2x
            last_upscaled_frame = upscale_frame_with_waifu2x(frame)
        
        # Если кадр не обрабатывается, используем последний обработанный кадр
        output_frame = last_upscaled_frame if last_upscaled_frame is not None else frame

        # Отправляем кадр в FFmpeg для вывода в RTSP
        output_process.stdin.write(output_frame.tobytes())
        frame_count += 1

except KeyboardInterrupt:
    print("Streaming interrupted")

finally:
    cap.release()
    output_process.stdin.close()
    output_process.wait()
