# Proyek Analisis Data: E-Commerce Public Dataset (Olist)

Analisis data penjualan e-commerce Olist (Brasil) periode **Januari 2017 - Agustus 2018**, mencakup tren penjualan, performa kategori produk, lama pengiriman, segmentasi pelanggan (RFM), analisis geospasial, dan binning lama pengiriman.

## Struktur Direktori
```
submission
├───dashboard
│   ├───main_data.csv
│   └───dashboard.py
├───data
│   └───*.csv  (dataset Olist)
├───notebook.ipynb
├───README.md
├───requirements.txt
└───url.txt
```

## Setup Environment

### Opsi 1: Anaconda
```
conda create --name main-ds python=3.11
conda activate main-ds
pip install -r requirements.txt
```

### Opsi 2: Shell/Terminal (virtual environment)
```
mkdir proyek_analisis_data
cd proyek_analisis_data
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
```

## Menjalankan Dashboard
Dari folder utama proyek (`submission`), jalankan:
```
python -m streamlit run dashboard/dashboard.py
```
Dashboard terbuka otomatis di `http://localhost:8501`.

## Fitur Dashboard
- **Filter sidebar:** rentang tanggal, state pelanggan, dan kategori produk
- **Metrik ringkas:** total order, revenue, pelanggan unik, rata-rata review, % order terlambat
- **Kategori Produk:** revenue tertinggi dan review di bawah rata-rata
- **Tren Bulanan:** order dan revenue per bulan, lonjakan dan penurunan MoM
- **Pengiriman per State:** lama kirim, % terlambat, dan review per state
- **Binning Lama Kirim:** kelompok interval lama pengiriman vs review
- **RFM Analysis:** segmentasi pelanggan (dihitung ulang sesuai filter) dan unduh CSV
- **Geospasial:** kepadatan pelanggan dan revenue/lama kirim per state

## Dashboard Online
https://olist-dashboard-grace-pinkkan-ladyna.streamlit.app/

(Tautan yang sama juga ada di `url.txt`.)