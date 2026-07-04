# 🎮 Panduan Gesture & Kontrol Sistem v3.0

Dokumen ini menjelaskan spesifikasi teknis dari model pengenalan gesture (*hand tracking*), cara kerja peredaman gangguan koordinat (*coordinate smoothing*), klasifikasi geometri tangan, serta panduan interaktif lengkap untuk mengontrol audio dan visualizer.

---

## 🔬 Mekanisme Pelacakan & Peredaman Jitter

Sistem menggunakan **Google MediaPipe Hand Landmarker Tasks API** untuk melacak 21 titik koordinat (*landmarks*) 3D tangan. Untuk mencegah getaran halus (*jitter*) yang disebabkan oleh derau kamera atau pergerakan sensorik kecil, koordinat piksel dihaluskan menggunakan **Exponential Moving Average (EMA)** sebelum diterjemahkan oleh modul klasifikasi:

$$S_t = \alpha \cdot Y_t + (1 - \alpha) \cdot S_{t-1}$$

*   $Y_t$ adalah koordinat mentah (*raw*) piksel pada frame saat ini.
*   $S_{t-1}$ adalah koordinat yang telah dihaluskan pada frame sebelumnya.
*   $\alpha$ adalah faktor kelembutan (*smoothing alpha*), yang diatur sebesar $0.45$. Nilai ini memberikan keseimbangan optimal antara latensi responsif (tanpa delay) dan kestabilan visual.

---

## ⚙️ Logika Deteksi Keterbukaan Jari

