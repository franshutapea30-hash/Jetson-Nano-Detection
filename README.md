# 🚦 Sistem Pengenalan Rambu Otomatis & Kendali Indikator LED Berbasis NVIDIA Jetson Nano

Repositori ini berisi implementasi sistem cerdas berbasis Edge Computing menggunakan **NVIDIA Jetson Nano** dan **Kamera CSI** untuk mengenali rambu lalu lintas (STOP, SLOW, GO) secara otomatis, menghitung nilai *confidence score*, serta mengendalikan 3 indikator lampu LED melalui pin GPIO.

---

## 1. Spesifikasi Hardware dan Software

### Hardware:
* **Komputer Embedded:** NVIDIA Jetson Nano Developer Kit (4GB RAM, Quad-Core ARM Cortex-A57).
* **Kamera:** Dual CSI Camera Module (Sensor Sony IMX219, 8 Megapixel).
* **Aktuator Output:**
  * 1x LED Merah (Indikator STOP)
  * 1x LED Kuning (Indikator SLOW)
  * 1x LED Hijau (Indikator GO)
* **Komponen Pendukung:**
  * 3x Resistor 220 Ohm
  * 1x Breadboard
  * 4x Kabel Jumper Female-to-Male
  * Casing Logam Waveshare Jetson Nano
* **Sumber Daya:** Adaptor DC 5V 4A (Barrel Jack).

### Software:
* **Operating System:** Linux Ubuntu 18.04 LTS (JetPack 4.6 / L4T R32.7).
* **Bahasa Pemrograman:** Python 3.6.9.
* **Computer Vision:** OpenCV (v3.2.0) & NumPy (v1.19.4).
* **Hardware Video Pipeline:** NVIDIA GStreamer (`nvarguscamerasrc` & `nvvidconv`).
* **GPIO Control:** Library `Jetson.GPIO`.

---

## 2. Cara Kerja Sistem

Sistem bekerja secara otomatis (*closed-loop real-time pipeline*) dengan alur:
[Kamera CSI] ──► [Frame Preprocessing] ──► [Color & Shape Detection] ──► [Decision Logic] ──► [GPIO Driver] ──► [3 LED] │ ▼ [Dashboard Monitor Overlay]


### Tahapan Algoritma:
1. **Camera Ingestion:** Kamera CSI mengambil video resolusi 1280x720 pada 30 FPS, dirotasi 180° (`flip-method=2`), dan diubah ke format BGRx resolusi 640x480 secara akselerasi hardware.
2. **Color Space Segmentation:** Frame dikonversi ke ruang warna **HSV (Hue, Saturation, Value)** untuk membedakan warna secara tahan terhadap perubahan cahaya:
   * **Merah (STOP):** $H \in [0, 12] \cup [160, 180]$
   * **Kuning (SLOW):** $H \in [14, 38]$
   * **Hijau (GO):** $H \in [35, 92]$
3. **Morphological Filtering:** Menggunakan operasi *Opening* kernel $5 \times 5$ untuk membersihkan bintik-bintik noise cahaya.
4. **Shape & Contour Analysis:**
   * Mengekstrak kontur objek dengan ukuran minimal $Area > 1200\text{ piksel}$.
   * Memvalidasi rasio aspek simetris ($0.5 \le \text{Aspect Ratio} \le 2.0$) untuk mencocokkan bentuk khas rambu lalu lintas.
5. **Confidence Score Calculation:**
   * Dihitung secara matematis berdasarkan tingkat kepadatan bentuk kontur (*solidity*).
6. **Decision Logic & GPIO Control:**
   * Jika $\text{Confidence} \ge 50\%$:
     * **STOP** $\rightarrow$ LED Merah Menyala (Pin 12 HIGH), lainnya mati.
     * **SLOW** $\rightarrow$ LED Kuning Menyala (Pin 16 HIGH), lainnya mati.
     * **GO** $\rightarrow$ LED Hijau Menyala (Pin 18 HIGH), lainnya mati.
   * Jika tidak ada rambu atau di bawah batas keyakinan:
     * **SAFE STATE** $\rightarrow$ Semua LED otomatis MATI demi keamanan.
7. **Display GUI:** Menampilkan video live, kotak pembatas (*bounding box*), label rambu, persentase akurasi, dan status output GPIO.

---

## 3. Wiring dan Sambungan Pin GPIO

Koneksi kabel jumper dari pin GPIO Jetson Nano (Mode BOARD) ke Breadboard:

| Jalur | Pin Jetson Nano | Label Casing Waveshare | Titik Breadboard | Fungsi |
| :--- | :---: | :---: | :---: | :--- |
| **Ground** | **Pin 6** | `GND` | Rel Negatif (`-`) | Jalur Ground Bersama |
| **LED Merah** | **Pin 12** | `D18` | Kolom `c6` (Anoda LED) | Sinyal Aktif STOP |
| **LED Kuning** | **Pin 16** | `D23` | Kolom `c11` (Anoda LED) | Sinyal Aktif SLOW |
| **LED Hijau** | **Pin 18** | `D24` | Kolom `c16` (Anoda LED) | Sinyal Aktif GO |

*Setiap katoda (kaki pendek) LED dihubungkan seri dengan resistor 220 Ohm menuju ke rel negatif Ground (`-`).*

---

## 4. Cara Instalasi dan Menjalankan Program

### Persiapan Dependensi di Jetson Nano:
```bash
sudo apt update
sudo apt install python3-pip python3-opencv -y
pip3 install numpy==1.19.4
echo 'export OPENBLAS_CORETYPE=ARMV8' >> ~/.bashrc
export OPENBLAS_CORETYPE=ARMV8

## Menjalankan Program Utama
# 1. Reset service kamera CSI
sudo systemctl restart nvargus-daemon

# 2. Atur sesi tampilan display monitor
export DISPLAY=:1
export XAUTHORITY=/run/user/1000/gdm/Xauthority

# 3. Jalankan program deteksi otomatis
python3 main_system.py
