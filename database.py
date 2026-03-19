# -*- coding: utf-8 -*-
"""
Hal Esnafı Teminat ve Tebligat Takip Sistemi - Veritabanı Modülü
Uyumlu ve Filtreleme Destekli Final Versiyon
"""
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime

# Veritabanı dosya yolu
DB_PATH = Path(__file__).resolve().parent / "hal_teminat.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    """Tabloyu oluşturur. Yazıhane No unique (PRIMARY KEY)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS esnaf_teminat (
            "Yazıhane No" TEXT PRIMARY KEY,
            "Vergi No" TEXT,
            "Teminat Tutar" REAL,
            "Yazıhane Adı" TEXT,
            "İlk Tahsis Teminat" REAL,
            "Thk Toplam" REAL,
            "Mektup Sayısı" INTEGER,
            "Mektup Tutarı" REAL,
            "Kalan" REAL,
            "Durum" TEXT,
            "Süresiz Var" TEXT,
            "Hal" TEXT,
            "Azalma Tarihi" TEXT,
            "Tebligat Sayı" TEXT,
            "Tebligat Tarihi" TEXT
        )
    """)
    conn.commit()
    conn.close()

def upsert_from_excel(df: pd.DataFrame) -> tuple[int, int, int]:
    """
    Excel'e göre veritabanını tam senkronize eder.
    YENİ: Hal No (0, 573, Boş) filtreleme kriterleri buraya eklendi.
    """
    init_db()
    conn = get_connection()
    cur = conn.cursor()

    # 1. Mevcut tebligat bilgilerini al (Senkronizasyon sırasında kaybolmasınlar)
    cur.execute('SELECT "Yazıhane No", "Tebligat Sayı", "Tebligat Tarihi" FROM esnaf_teminat')
    rows = cur.fetchall()
    existing_data = {row[0]: (row[1], row[2]) for row in rows}
    db_yazihane_nolar = set(existing_data.keys())

    excel_yazihane_nolar = set()
    updated = 0
    inserted = 0
    deleted = 0

    # 2. Excel'deki verileri işle
    for _, row in df.iterrows():
        yazihane_no = str(row.get("Yazıhane No", "")).strip()
        hal_val = str(row.get("Hal", "")).strip().lower()

        # --- KRİTİK FİLTRELEME: Hal No Boş, 0 veya 573 ise ATLA ---
        if not yazihane_no or yazihane_no in ["nan", "0", "None", ""]:
            continue
        
        if not hal_val or hal_val in ["0", "573", "nan", "none", ""]:
            continue
        
        excel_yazihane_nolar.add(yazihane_no)

        # Durum kontrolü (Küçük harf duyarsızlaştırma)
        new_durum = str(row.get("Durum", "")).strip().lower()
        new_durum = new_durum.replace("İ", "i").replace("I", "ı")

        t_sayi = None
        t_tarih = None

        # Eğer bu kayıt zaten varsa, eski tebligat bilgilerini koru
        if yazihane_no in db_yazihane_nolar:
            old_sayi, old_tarih = existing_data[yazihane_no]
            
            # Eğer durum "Ödendi" veya "Fazla" olduysa tebligatı sıfırla, yoksa eskiyi koru
            if any(x in new_durum for x in ["ödendi", "odendi", "fazla"]):
                t_sayi = None
                t_tarih = None
            else:
                t_sayi = old_sayi
                t_tarih = old_tarih
            updated += 1
        else:
            inserted += 1

        def _val(v):
            if pd.isna(v) or str(v).lower() in ["nan", "none"]: return None
            if isinstance(v, (datetime, pd.Timestamp)): return v.strftime("%d.%m.%Y")
            return v

        values = (
            yazihane_no, _val(row.get("Vergi No")), _val(row.get("Teminat Tutar")),
            _val(row.get("Yazıhane Adı")), _val(row.get("İlk Tahsis Teminat")),
            _val(row.get("Thk Toplam")), _val(row.get("Mektup Sayısı")),
            _val(row.get("Mektup Tutarı")), _val(row.get("Kalan")),
            str(row.get("Durum", "")), _val(row.get("Süresiz Var")),
            _val(row.get("Hal")), _val(row.get("Azalma Tarihi")),
            t_sayi, t_tarih
        )

        cur.execute("""
            INSERT INTO esnaf_teminat (
                "Yazıhane No", "Vergi No", "Teminat Tutar", "Yazıhane Adı",
                "İlk Tahsis Teminat", "Thk Toplam", "Mektup Sayısı", "Mektup Tutarı",
                "Kalan", "Durum", "Süresiz Var", "Hal", "Azalma Tarihi",
                "Tebligat Sayı", "Tebligat Tarihi"
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT("Yazıhane No") DO UPDATE SET
                "Vergi No" = excluded."Vergi No",
                "Teminat Tutar" = excluded."Teminat Tutar",
                "Yazıhane Adı" = excluded."Yazıhane Adı",
                "İlk Tahsis Teminat" = excluded."İlk Tahsis Teminat",
                "Thk Toplam" = excluded."Thk Toplam",
                "Mektup Sayısı" = excluded."Mektup Sayısı",
                "Mektup Tutarı" = excluded."Mektup Tutarı",
                "Kalan" = excluded."Kalan",
                "Durum" = excluded."Durum",
                "Süresiz Var" = excluded."Süresiz Var",
                "Hal" = excluded."Hal",
                "Azalma Tarihi" = excluded."Azalma Tarihi",
                "Tebligat Sayı" = excluded."Tebligat Sayı",
                "Tebligat Tarihi" = excluded."Tebligat Tarihi"
        """, values)

    # 3. SİLME İŞLEMİ: Excel'den çıkarılan (veya filtrelenen) kayıtları veritabanından sil
    to_delete = db_yazihane_nolar - excel_yazihane_nolar
    for no in to_delete:
        cur.execute('DELETE FROM esnaf_teminat WHERE "Yazıhane No" = ?', (no,))
        deleted += 1

    conn.commit()
    conn.close()
    return updated, inserted, deleted

def upload_excel(file):
    """Excel yükleme köprüsü"""
    df = pd.read_excel(file)
    # Kolon isimlerindeki boşlukları temizle
    df.columns = [str(c).strip() for c in df.columns]
    return upsert_from_excel(df)

def get_all() -> pd.DataFrame:
    init_db()
    conn = get_connection()
    # Verileri Yazıhane No'ya göre sayısal sırala
    df = pd.read_sql_query('SELECT * FROM esnaf_teminat ORDER BY CAST("Yazıhane No" AS INTEGER)', conn)
    conn.close()
    return df

def update_tebligat(yazihane_no: str, tebligat_sayi: str, tebligat_tarihi: str) -> bool:
    """Tekli tebligat güncelleme (Editor üzerinden gelen)"""
    init_db()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        'UPDATE esnaf_teminat SET "Tebligat Sayı" = ?, "Tebligat Tarihi" = ? WHERE "Yazıhane No" = ?',
        (str(tebligat_sayi).strip() if tebligat_sayi and str(tebligat_sayi).lower() != "none" else None, 
         str(tebligat_tarihi).strip() if tebligat_tarihi and str(tebligat_tarihi).lower() != "none" else None, 
         str(yazihane_no).strip())
    )
    n = cur.rowcount
    conn.commit()
    conn.close()
    return n > 0