# -*- coding: utf-8 -*-
"""
Hal Esnafı Takip Sistemi - TAM SAYFA GİRİŞ EKRANIYLA
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import database as db

st.set_page_config(page_title="TEMİNAT MEKTUBU TEBLİGAT TAKİP SİSTEMİ", layout="wide")

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #020617 0%, #0f172a 100%) !important; }
    h1, h2, h3, h4, p, span, label { color: #FFFFFF !important; }
    div.stButton > button, div.stDownloadButton > button {
        background-color: #2563eb !important;
        color: white !important;
        border-radius: 8px !important;
        font-weight: bold !important;
        width: 100% !important;
    }
    div.stButton > button:hover, div.stDownloadButton > button:hover {
        background-color: #1d4ed8 !important;
        box-shadow: 0px 4px 12px rgba(37, 99, 235, 0.3) !important;
    }
    .login-box {
        background: rgba(30, 41, 59, 0.9);
        border: 2px solid #3b82f6;
        border-radius: 15px;
        padding: 50px;
        max-width: 400px;
        margin: 100px auto;
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

def to_excel_formatted(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='TakipListesi')
        workbook = writer.book
        worksheet = writer.sheets['TakipListesi']
        header_format = workbook.add_format({'bold': True, 'bg_color': '#1e293b', 'font_color': 'white'})
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
        for i, col in enumerate(df.columns):
            column_len = max(df[col].astype(str).str.len().max(), len(col)) + 4
            worksheet.set_column(i, i, column_len)
    return output.getvalue()

def clean_currency(value):
    if pd.isna(value) or value == "" or str(value).lower() == "none": return 0.0
    try:
        if isinstance(value, str):
            return float(value.replace('.', '').replace(',', '.'))
        return float(value)
    except: return 0.0

def parse_date(date_str):
    if pd.isna(date_str) or not str(date_str).strip() or str(date_str).lower() in ["none", "nan", ""]: return None
    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try: return datetime.strptime(str(date_str).strip(), fmt)
        except: continue
    return None

def calculate_gecikme_custom(tebligat_tarihi_str):
    dt = parse_date(tebligat_tarihi_str)
    if not dt: return 0
    return max(0, (datetime.now() - dt).days)

def row_style_logic(row):
    g = row.get("Tebliğ Tarihinden Bugüne Geçen Gün")
    if pd.isna(g) or g <= 30: return [""] * len(row)
    return ["background-color: rgba(220, 38, 38, 0.8); color: #FFFFFF;"] * len(row)

def create_word_tebligat(row):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Times New Roman'
    style.font.size = Pt(12)
    unvan = str(row.get("Yazıhane Adı", "")).upper()
    hal_no = str(row.get("Yazıhane No", ""))
    hal_adi = str(row.get("Hal", ""))
    tarih_son = "30.09.2026"
    is_sirket = any(x in unvan for x in ["LTD", "ŞTİ", "A.Ş", "ANONİM", "KOOP"])
    hitap = "Bilgilerinize rica ederim." if is_sirket else "Bilgilerinize sunulur."
    
    p_header = doc.add_paragraph()
    p_header.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_h = p_header.add_run(f"{unvan}\n{hal_adi} Hal No: {hal_no}")
    run_h.bold = True
    
    metinler = [
        "5957 sayılı Kanunun 12'nci maddesinin birinci fıkrasında teminat alınması gerektiği hükmü yer almaktadır.",
        "Yönetmeliğin 31'inci maddesinin onikinci fıkrasında eksik teminatın bir ay içinde tamamlanması gerektiği ifade edilmektedir.",
        f"Kayıtlarımızda, {hal_adi} Hali {hal_no} numaralı işyerinizin teminat süresinin {tarih_son} tarihinde sona erdiği tespit edilmiştir.",
        "Bu nedenle teminatı yazımızın tarafınıza tebliğ edildiği tarihten itibaren 30 gün içinde teslim etmeniz gerekmektedir.",
        hitap
    ]
    
    for m in metinler:
        para = doc.add_paragraph(m)
        para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        para.paragraph_format.line_spacing = 1.15
    
    p_sign = doc.add_paragraph()
    p_sign.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run_s = p_sign.add_run("İsrafil AYDIN\nHal Müdürü")
    run_s.bold = True
    
    target = BytesIO()
    doc.save(target)
    return target.getvalue()

def login_page():
    """Tam sayfa giriş ekranı"""
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown("### 🏛️ TEMİNAT MEKTUBU")
        st.markdown("### TEBLİGAT TAKİP SİSTEMİ")
        st.markdown("---")
        sifre = st.text_input("🔐 Yönetici Şifresi", type="password", placeholder="Şifreyi girin")
        
        if st.button("🔓 Giriş Yap", use_container_width=True, key="login_btn"):
            if sifre == "1234":
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("❌ Hatalı Şifre!")

def main_dashboard():
    """Ana yönetim paneli"""
    with st.sidebar:
        st.header("🔑 Yönetici Paneli")
        st.success("✅ Giriş Yapıldı")
        if st.button("🚪 Çıkış Yap", use_container_width=True):
            st.session_state["authenticated"] = False
            st.rerun()
        st.divider()

    st.markdown("<h1>🏛️ TEMİNAT MEKTUBU TEBLİGAT TAKİP SİSTEMİ</h1>", unsafe_allow_html=True)
    
    df_raw = db.get_all()
    
    if not df_raw.empty:
        for col in df_raw.columns:
            df_raw[col] = df_raw[col].apply(lambda x: "" if str(x).lower() in ["none", "nan", ""] else x)
        
        df_raw["Yazıhane No"] = pd.to_numeric(df_raw["Yazıhane No"], errors='coerce').fillna(0).astype(int)
        df_raw["Teminat Tutar"] = df_raw["Teminat Tutar"].apply(clean_currency)
        df_raw["Kalan"] = df_raw["Kalan"].apply(clean_currency)
        df_raw["Tebliğ Tarihinden Bugüne Geçen Gün"] = df_raw["Tebligat Tarihi"].apply(calculate_gecikme_custom)
        df_raw = df_raw.sort_values(by="Yazıhane No")

        st.markdown("### 📊 Genel Durum Özeti")
        c1, c2, c3, c4, c5 = st.columns(5)
        eksik_df = df_raw[df_raw["Durum"].astype(str).str.contains("Eksik", case=False, na=False)]
        c1.metric("🔴 Toplam Eksik", f"{len(eksik_df)}")
        odendi_fazla = len(df_raw[df_raw["Durum"].astype(str).str.contains("Ödendi|Odendi|Fazla", case=False, na=False)])
        c2.metric("🟢 Ödendi + Fazla", f"{odendi_fazla}")
        teblig_edilen = len(df_raw[(df_raw["Tebligat Tarihi"].astype(str).str.strip() != "")])
        c3.metric("📩 Tebliğ Edilen", f"{teblig_edilen}")
        geciken_sayisi = len(df_raw[df_raw["Tebliğ Tarihinden Bugüne Geçen Gün"] > 30])
        c4.metric("⚠️ 30 Günü Geçen", f"{geciken_sayisi}")
        c5.metric("⚪ Tebligat Yapılmamış", f"{len(eksik_df[(eksik_df['Tebligat Sayı'].astype(str).str.strip() == '')])}")
        st.divider()

    with st.sidebar:
        st.header("🔍 Filtreleme")
        s_no = st.text_input("Yazıhane No")
        s_ad = st.text_input("Esnaf Adı")
        u_hals = sorted(df_raw["Hal"].dropna().unique().tolist()) if not df_raw.empty else []
        u_durums = sorted(df_raw["Durum"].dropna().unique().tolist()) if not df_raw.empty else []
        sel_hal = st.selectbox("Hal Bölgesi", ["Tümü"] + u_hals)
        sel_durum = st.selectbox("Durum", ["Tümü"] + u_durums)

    df_f = df_raw.copy() if not df_raw.empty else pd.DataFrame()
    if not df_f.empty:
        if sel_hal != "Tümü": df_f = df_f[df_f["Hal"] == sel_hal]
        if sel_durum != "Tümü": df_f = df_f[df_f["Durum"] == sel_durum]
        if s_no:
            try: df_f = df_f[df_f["Yazıhane No"] == int(s_no)]
            except: pass
        if s_ad: df_f = df_f[df_f["Yazıhane Adı"].astype(str).str.contains(s_ad, case=False, na=False)]

    tab1, tab2, tab3 = st.tabs(["📋 TAKİP PANELİ", "⚡ TEBLİGAT GİRİŞİ", "📥 VERİ GÜNCELLEME"])

    with tab1:
        if df_f.empty:
            st.warning("Veri bulunamadı.")
        else:
            cols_export = ["Yazıhane No", "Yazıhane Adı", "Teminat Tutar", "Durum", "Kalan"]
            excel_data = to_excel_formatted(df_f[cols_export])
            st.download_button("📥 Excel İndir", data=excel_data,
                               file_name=f"Hal_Takip_{datetime.now().strftime('%d_%m_%Y')}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            
            cols_show = ["Yazıhane No", "Yazıhane Adı", "Teminat Tutar", "Durum", "Kalan"]
            st.dataframe(df_f[cols_show].style.apply(row_style_logic, axis=1),
                         use_container_width=True, hide_index=True)

    with tab2:
        if df_f.empty:
            st.info("Veri bulunamadı.")
        else:
            st.subheader("📄 Word Tebligat Hazırla")
            esnaf_list = df_f.apply(lambda r: f"{r['Yazıhane No']} - {r['Yazıhane Adı']}", axis=1).tolist()
            c1, c2 = st.columns([3, 1])
            with c1:
                secilen = st.selectbox("Esnaf Seçin:", options=esnaf_list, key="sb_word")
            if secilen:
                y_no = int(secilen.split(" - ")[0])
                row_data = df_f[df_f["Yazıhane No"] == y_no].iloc[0]
                word_bin = create_word_tebligat(row_data)
                with c2:
                    st.write("")
                    st.download_button(f"📥 {y_no} Nolu Word", data=word_bin,
                                       file_name=f"Tebligat_{y_no}.docx",
                                       mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    with tab3:
        st.subheader("📥 Excel Yükle")
        up = st.file_uploader("Excel dosyası:", type=["xlsx"])
        if up and st.button("🚀 Yükle"):
            try:
                check_df = pd.read_excel(up)
                required_cols = ["Yazıhane No", "Yazıhane Adı", "Hal", "Durum"]
                if not all(col in check_df.columns for col in required_cols):
                    st.error("❌ Gerekli sütunlar yok!")
                else:
                    db.upload_excel(up)
                    st.success("✅ Yüklendi!")
                    st.rerun()
            except Exception as e:
                st.error(f"Hata: {e}")

if __name__ == "__main__":
    if not st.session_state["authenticated"]:
        login_page()
    else:
        main_dashboard()
