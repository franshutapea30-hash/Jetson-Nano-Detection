import os
import random
import cv2
import numpy as np

# Konfigurasi Dataset
JUMLAH_PER_KELAS = 100
IMG_SIZE = 416

KELAS = {
    0: "STOP",
    1: "SLOW",
    2: "GO"
}

# Membuat struktur folder standar YOLO
for split in ["train", "val"]:
    os.makedirs(f"dataset/images/{split}", exist_ok=True)
    os.makedirs(f"dataset/labels/{split}", exist_ok=True)

def buat_rambu_dasar(nama):
    size = 200
    img = np.zeros((size, size, 4), dtype=np.uint8)  # RGBA transparan
    
    if nama == "STOP":
        pts = np.array([[60, 10], [140, 10], [190, 60], [190, 140], 
                        [140, 190], [60, 190], [10, 140], [10, 60]], np.int32)
        cv2.fillPoly(img, [pts], (0, 0, 220, 255))
        cv2.polylines(img, [pts], True, (255, 255, 255, 255), 4)
        cv2.putText(img, "STOP", (25, 115), cv2.FONT_HERSHEY_DUPLEX, 1.4, (255, 255, 255, 255), 4)

    elif nama == "SLOW":
        pts = np.array([[100, 10], [190, 100], [100, 190], [10, 100]], np.int32)
        cv2.fillPoly(img, [pts], (0, 215, 255, 255))
        cv2.polylines(img, [pts], True, (0, 0, 0, 255), 4)
        cv2.putText(img, "SLOW", (30, 112), cv2.FONT_HERSHEY_DUPLEX, 1.1, (0, 0, 0, 255), 3)

    elif nama == "GO":
        cv2.circle(img, (100, 100), 90, (0, 180, 0, 255), -1)
        cv2.circle(img, (100, 100), 90, (255, 255, 255, 255), 4)
        cv2.putText(img, "GO", (55, 118), cv2.FONT_HERSHEY_DUPLEX, 1.6, (255, 255, 255, 255), 4)

    return img

def buat_background_acak(w, h):
    tipe = random.choice(["solid", "gradient", "noise"])
    if tipe == "solid":
        warna = (random.randint(70, 210), random.randint(70, 210), random.randint(70, 210))
        bg = np.full((h, w, 3), warna, dtype=np.uint8)
    elif tipe == "gradient":
        c1 = np.array([random.randint(60, 180), random.randint(60, 180), random.randint(60, 180)])
        c2 = np.array([random.randint(100, 230), random.randint(100, 230), random.randint(100, 230)])
        grad = np.linspace(0, 1, h)[:, None, None]
        bg = (c1 * (1 - grad) + c2 * grad).astype(np.uint8)
        bg = np.repeat(bg, w, axis=1)
    else:
        bg = np.random.randint(70, 190, (h, w, 3), dtype=np.uint8)
        bg = cv2.GaussianBlur(bg, (25, 25), 0)
    return bg

print("Membuat dataset sintetis otomatis...")
for class_id, nama_kelas in KELAS.items():
    rambu_base = buat_rambu_dasar(nama_kelas)
    for i in range(JUMLAH_PER_KELAS):
        split = "train" if random.random() < 0.8 else "val"
        bg = buat_background_acak(IMG_SIZE, IMG_SIZE)
        
        # Variasi Ukuran (Skala acak)
        scale = random.uniform(0.35, 1.1)
        w_baru = int(rambu_base.shape[1] * scale)
        h_baru = int(rambu_base.shape[0] * scale)
        resized = cv2.resize(rambu_base, (w_baru, h_baru), interpolation=cv2.INTER_AREA)
        
        # Variasi Rotasi (-25 s/d +25 derajat)
        sudut = random.uniform(-25, 25)
        M = cv2.getRotationMatrix2D((w_baru // 2, h_baru // 2), sudut, 1.0)
        rotated = cv2.warpAffine(resized, M, (w_baru, h_baru), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
        
        # Posisi Acak
        max_x = max(0, IMG_SIZE - w_baru)
        max_y = max(0, IMG_SIZE - h_baru)
        pos_x = random.randint(0, max_x)
        pos_y = random.randint(0, max_y)
        
        # Penggabungan Alpha Blending
        alpha = rotated[:, :, 3] / 255.0
        for c in range(3):
            bg[pos_y:pos_y + h_baru, pos_x:pos_x + w_baru, c] = (
                alpha * rotated[:, :, c] + (1.0 - alpha) * bg[pos_y:pos_y + h_baru, pos_x:pos_x + w_baru, c]
            )
            
        # Variasi Pencahayaan
        kecerahan = random.uniform(0.7, 1.3)
        bg = np.clip(bg * kecerahan, 0, 255).astype(np.uint8)
        
        # Bounding Box YOLO (x_center y_center width height ternormalisasi 0-1)
        x_center = (pos_x + w_baru / 2.0) / IMG_SIZE
        y_center = (pos_y + h_baru / 2.0) / IMG_SIZE
        bb_w = w_baru / IMG_SIZE
        bb_h = h_baru / IMG_SIZE
        
        file_id = f"{nama_kelas}_{i:03d}"
        cv2.imwrite(f"dataset/images/{split}/{file_id}.jpg", bg)
        with open(f"dataset/labels/{split}/{file_id}.txt", "w") as f:
            f.write(f"{class_id} {x_center:.6f} {y_center:.6f} {bb_w:.6f} {bb_h:.6f}\n")

with open("dataset/data.yaml", "w") as f:
    f.write("train: ./images/train\nval: ./images/val\nnc: 3\nnames: ['STOP', 'SLOW', 'GO']\n")

print("Dataset sintetis format YOLO berhasil dibuat!")
