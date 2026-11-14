"""
Dashboard Analisis E-Commerce Public Dataset (Olist, Brasil)
Periode: Januari 2017 - Agustus 2018

Jalankan dari root folder proyek:
    streamlit run dashboard/dashboard.py
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import streamlit as st
from matplotlib.ticker import FuncFormatter

# ------------------------------------------------------------------ konfigurasi
st.set_page_config(page_title="Dashboard E-Commerce Olist", page_icon="🛒", layout="wide")

sns.set_theme(style="whitegrid")
plt.rcParams.update({"axes.titleweight": "bold", "axes.titlesize": 13, "figure.dpi": 100})

HIGHLIGHT = "#1f5fa8"  # sorotan utama
MUTED = "#c4c9d0"      # pembanding netral
ALERT = "#c0392b"      # hal negatif / peringatan

DATA_PATH = Path(__file__).parent / "main_data.csv"


def fmt_real(x, _=None):
    return f"R$ {x / 1e6:,.1f} jt"


def fmt_num(x):
    """Format angka gaya Indonesia: titik ribuan, koma desimal."""
    return f"{x:,.0f}".replace(",", ".")


def fmt_dec(x, n=2):
    return f"{x:,.{n}f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ------------------------------------------------------------------ data
@st.cache_data(show_spinner="Memuat data...")
def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH, parse_dates=["order_purchase_timestamp"])
    df["category"] = df["category"].fillna("unknown")
    return df


def hitung_rfm(df: pd.DataFrame) -> pd.DataFrame:
    """RFM: R & M pakai kuartil, F pakai aturan bisnis (1, 2, >=3 order)."""
    snapshot = df.order_purchase_timestamp.max() + pd.Timedelta(days=1)
    rfm = (df.groupby("customer_unique_id")
             .agg(terakhir_beli=("order_purchase_timestamp", "max"),
                  frequency=("order_id", "nunique"),
                  monetary=("price", "sum"))
             .reset_index())
    rfm["recency"] = (snapshot - rfm.terakhir_beli).dt.days
    rfm["R"] = pd.qcut(rfm.recency.rank(method="first"), 4, labels=[4, 3, 2, 1]).astype(int)
    rfm["M"] = pd.qcut(rfm.monetary.rank(method="first"), 4, labels=[1, 2, 3, 4]).astype(int)
    rfm["F"] = np.select([rfm.frequency >= 3, rfm.frequency == 2], [3, 2], default=1)
    rfm["segmen"] = np.select(
        [(rfm.F >= 2) & (rfm.R >= 3) & (rfm.M >= 3),
         (rfm.F >= 2),
         (rfm.R >= 3) & (rfm.M >= 3),
         (rfm.R >= 3),
         (rfm.M >= 3)],
        ["Champions", "Repeat Buyers", "Recent Big Spenders", "Recent One-time", "Lapsed Big Spenders"],
        default="Lapsed One-time")
    return rfm


URUTAN_SEGMEN = ["Champions", "Repeat Buyers", "Recent Big Spenders",
                 "Recent One-time", "Lapsed Big Spenders", "Lapsed One-time"]

# ------------------------------------------------------------------ muat & filter
main = load_data()

st.sidebar.title("🛒 Filter Data")
tgl_min = main.order_purchase_timestamp.min().date()
tgl_max = main.order_purchase_timestamp.max().date()
rentang = st.sidebar.date_input("Rentang tanggal order", value=(tgl_min, tgl_max),
                                min_value=tgl_min, max_value=tgl_max)
if isinstance(rentang, (tuple, list)) and len(rentang) == 2:
    tgl_awal, tgl_akhir = rentang
else:  # pengguna baru memilih satu tanggal
    tgl_awal = tgl_akhir = rentang[0] if isinstance(rentang, (tuple, list)) else rentang

semua_state = sorted(main.customer_state.dropna().unique())
state_pilih = st.sidebar.multiselect("State pelanggan", semua_state, default=semua_state)

kat_semua = sorted(main.category.unique())
kat_pilih = st.sidebar.multiselect("Kategori produk", kat_semua, default=[],
                                   help="Kosongkan untuk memilih semua kategori.")
st.sidebar.caption("Nilai uang dalam Real Brasil (R$). Data: Olist, order berstatus *delivered*.")

df = main[
    (main.order_purchase_timestamp.dt.date >= tgl_awal)
    & (main.order_purchase_timestamp.dt.date <= tgl_akhir)
    & (main.customer_state.isin(state_pilih))
]
if kat_pilih:
    df = df[df.category.isin(kat_pilih)]

st.title("Dashboard Analisis E-Commerce Olist")
st.caption(f"Periode: {tgl_awal:%d %b %Y} - {tgl_akhir:%d %b %Y} | Brasil, pesanan terkirim")

if df.empty:
    st.warning("Tidak ada data untuk filter yang dipilih. Ubah rentang tanggal, state, atau kategori.")
    st.stop()

order_lvl = df.drop_duplicates("order_id")

# ------------------------------------------------------------------ metrik ringkas
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Order", fmt_num(order_lvl.order_id.nunique()))
c2.metric("Total Revenue", f"R$ {fmt_dec(df.price.sum() / 1e6)} jt")
c3.metric("Pelanggan Unik", fmt_num(df.customer_unique_id.nunique()))
c4.metric("Rata-rata Review", fmt_dec(order_lvl.review_score.mean()))
c5.metric("Order Terlambat", f"{fmt_dec(order_lvl.is_late.mean() * 100, 1)}%")

tab_kat, tab_tren, tab_state, tab_bin, tab_rfm, tab_geo = st.tabs(
    ["📦 Kategori Produk", "📈 Tren Bulanan", "🚚 Pengiriman per State",
     "⏱️ Binning Lama Kirim", "👥 RFM Analysis", "🗺️ Geospasial"])

# ------------------------------------------------------------------ 1. kategori
with tab_kat:
    st.subheader("Kategori produk apa yang menyumbang revenue tertinggi, dan mana yang review-nya di bawah rata-rata?")
    top_n = st.slider("Jumlah kategori teratas", 5, 20, 10)
    kat = (df.groupby("category")
             .agg(revenue=("price", "sum"), item_terjual=("order_item_id", "count"),
                  avg_review=("review_score", "mean"))
             .sort_values("revenue", ascending=False))
    kat["pct_revenue"] = kat.revenue / kat.revenue.sum() * 100
    rata_review = df.review_score.mean()
    top = kat.head(top_n).iloc[::-1]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, max(4.5, top_n * 0.45)), sharey=True)
    ax1.barh(top.index, top.revenue, color=[HIGHLIGHT if i >= top_n - 3 else MUTED for i in range(top_n)])
    ax1.xaxis.set_major_formatter(FuncFormatter(fmt_real))
    ax1.set_title("Revenue per kategori (3 teratas disorot)", loc="left")
    ax2.barh(top.index, top.avg_review,
             color=[ALERT if v < rata_review else MUTED for v in top.avg_review])
    ax2.axvline(rata_review, color="black", ls="--", lw=1)
    ax2.text(rata_review, -0.9, f" rata-rata {fmt_dec(rata_review)}", fontsize=9, va="top")
    ax2.set_xlim(3.4, 4.6)
    ax2.set_title("Rata-rata review (merah = di bawah rata-rata)", loc="left")
    sns.despine(); plt.tight_layout()
    st.pyplot(fig)

    n_bawah = int((top.avg_review < rata_review).sum())
    st.info(f"**Insight:** {top_n} kategori teratas menyumbang **{fmt_dec(kat.head(top_n).pct_revenue.sum(), 1)}%** "
            f"revenue. Dari {top_n} kategori itu, **{n_bawah}** punya review di bawah rata-rata.")
    with st.expander("Lihat tabel kategori"):
        st.dataframe(kat.head(top_n).round(2))

# ------------------------------------------------------------------ 2. tren
with tab_tren:
    st.subheader("Bagaimana tren order dan revenue bulanan (MoM), serta bulan apa yang mencatat lonjakan tertinggi dan penurunan terbesar?")
    bln = (df.assign(bulan=df.order_purchase_timestamp.dt.to_period("M").astype(str))
             .groupby("bulan").agg(jumlah_order=("order_id", "nunique"), revenue=("price", "sum")))
    bln["order_mom_pct"] = bln.jumlah_order.pct_change() * 100
    bln["revenue_mom_pct"] = bln.revenue.pct_change() * 100
    # Lonjakan persentase dari basis kecil tidak representatif: hanya bulan dengan bulan sebelumnya >= 1.000 order
    valid = bln.jumlah_order.shift(1) >= 1000

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(13, 10), sharex=True)
    ax1.plot(bln.index, bln.jumlah_order, marker="o", color=HIGHLIGHT)
    ax1.set_ylabel("Jumlah order"); ax1.set_title("Jumlah order per bulan", loc="left")
    ax2.plot(bln.index, bln.revenue, marker="o", color="#2e8b57")
    ax2.yaxis.set_major_formatter(FuncFormatter(fmt_real))
    ax2.set_title("Revenue per bulan", loc="left")
    idx, lebar = np.arange(len(bln)), 0.38
    ax3.bar(idx - lebar / 2, bln.order_mom_pct.fillna(0), lebar, color=HIGHLIGHT, label="Order")
    ax3.bar(idx + lebar / 2, bln.revenue_mom_pct.fillna(0), lebar, color="#2e8b57", label="Revenue")
    ax3.axhline(0, color="black", lw=0.8)
    ax3.set_xticks(idx); ax3.set_xticklabels(bln.index, rotation=60, ha="right")
    ax3.set_ylabel("% perubahan"); ax3.legend(frameon=False, ncol=2, loc="upper right")
    ax3.set_title("Pertumbuhan Month-over-Month: order vs revenue", loc="left")
    for ax in (ax1, ax2, ax3):
        ax.grid(axis="x", visible=False)
    sns.despine(); plt.tight_layout()
    st.pyplot(fig)

    if valid.any():
        o_naik, o_turun = bln.order_mom_pct[valid].idxmax(), bln.order_mom_pct[valid].idxmin()
        r_naik, r_turun = bln.revenue_mom_pct[valid].idxmax(), bln.revenue_mom_pct[valid].idxmin()
        st.info(f"**Insight:** lonjakan order tertinggi **{o_naik}** ({bln.order_mom_pct[o_naik]:+.1f}% MoM), "
                f"penurunan order terbesar **{o_turun}** ({bln.order_mom_pct[o_turun]:+.1f}%). "
                f"Lonjakan revenue tertinggi **{r_naik}** ({bln.revenue_mom_pct[r_naik]:+.1f}%), "
                f"penurunan revenue terbesar **{r_turun}** ({bln.revenue_mom_pct[r_turun]:+.1f}%). "
                "Bulan yang bulan sebelumnya berisi kurang dari 1.000 order tidak dihitung karena basisnya terlalu kecil.")
    else:
        st.info("Pilih rentang yang mencakup minimal 2 bulan dengan basis >= 1.000 order untuk melihat perubahan MoM.")
    with st.expander("Lihat tabel bulanan"):
        st.dataframe(bln.round(2))

# ------------------------------------------------------------------ 3. state
with tab_state:
    st.subheader("State mana yang pengirimannya paling lama/terlambat, dan berapa selisih review order tepat waktu vs terlambat?")
    min_order = st.slider("Minimal jumlah order per state (menghindari state dengan sampel kecil)", 1, 500, 50)
    state = (order_lvl.groupby("customer_state")
               .agg(jumlah_order=("order_id", "nunique"), avg_delivery_days=("delivery_days", "mean"),
                    pct_terlambat=("is_late", lambda s: s.mean() * 100), avg_review=("review_score", "mean")))
    state = state[state.jumlah_order >= min_order].sort_values("avg_delivery_days")

    if state.empty:
        st.warning("Tidak ada state yang memenuhi minimal order. Turunkan batas minimalnya.")
    else:
        rata_kirim = order_lvl.delivery_days.mean()
        fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(16, max(5, len(state) * 0.32)), sharey=True)
        warna = [ALERT if v > rata_kirim else MUTED for v in state.avg_delivery_days]
        ax1.barh(state.index, state.avg_delivery_days, color=warna)
        ax1.axvline(rata_kirim, color="black", ls="--", lw=1)
        ax1.set_title("Rata-rata lama kirim (hari)", loc="left")
        ax2.barh(state.index, state.pct_terlambat, color=warna)
        ax2.set_title("% order terlambat", loc="left")
        ax3.barh(state.index, state.avg_review, color=warna)
        ax3.set_xlim(3.0, 4.6); ax3.set_title("Rata-rata review", loc="left")
        sns.despine(); plt.tight_layout()
        st.pyplot(fig)

        terlama = state.avg_delivery_days.idxmax()
        st.info(f"**Insight:** state dengan pengiriman terlama adalah **{terlama}** "
                f"({fmt_dec(state.loc[terlama, 'avg_delivery_days'], 1)} hari, review "
                f"{fmt_dec(state.loc[terlama, 'avg_review'])}). Merah = lebih lama dari rata-rata "
                f"({fmt_dec(rata_kirim, 1)} hari).")

# ------------------------------------------------------------------ 4. binning
with tab_bin:
    st.subheader("Binning: bagaimana rata-rata review berubah menurut kelompok lama pengiriman?")
    st.caption("Teknik clustering manual: order dikelompokkan ke interval lama pengiriman dengan `pd.cut`.")
    o = order_lvl.dropna(subset=["delivery_days"]).copy()
    o["kelompok_kirim"] = pd.cut(o.delivery_days, bins=[0, 7, 14, 21, 30, np.inf],
                                 labels=["<= 7 hari", "8-14 hari", "15-21 hari", "22-30 hari", "> 30 hari"])
    bin_df = (o.groupby("kelompok_kirim", observed=True)
                .agg(jumlah_order=("order_id", "count"), avg_review=("review_score", "mean"),
                     pct_review_1_2=("review_score", lambda s: (s <= 2).mean() * 100)))
    bin_df["pct_order"] = bin_df.jumlah_order / bin_df.jumlah_order.sum() * 100

    fig, ax = plt.subplots(figsize=(9, 4.5))
    warna = [ALERT if lbl in ("22-30 hari", "> 30 hari") else MUTED for lbl in bin_df.index.astype(str)]
    ax.bar(bin_df.index.astype(str), bin_df.avg_review, color=warna)
    for i, (m, p) in enumerate(zip(bin_df.avg_review, bin_df.pct_order)):
        ax.text(i, m + 0.05, f"{m:.2f}\n({p:.1f}% order)", ha="center", fontsize=9)
    ax.set_ylim(0, 5.3); ax.set_ylabel("Rata-rata skor review")
    ax.set_title("Semakin lama pengiriman, semakin rendah review", loc="left")
    ax.grid(axis="x", visible=False); sns.despine(); plt.tight_layout()
    st.pyplot(fig)
    cepat, lambat = o[o.delivery_days <= 21].review_score.mean(), o[o.delivery_days > 21].review_score.mean()
    if pd.notna(cepat) and pd.notna(lambat):
        st.info(f"**Insight:** rata-rata review order yang tiba dalam <= 21 hari adalah **{fmt_dec(cepat)}**, "
                f"sedangkan order > 21 hari **{fmt_dec(lambat)}** (selisih {fmt_dec(cepat - lambat)} poin). "
                "Ini hubungan antar kelompok, bukan bukti sebab-akibat.")
    with st.expander("Lihat tabel binning"):
        st.dataframe(bin_df.round(2))

# ------------------------------------------------------------------ 5. RFM
with tab_rfm:
    st.subheader("RFM Analysis: segmentasi pelanggan berdasarkan perilaku belanja")
    st.caption("**Recency** = hari sejak pembelian terakhir, **Frequency** = jumlah order, **Monetary** = total belanja. "
               "Skor R & M memakai kuartil (4 = terbaik); F memakai aturan bisnis (1, 2, >=3 order). "
               "RFM dihitung ulang sesuai filter yang dipilih.")
    if df.customer_unique_id.nunique() < 20:
        st.warning("Pelanggan terlalu sedikit untuk segmentasi RFM. Perluas filter.")
    else:
        rfm = hitung_rfm(df)
        seg = (rfm.groupby("segmen")
                  .agg(pelanggan=("customer_unique_id", "count"), avg_recency=("recency", "mean"),
                       avg_frequency=("frequency", "mean"), avg_monetary=("monetary", "mean"),
                       total_revenue=("monetary", "sum"))
                  .reindex(URUTAN_SEGMEN).dropna(how="all"))
        seg["pct_pelanggan"] = seg.pelanggan / seg.pelanggan.sum() * 100
        seg["pct_revenue"] = seg.total_revenue / seg.total_revenue.sum() * 100

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 4.8), sharey=True)
        y = seg.index[::-1]
        ax1.barh(y, seg.pct_pelanggan[::-1], color=MUTED)
        ax2.barh(y, seg.pct_revenue[::-1], color=HIGHLIGHT)
        for ax, col, ttl in ((ax1, "pct_pelanggan", "% pelanggan"), (ax2, "pct_revenue", "% revenue")):
            for i, v in enumerate(seg[col][::-1]):
                ax.text(v + 0.5, i, f"{v:.1f}%", va="center", fontsize=9)
            ax.set_title(ttl, loc="left"); ax.set_xlim(0, max(seg.pct_pelanggan.max(), seg.pct_revenue.max()) * 1.2)
            ax.grid(axis="y", visible=False)
        sns.despine(); plt.tight_layout()
        st.pyplot(fig)

        satu_kali = (rfm.frequency == 1).mean() * 100
        lapsed = seg.loc["Lapsed Big Spenders"] if "Lapsed Big Spenders" in seg.index else None
        teks = f"**{fmt_dec(satu_kali, 1)}%** pelanggan hanya membeli sekali, sehingga retensi menjadi masalah utama."
        if lapsed is not None:
            teks += (f" Segmen *Lapsed Big Spenders* ({fmt_dec(lapsed.pct_pelanggan, 1)}% pelanggan, "
                     f"{fmt_dec(lapsed.pct_revenue, 1)}% revenue) paling layak dihubungi ulang.")
        st.info("**Insight:** " + teks)
        st.dataframe(seg.round(2))
        st.download_button("⬇️ Unduh data RFM (CSV)",
                           rfm.drop(columns="terakhir_beli").to_csv(index=False).encode("utf-8"),
                           "rfm_pelanggan.csv", "text/csv")

# ------------------------------------------------------------------ 6. geospasial
with tab_geo:
    st.subheader("Geospatial Analysis: sebaran pelanggan dan kaitannya dengan lama pengiriman")
    geo = df.dropna(subset=["lat", "lng"])
    if geo.empty:
        st.warning("Tidak ada data koordinat untuk filter ini.")
    else:
        pel = geo.drop_duplicates("customer_unique_id")
        geo_state = (geo.groupby("customer_state")
                        .agg(lat=("lat", "mean"), lng=("lng", "mean"), revenue=("price", "sum"),
                             avg_delivery_days=("delivery_days", "mean")))
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7.5))
        hb = ax1.hexbin(pel.lng, pel.lat, gridsize=55, bins="log", cmap="Blues", mincnt=1)
        ax1.set_title("Kepadatan pelanggan", loc="left")
        plt.colorbar(hb, ax=ax1, label="Jumlah pelanggan (skala log)", shrink=0.7)

        ukuran = 120 + 2600 * (geo_state.revenue / geo_state.revenue.max()) ** 0.6
        sc = ax2.scatter(geo_state.lng, geo_state.lat, s=ukuran, c=geo_state.avg_delivery_days, cmap="YlOrRd",
                         edgecolor="black", linewidth=0.6, alpha=0.9)
        for st_name, r in geo_state.iterrows():
            ax2.annotate(st_name, (r.lng, r.lat), ha="center", va="center", fontsize=8, fontweight="bold")
        ax2.set_title("Revenue (ukuran) dan lama pengiriman (warna) per state", loc="left")
        plt.colorbar(sc, ax=ax2, label="Rata-rata lama pengiriman (hari)", shrink=0.7)
        for ax in (ax1, ax2):
            ax.set_xlabel("Longitude"); ax.set_ylabel("Latitude"); ax.set_aspect("equal"); ax.grid(False)
        sns.despine(); plt.tight_layout()
        st.pyplot(fig)
        st.info("**Insight:** pelanggan terkonsentrasi di Tenggara dan Selatan Brasil. Ukuran bubble menunjukkan revenue "
                "dan warna menunjukkan rata-rata lama pengiriman per state. Analisis jarak penjual-pelanggan "
                "(Haversine) ada di notebook.")

        with st.expander("Peta interaktif sebaran pelanggan"):
            st.map(pel[["lat", "lng"]].rename(columns={"lng": "lon"}).sample(min(5000, len(pel)), random_state=1))

st.divider()
st.caption("Proyek Analisis Data - Grace Pinkkan Ladyna | Sumber data: Olist Brazilian E-Commerce Public Dataset")