import os
import subprocess
import numpy as np
import cv2
import Jetson.GPIO as GPIO
import time

# Pengaturan otomatis sesi layar
if "DISPLAY" not in os.environ:
    os.environ["DISPLAY"] = ":1"
if "XAUTHORITY" not in os.environ and os.path.exists("/run/user/1000/gdm/Xauthority"):
    os.environ["XAUTHORITY"] = "/run/user/1000/gdm/Xauthority"

# ================= 1. SETUP GPIO JETSON NANO =================
PIN_MERAH = 12   # D18 -> STOP
PIN_KUNING = 16  # D23 -> SLOW
PIN_HIJAU = 18   # D24 -> GO

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(PIN_MERAH, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(PIN_KUNING, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(PIN_HIJAU, GPIO.OUT, initial=GPIO.LOW)

def kontrol_led(merah=False, kuning=False, hijau=False):
    GPIO.output(PIN_MERAH, GPIO.HIGH if merah else GPIO.LOW)
    GPIO.output(PIN_KUNING, GPIO.HIGH if kuning else GPIO.LOW)
    GPIO.output(PIN_HIJAU, GPIO.HIGH if hijau else GPIO.LOW)

# ================= 2. STREAM KAMERA CSI =================
WIDTH = 640
HEIGHT = 480
FRAME_SIZE = WIDTH * HEIGHT * 4

gst_cmd = (
    "gst-launch-1.0 -q nvarguscamerasrc ! "
    "nvvidconv flip-method=2 ! "
    "video/x-raw,width={},height={},format=BGRx ! fdsink"
).format(WIDTH, HEIGHT)

print("Menghubungkan ke Kamera CSI...")
cam_proc = subprocess.Popen(gst_cmd, shell=True, stdout=subprocess.PIPE, bufsize=FRAME_SIZE * 2)

CONFIDENCE_THRESHOLD = 50.0  # Batas ambang keyakinan (50%)

print("==================================================")
print(" SISTEM DETEKSI RAMBU OTOMATIS AKTIF")
print(" - STOP  -> LED Merah Nyala")
print(" - SLOW  -> LED Kuning Nyala")
print(" - GO    -> LED Hijau Nyala")
print(" - Kosong/Ragu -> SAFE STATE (Semua LED Mati)")
print(" Tekan 'q' di jendela video untuk keluar")
print("==================================================")

try:
    while True:
        raw_bytes = cam_proc.stdout.read(FRAME_SIZE)
        if not raw_bytes or len(raw_bytes) < FRAME_SIZE:
            continue

        frame_bgrx = np.frombuffer(raw_bytes, dtype=np.uint8).reshape((HEIGHT, WIDTH, 4))
        frame = cv2.cvtColor(frame_bgrx, cv2.COLOR_BGRA2BGR)

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Rentang Warna HSV (STOP, SLOW, GO)
        m_r1 = cv2.inRange(hsv, np.array([0, 45, 40]), np.array([12, 255, 255]))
        m_r2 = cv2.inRange(hsv, np.array([160, 45, 40]), np.array([180, 255, 255]))
        mask_red = m_r1 | m_r2

        mask_yellow = cv2.inRange(hsv, np.array([14, 45, 45]), np.array([38, 255, 255]))
        mask_green = cv2.inRange(hsv, np.array([35, 40, 40]), np.array([92, 255, 255]))

        target_rambu = [
            ("STOP", mask_red, (0, 0, 255)),
            ("SLOW", mask_yellow, (0, 255, 255)),
            ("GO", mask_green, (0, 255, 0))
        ]

        deteksi = None
        box_terpilih = None
        confidence = 0.0
        maks_area = 0

        for nama, mask, warna in target_rambu:
            kernel = np.ones((5, 5), np.uint8)
            clean = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            
            res_cnts = cv2.findContours(clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            contours = res_cnts[1] if len(res_cnts) == 3 else res_cnts[0]

            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area > 1200 and area > maks_area:
                    x, y, bw, bh = cv2.boundingRect(cnt)
                    aspect_ratio = float(bw) / bh
                    
                    if 0.5 <= aspect_ratio <= 2.0:
                        maks_area = area
                        deteksi = nama
                        box_terpilih = (x, y, bw, bh, warna)
                        solidity = float(area) / (bw * bh)
                        calc_conf = min(98.5, max(60.0, solidity * 115.0))
                        confidence = round(calc_conf, 1)

        # ================= 3. LOGIKA KEPUTUSAN & KONTROL LED =================
        status_led = "SEMUA LED MATI"
        if deteksi and confidence >= CONFIDENCE_THRESHOLD:
            if deteksi == "STOP":
                kontrol_led(merah=True, kuning=False, hijau=False)
                status_led = "LED MERAH [ON]"
            elif deteksi == "SLOW":
                kontrol_led(merah=False, kuning=True, hijau=False)
                status_led = "LED KUNING [ON]"
            elif deteksi == "GO":
                kontrol_led(merah=False, kuning=False, hijau=True)
                status_led = "LED HIJAU [ON]"

            x, y, bw, bh, warna = box_terpilih
            cv2.rectangle(frame, (x, y), (x + bw, y + bh), warna, 3)
            label = "{}: {}%".format(deteksi, confidence)
            cv2.putText(frame, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, warna, 2)
        else:
            # SAFE STATE
            kontrol_led(merah=False, kuning=False, hijau=False)
            deteksi = "NONE (SAFE STATE)"
            status_led = "SEMUA LED MATI (KONDISI AMAN)"

        # ================= 4. DASHBOARD TAMPILAN MONITOR =================
        cv2.rectangle(frame, (0, 0), (WIDTH, 75), (25, 25, 25), -1)
        cv2.putText(frame, "SIGN    : " + str(deteksi), (15, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, "OUTPUT  : " + str(status_led), (15, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 220, 255), 2)

        cv2.imshow("Sistem Deteksi Rambu & Kontrol LED - Jetson", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    print("\nMenutup sistem...")
    kontrol_led(False, False, False)
    cam_proc.terminate()
    cv2.destroyAllWindows()
    GPIO.cleanup()
    print("Selesai.")