Modul [gestures.py](file:///d:/handtracking/gestures.py) menghitung status keterbukaan jari secara mandiri menggunakan kombinasi jarak euklides dan proyeksi spasial:

1.  **Ibu Jari (Thumb):**
    *   Dihitung berdasarkan perbandingan jarak dari ujung ibu jari (landmark 4) ke titik tengah telapak tangan (rata-rata koordinat landmark 0, 5, 9, 13, 17) dibandingkan dengan jarak sendi IP ibu jari (landmark 3) ke pusat telapak.
    *   Jika jarak ujung jari $>$ 1.1 kali jarak sendi IP, ibu jari dianggap **terbuka** (extended).
2.  **Jari Telunjuk, Tengah, Manis, Kelingking:**
    *   Menggunakan pendekatan jarak relatif terhadap pergelangan tangan (landmark 0) dan buku jari MCP (landmark 5, 9, 13, 17).
    *   Jari dinyatakan **terbuka** jika dan hanya jika memenuhi dua kondisi:
        *   Jarak ujung jari (*Tip*) ke pergelangan tangan $>$ 0.92 kali jarak sendi PIP ke pergelangan tangan.
        *   Jarak ujung jari (*Tip*) ke buku jari MCP $>$ 0.8 kali jarak sendi PIP ke buku jari MCP.
    *   Pendekatan ini meminimalkan kesalahan deteksi akibat rotasi sudut tangan (*scale & rotation invariant*).

---

## 📋 Daftar Klasifikasi Gesture Satu Tangan

Sistem mendefinisikan beberapa aksi kontinu (*continuous*) dan aksi sekali picu (*toggle/one-shot*) berdasarkan pola kombinasi jari:

### 1. 🤏 PINCH (Cubit Telunjuk-Jempol)
*   **Logika:** Jarak antara ujung jempol (4) dan ujung telunjuk (8) $<$ 30% dari ukuran lebar telapak tangan (jarak landmark 0 ke 9).
*   **Fungsi:** Mengatur volume master. Ketinggian tangan (koordinat Y ujung telunjuk) dipetakan secara terbalik terhadap tinggi frame:
    $$\text{Volume Ratio} = 1.0 - \frac{Y_{\text{cursor}}}{H_{\text{frame}}}$$
*   **Mode:** Kontinu.
*   **Umpan Balik Visual:** Spark partikel neon keluar dari titik cubitan.

### 2. ✊ FIST (Mengepal)
*   **Logika:** Seluruh jari (telunjuk, tengah, manis, kelingking) terdeteksi dalam kondisi tertutup (tidak terbuka).
*   **Fungsi:** Mengaktifkan low-pass filter (*muffled*) pada lagu, menyaring suara frekuensi tinggi sehingga terdengar seperti di dalam air.
*   **Mode:** Kontinu (aktif selama tangan mengepal).
*   **Umpan Balik Visual:** VHS digital noise dan efek guncangan layar berat (*heavy screen shake*).

### 3. ✌️ VICTORY (Dua Jari Terbuka)
*   **Logika:** Jari telunjuk dan tengah terbuka; jempol, manis, dan kelingking tertutup.
*   **Fungsi:** Mengaktifkan filter suara retro Lo-Fi (Bitcrusher/Downsampling).
*   **Mode:** Sekali picu (*Toggle*).
*   **Umpan Balik Visual:** Muncul glitch visual horizontal ringan selama transisi.

### 4. 🤘 ROCK (Metal Sign)
*   **Logika:** Jari telunjuk dan kelingking terbuka; jempol, tengah, dan manis tertutup.
*   **Fungsi:** Memicu efek kilatan cahaya strobe (*strobe flash*) selama 1.5 detik. Sangat cocok digunakan untuk mengiringi ketukan bass (*beat drops*).
*   **Mode:** Sekali picu (*One-shot*).
*   **Umpan Balik Visual:** Sparkle bursts partikel bintang putih memancar dari tangan.

### 5. ☝️ POINT_UP (Menunjuk ke Atas)
*   **Logika:** Hanya jari telunjuk yang terbuka; semua jari lainnya tertutup.
*   **Fungsi:** Berpindah ke tipe visualizer neon berikutnya (Circle ➔ Wave ➔ Bar ➔ Concert).
*   **Mode:** Sekali picu (*Toggle*).
*   **Umpan Balik Visual:** Teks melayang menampilkan mode visualizer yang aktif.

### 6. 🖐️ OPEN_PALM (Telapak Terbuka)
*   **Logika:** Keempat jari utama (telunjuk, tengah, manis, kelingking) terbuka penuh secara bersamaan.
*   **Fungsi:** Menghilangkan filter audio (kembali ke suara normal), mereset volume ke 100%, dan mereset equalizer default.
*   **Mode:** Kontinu.
*   **Umpan Balik Visual:** Menghentikan segala bentuk guncangan dan distorsi layar.

### 7. 👍 THUMB_UP (Jempol ke Atas)
*   **Logika:** Hanya ibu jari terbuka dengan posisi koordinat Y ujung jempol (4) berada di atas sendi IP (3). Jari lainnya mengepal.
*   **Fungsi:**
    *   *Kondisi Equalizer Terbuka:* Bergeser ke pemilihan band equalizer berikutnya (BASS ➔ MID ➔ TREBLE).
    *   *Kondisi Normal:* Menampilkan notifikasi visual "THUMB UP!".
*   **Mode:** Sekali picu (*Toggle*).

### 8. 👎 THUMB_DOWN (Jempol ke Bawah)
*   **Logika:** Hanya ibu jari terbuka dengan posisi koordinat Y ujung jempol (4) berada di bawah sendi IP (3). Jari lainnya mengepal.
*   **Fungsi:**
    *   *Kondisi Equalizer Terbuka:* Mengembalikan seluruh penguatan gain band (Bass, Mid, Treble) kembali ke 100% (1.0).
    *   *Kondisi Normal:* Menampilkan notifikasi visual "THUMB DOWN!".
*   **Mode:** Sekali picu (*Toggle*).

---

## 🤝 Daftar Klasifikasi Gesture Dua Tangan

### 1. 🫶 HEART (Bentuk Hati)
*   **Logika:** Jarak antara kedua ujung jempol $<$ 50% rata-rata lebar telapak tangan, DAN jarak kedua ujung telunjuk $<$ 50% rata-rata lebar telapak tangan.
*   **Fungsi:** Mengaktifkan *Love Mode* secara bolak-balik (*Toggle*). Tema visualizer berubah menjadi pink gelap, lirik lagu muncul, dan partikel hati melayang mengikuti getaran audio.

### 2. 🤟🤟 THREE_THREE (3+3 Jari Tengah)
*   **Logika:** Jari telunjuk, tengah, dan manis terbuka pada kedua tangan; sementara jempol dan kelingking dalam kondisi tertutup rapat.
*   **Fungsi:** Membuka dan menutup panel menu *Virtual Equalizer Overlay*.
*   **Mode:** Sekali picu (*Toggle*).

### 3. 🖐️🖐️ ALL_OPEN (Sepuluh Jari Terbuka)
*   **Logika:** Minimal 4 jari terbuka pada kedua tangan secara bersamaan.
*   **Fungsi:** Mengaktifkan *Concert Mode* secara bolak-balik (*Toggle*).
*   **Umpan Balik Visual:** Memicu lampu sorot (*spotlight*), laser garis, hujan konfeti, dan teks lirik berpendar (*glow text*).

---

## 🎛️ Panduan Interaktif Virtual Equalizer

Sistem menyediakan antarmuka pencampuran frekuensi audio yang sepenuhnya dikontrol secara nirkabel dengan gerakan tangan Anda.

```
       [ VIRTUAL EQUALIZER ]
  > BASS   ████████░░░░░░  100%
    MID    ████████░░░░░░  100%
    TREBLE ████████░░░░░░  100%
             
           (O)---[ DIAL ] -> Putar pergelangan
```

### Langkah Pengoperasian Equalizer:
1.  **Buka Equalizer:** Bentuk gesture **THREE_THREE** dengan kedua tangan Anda. Menu hologram transparan akan muncul di bagian tengah layar.
2.  **Pilih Band Frekuensi:** Gunakan gesture **THUMB_UP** untuk memilih band yang ingin diubah. Panah penunjuk `>` akan bergeser dari `BASS` ➔ `MID` ➔ `TREBLE`.
3.  **Putar Dial Gain:** 
    *   Sistem membaca sudut inklinasi telapak tangan utama berdasarkan garis koordinat dari pergelangan tangan (landmark 0) ke pangkal jari tengah (landmark 9).
    *   Putar pergelangan tangan Anda searah atau berlawanan jarum jam. Delta rotasi sudut akan dihitung secara diferensial dan ditambahkan langsung ke gain band yang sedang aktif (rentang penguatan dibatasi dari **0% (hening)** hingga **200% (boost ganda)**).
4.  **Reset Default:** Jika penguatan audio pecah atau tidak seimbang, lakukan gesture **THUMB_DOWN** untuk mereset seluruh band kembali ke nilai dasar 100%.
5.  **Tutup Menu:** Buat kembali gesture **THREE_THREE** untuk menyimpan setelan dan menyembunyikan panel equalizer.

---

## 💡 Tips Deteksi dan Kinerja Optimal

1.  **Pencahayaan yang Stabil:** Hindari membelakangi jendela terang atau lampu pijar langsung (*backlight*). Jaringan saraf MediaPipe membutuhkan kontras bayangan yang jelas untuk membedakan ruas jari.
2.  **Jarak Operasional:** Posisikan diri Anda sekitar **50cm hingga 1 meter** dari lensa webcam. Pastikan seluruh bagian pergelangan tangan hingga ujung kelingking tidak terpotong tepi layar.
3.  **Gunakan Dua Tangan Secara Jelas:** Untuk gesture ganda seperti `THREE_THREE` atau `ALL_OPEN`, pastikan kedua tangan diangkat secara bersamaan pada ketinggian yang serupa agar kamera tidak kehilangan fokus deteksi salah satu tangan.
4.  **Bermain Bersama Ketukan:** Gunakan gesture **ROCK (🤘)** persis saat lagu mencapai klimaks untuk memadukan lampu strobo dengan efek laser dari **Concert Mode (🖐️🖐️)**.
