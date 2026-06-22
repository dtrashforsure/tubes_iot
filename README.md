# Sistem Monitoring Suhu Berbasis IoT Cerdas

**Tugas Besar Mata Kuliah IoT Cerdas — S2 Teknik Elektro, Universitas Telkom**

Sistem monitoring suhu *end-to-end* menggunakan ESP32, sensor DS18B20, platform ThingSpeak, dan model AI *Random Forest Regressor* untuk prediksi suhu 1 menit ke depan.

---

## Arsitektur Sistem

```
DS18B20 → ESP32 (Wokwi) → ThingSpeak ← Python AI (Random Forest)
                                ↓
                          Dashboard ThingSpeak
                     (Field 1: Aktual | Field 2: Prediksi | Field 3: Status)
```

---

## Struktur Repositori

```
TUBES_IOT/
├── vscode/
│   ├── kodingantubeswokwi.c   # Firmware ESP32 (Arduino/C)
│   └── randomorrest.py        # Program Python AI Random Forest
└── buku_latex/
    ├── DECO_buku_iot_cerdas.tex  # File utama LaTeX
    ├── bab/                      # Bab 1–5
    ├── bagian_awal/              # Cover, abstrak, abstract
    ├── lampiran/                 # Source code & singkatan
    ├── images/                   # Gambar pendukung
    ├── references.bib            # Daftar pustaka
    └── Makefile                  # Build PDF: make pdf
```

---

## Cara Menjalankan

### 1. Firmware ESP32 (Wokwi)
- Buka [wokwi.com](https://wokwi.com) dan buat proyek ESP32
- Salin isi `vscode/kodingantubeswokwi.c`
- Isi `writeAPIKey` dengan Write API Key ThingSpeak Anda
- Jalankan simulasi

### 2. Program Python AI
```bash
pip install requests numpy pandas scikit-learn
```
- Isi `WRITE_API_KEY` di `vscode/randomorrest.py` dengan Write API Key Anda
- Jalankan:
```bash
python vscode/randomorrest.py
```

### 3. Kompilasi Laporan LaTeX
```bash
cd buku_latex
make pdf
```

---

## Konfigurasi ThingSpeak

| Field   | Nama                    | Sumber         |
|---------|-------------------------|----------------|
| Field 1 | Temperature             | ESP32 / Wokwi  |
| Field 2 | Predicted Temperature 1 Min | Python AI  |
| Field 3 | AI Status Code          | Python AI      |

Status: `0` = Dingin (<25°C) | `1` = Normal (25–30°C) | `2` = Panas (>30°C)

---

## Parameter Model AI

| Parameter         | Nilai                        |
|-------------------|------------------------------|
| Algoritma         | Random Forest Regressor      |
| n_estimators      | 100                          |
| max_depth         | 6                            |
| Fitur input       | 7 (lag, delta, moving avg)   |
| Target prediksi   | 1 menit ke depan (4 langkah) |
| Split data        | 80% train / 20% test         |
