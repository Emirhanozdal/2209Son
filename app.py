# ==============================================================================
# GEREKLİ KÜTÜPHANELER
# ==============================================================================
import streamlit as st
from PIL import Image
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import os
import traceback
from io import BytesIO
import base64
from collections import Counter
import locale
import datetime

# ==============================================================================
# KÜTÜPHANE KONTROLLERİ
# ==============================================================================
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

# ==============================================================================
# VERİ YAPISI
# ==============================================================================
@dataclass
class ValidationResult:
    """Bir doğrulama bölümünün sonuçlarını tutan veri yapısı."""
    section_name: str
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

# ==============================================================================
# YARDIMCI FONKSİYONLAR
# ==============================================================================
def display_pdf_from_bytes(pdf_bytes: bytes):
    try:
        base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
        pdf_display = f'<div style="height: 700px; border-radius: 15px; overflow: hidden; border: 1px solid rgba(255, 255, 255, 0.2); box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);"><iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="100%" type="application/pdf"></iframe></div>'
        st.markdown(pdf_display, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"PDF görüntülenirken bir hata oluştu: {e}")

def display_custom_spinner(text: str):
    spinner_html = f"""
    <style>
        .spinner-text {{
            text-align: center; color: #FFD700; font-size: 1.1em; font-weight: bold;
            margin-top: 20px; margin-bottom: 20px;
        }}
        .spinner-container {{
            display: grid; place-content: center; overflow: hidden; margin-bottom: 2rem;
        }}
        :root {{ --border-size: 1.5%; --duration: 7s; --open-from: .5; }}
        @property --progress {{ syntax: '<number>'; initial-value: 0; inherits: false; }}
        @keyframes progress {{ to {{ --progress: 1; }} }}
        .hexagon {{
            grid-area: 1 / 1; width: clamp(100px, 40vmin, 200px); aspect-ratio: 1; background: #FFD700;
            --o: (var(--progress) * 50%); --i: max(0%, var(--o) - var(--border-size));
            clip-path: polygon(
                calc(50% + var(--o) * cos(0deg)) calc(50% + var(--o) * sin(0deg)), calc(50% + var(--o) * cos(60deg)) calc(50% + var(--o) * sin(60deg)),
                calc(50% + var(--o) * cos(120deg)) calc(50% + var(--o) * sin(120deg)), calc(50% + var(--o) * cos(180deg)) calc(50% + var(--o) * sin(180deg)),
                calc(50% + var(--o) * cos(240deg)) calc(50% + var(--o) * sin(240deg)), calc(50% + var(--o) * cos(300deg)) calc(50% + var(--o) * sin(300deg)),
                calc(50% + var(--o) * cos(360deg)) calc(50% + var(--o) * sin(360deg)), calc(50% + var(--i) * cos(360deg)) calc(50% + var(--i) * sin(360deg)),
                calc(50% + var(--i) * cos(300deg)) calc(50% + var(--i) * sin(300deg)), calc(50% + var(--i) * cos(240deg)) calc(50% + var(--i) * sin(240deg)),
                calc(50% + var(--i) * cos(180deg)) calc(50% + var(--i) * sin(180deg)), calc(50% + var(--i) * cos(120deg)) calc(50% + var(--i) * sin(120deg)),
                calc(50% + var(--i) * cos(60deg)) calc(50% + var(--i) * sin(60deg)), calc(50% + var(--i) * cos(0deg)) calc(50% + var(--i) * sin(0deg))
            );
            --a: (clamp(0, (var(--progress) - var(--open-from)) / (1 - var(--open-from)), 1) * 30deg);
            mask-image: conic-gradient(#0000 calc(var(--a)), #000 0 calc(60deg - var(--a)), #0000 0 calc(60deg + var(--a)), #000 0 calc(120deg - var(--a)), #0000 0 calc(120deg + var(--a)), #000 0 calc(180deg - var(--a)), #0000 0 calc(180deg + var(--a)), #000 0 calc(240deg - var(--a)), #0000 0 calc(240deg + var(--a)), #000 0 calc(300deg - var(--a)), #0000 0 calc(300deg + var(--a)), #000 0 calc(360deg - var(--a)), #0000 0);
            animation: progress var(--duration) linear infinite; --sibling-count: 6; --sibling-index: 1;
            animation-delay: calc(-1 * var(--duration) * (var(--sibling-index) - 1) / var(--sibling-count));
        }}
        .hexagon:nth-child(2) {{ --sibling-index: 2; }} .hexagon:nth-child(3) {{ --sibling-index: 3; }}
        .hexagon:nth-child(4) {{ --sibling-index: 4; }} .hexagon:nth-child(5) {{ --sibling-index: 5; }}
        .hexagon:nth-child(6) {{ --sibling-index: 6; }} .hexagon:nth-child(2n) {{ rotate: 30deg; }}
    </style>
    <div>
        <p class="spinner-text">{text}</p>
        <div class="spinner-container">
            <div class="hexagon"></div><div class="hexagon"></div><div class="hexagon"></div>
            <div class="hexagon"></div><div class="hexagon"></div><div class="hexagon"></div>
        </div>
    </div>
    """
    st.markdown(spinner_html, unsafe_allow_html=True)

def load_local_file_as_base64(filename: str) -> Optional[str]:
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(script_dir, filename)
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return None
    except Exception as e:
        st.warning(f"Dosya yüklenirken hata: {e}")
        return None
        
def format_results_for_download(results: Dict[str, ValidationResult]) -> str:
    """Analiz sonuçlarını .txt dosyası için formatlar."""
    report_lines = []
    report_lines.append("TÜBİTAK 2209-A PROJE ÖN DEĞERLENDİRME RAPORU")
    report_lines.append(f"Rapor Tarihi: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("="*50)
    
    for result in results.values():
        report_lines.append(f"\n--- {result.section_name.upper()} ---")
        if not result.errors and not result.warnings:
            report_lines.append(">> Bu bölümde önemli bir sorun veya uyarı tespit edilmedi.")
        
        if result.errors:
            report_lines.append("\n[KRİTİK HATALAR]")
            for e in result.errors: report_lines.append(f"  - {e}")
        
        if result.warnings:
            report_lines.append("\n[ÖNEMLİ UYARILAR]")
            for w in result.warnings: report_lines.append(f"  - {w}")
            
        if result.suggestions:
            report_lines.append("\n[İYİLEŞTİRME ÖNERİLERİ]")
            for s in result.suggestions: report_lines.append(f"  - {s}")
            
    report_lines.append("\n\n" + "="*50)
    report_lines.append("Yasal Uyarı: Bu rapor, resmi bir TÜBİTAK değerlendirmesi değildir. Yalnızca başvuru sahiplerine yardımcı olmak amacıyla hazırlanmış bir ön kontrol sistemidir.")
    return "\n".join(report_lines)

# ==============================================================================
# ANA DOĞRULAYICI SINIFI (MANTIKSAL HATALAR DÜZELTİLDİ)
# ==============================================================================
class TubitakFormValidator:
    def __init__(self):
        try: locale.setlocale(locale.LC_ALL, 'tr_TR.UTF-8')
        except locale.Error:
            try: locale.setlocale(locale.LC_ALL, 'Turkish_Turkey.1254')
            except locale.Error: pass

        self.MAIN_PATTERNS = {
            "genel_bilgiler": r"A\.\s*GENEL\s*BİLGİLER", "ozet": r"ÖZET", "ozgun_deger": r"1\.\s*ÖZGÜN\s*DEĞER",
            "amac_ve_hedefler": r"1\.2\.\s*Amaç\s*ve\s*Hedefler", "yontem": r"2\.\s*YÖNTEM",
            "is_zaman_cizelgesi": r"İŞ-ZAMAN\s*ÇİZELGESİ", "risk_yonetimi": r"RİSK\s*YÖNETİMİ\s*TABLOSU",
            "arastirma_olanaklari": r"3\.3\.\s*Araştırma\s*Olanakları", "yaygin_etki": r"4\.\s*YAYGIN\s*ETKİ",
            "butce": r"5\.\s*BÜTÇE\s*TALEP\s*ÇİZELGESİ", "diger_konular": r"6\.\s*BELİRTMEK\s*İSTEDİĞİNİZ\s*DİĞER\s*KONULAR",
            "kaynaklar": r"(?:EK-1\s*:\s*)?KAYNAKLAR", "ekler": r"7\.\s*EKLER"
        }
        self.REQUIRED_SECTIONS = [
            "genel_bilgiler", "ozet", "ozgun_deger", "amac_ve_hedefler", 
            "yontem", "is_zaman_cizelgesi", "risk_yonetimi", "yaygin_etki", "butce", "kaynaklar"
        ]
        self.MAX_BUDGET = 9000.0
        self.BANNED_BUDGET_ITEMS = ["tablet", "bilgisayar", "yazıcı", "telefon", "hard disk", "harici disk", "fotoğraf makinesi", "kamera", "monitör"]

    def _normalize_text(self, text: str) -> str:
        text = text.replace('-\n', '')
        text = re.sub(r' +', ' ', text)
        text = re.sub(r'(\n\s*){2,}', '\n\n', text)
        return text

    def extract_text_from_pdf_bytes(self, pdf_bytes: bytes) -> str:
        if not PDFPLUMBER_AVAILABLE: raise ImportError("`pdfplumber` kütüphanesi gerekli.")
        try:
            with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
                return "\n".join(page.extract_text(x_tolerance=1, y_tolerance=1) or "" for page in pdf.pages)
        except Exception as e:
            st.error(f"PDF'ten metin çıkarılırken hata oluştu: {e}"); return ""

    def parse_document_sections(self, text: str) -> Dict[str, str]:
        normalized_text = self._normalize_text(text)
        sections = {key: "" for key in self.MAIN_PATTERNS.keys()}
        found_headers = []
        for key, pattern in self.MAIN_PATTERNS.items():
            for match in re.finditer(r"^\s*" + pattern, normalized_text, re.IGNORECASE | re.MULTILINE):
                found_headers.append({'key': key, 'start': match.start(), 'end': match.end()})
        if not found_headers: return sections
        found_headers.sort(key=lambda x: x['start'])
        for i, header in enumerate(found_headers):
            content_start = header['end']
            content_end = found_headers[i + 1]['start'] if i + 1 < len(found_headers) else len(text)
            sections[header['key']] = text[content_start:content_end].strip()
        return sections

    def _create_result(self, section_name: str) -> ValidationResult:
        return ValidationResult(section_name=section_name.replace("_", " ").title())

    def _get_field(self, text: str, pattern: str) -> Optional[str]:
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1).strip() if match and match.group(1) else None

    # --- BÖLÜM BAZLI DOĞRULAMA FONKSİYONLARI (DÜZELTİLDİ) ---

    def validate_genel_bilgiler(self, section_text: str) -> ValidationResult:
        result = self._create_result("Genel Bilgiler")
        ogrenci_adi = self._get_field(section_text, r"Adı\s*Soyadı\s*:\s*(.+)")
        if not ogrenci_adi: result.warnings.append("Başvuru Sahibinin Adı Soyadı alanı bulunamadı veya boş.")
        elif len(ogrenci_adi.split()) not in [2, 3]: result.warnings.append(f"Başvuru Sahibinin Adı Soyadı '{ogrenci_adi}' olarak algılandı. Genellikle 2 veya 3 kelimeden oluşmalıdır.")
        
        baslik = self._get_field(section_text, r"Başlığı\s*:\s*(.+)")
        if not baslik or len(baslik.split()) < 3: result.warnings.append("Araştırma Önerisinin Başlığı alanı bulunamadı veya çok kısa.")

        danisman_adi = self._get_field(section_text, r"Danışmanın\s*Adı\s*Soyadı\s*:\s*(.+)")
        if not danisman_adi: result.warnings.append("Danışmanın Adı Soyadı alanı bulunamadı veya boş.")
        elif len(danisman_adi.split()) > 4: result.warnings.append(f"Danışman Adı Soyadı '{danisman_adi}' olarak algılandı. Birden fazla danışman ismi yazılmış olabilir. Sadece bir danışman belirtilmelidir.")
        
        kurum_adi = self._get_field(section_text, r"Kurum/Kuruluş\s*:\s*(.+)")
        if not kurum_adi: result.warnings.append("Araştırmanın Yürütüleceği Kurum/Kuruluş alanı bulunamadı.")
        else:
            if "üniversitesi" not in kurum_adi.lower(): result.errors.append("Kurum/Kuruluş alanında 'Üniversitesi' ifadesi geçmiyor. Sadece üniversitenizin tam adı yazılmalıdır.")
            for ifade in ["fakülte", "enstitü", "yüksekokul", "bölüm"]:
                if ifade in kurum_adi.lower(): result.warnings.append(f"Kurum/Kuruluş alanında '{ifade}' kelimesi algılandı. Bu alana fakülte/bölüm gibi detaylar yazılmamalıdır.")
        return result

    def validate_ozet(self, section_text: str) -> ValidationResult:
        result = self._create_result("Özet")
        anahtar_kelime_match = re.search(r"Anahtar\s*Kelimeler\s*:\s*(.+)", section_text, re.IGNORECASE)
        ozet_text = re.sub(r"Anahtar\s*Kelimeler\s*:.*", "", section_text, flags=re.IGNORECASE)
        kelime_sayisi = len(ozet_text.split())

        if kelime_sayisi < 75 or kelime_sayisi > 250:
            result.warnings.append(f"Özet bölümü {kelime_sayisi} kelime. Genellikle 100-250 kelime arasında olması beklenir. Çok kısa veya çok uzun özetler projenin ana hatlarını etkili bir şekilde yansıtmayabilir.")
        
        if not anahtar_kelime_match:
            result.errors.append("Anahtar Kelimeler bölümü bulunamadı.")
        else:
            kelimeler = [k.strip() for k in re.split(r'[,;]', anahtar_kelime_match.group(1)) if k.strip()]
            if len(kelimeler) < 3 or len(kelimeler) > 5:
                result.errors.append(f"Anahtar kelime sayısı ({len(kelimeler)}) ideal aralıkta değil. 3 ila 5 anahtar kelime belirtilmelidir.")
        return result

    def validate_ozgun_deger(self, section_text: str) -> ValidationResult:
        result = self._create_result("Özgün Değer")
        kelime_sayisi = len(section_text.split())
        if kelime_sayisi < 250:
            result.warnings.append(f"Özgün Değer bölümü nispeten kısa ({kelime_sayisi} kelime). Konunun önemini, literatürdeki boşluğu ve projenizin bu boşluğu nasıl dolduracağını detaylı referanslarla açıklamanız beklenir.")
        
        referanslar = re.findall(r'\[\d+(?:,\s*\d+)*\]', section_text)
        if len(referanslar) < 5:
            result.warnings.append(f"Bu bölümde {len(referanslar)} adet referans [1] formatında bulundu. Literatürdeki mevcut durumu ve eksiklikleri göstermek için daha fazla atıf yapılması genellikle beklenir.")

        result.suggestions.append("Bu bölümde 'literatürdeki eksiklik', 'bu çalışmanın farkı', 'özgünlüğü', 'araştırma sorusu', 'hipotez' gibi ifadelere yer vererek projenizin yenilikçi yönünü vurguladığınızdan emin olun.")
        return result

    def validate_amac_ve_hedefler(self, section_text: str) -> ValidationResult:
        result = self._create_result("Amaç ve Hedefler")
        if not re.search(r"projenin\s*amac(ı|i)", section_text, re.IGNORECASE):
            result.warnings.append("Projenin genel amacı net bir şekilde 'Projenin amacı...' ifadesiyle belirtilmemiş olabilir.")
        
        maddeler = re.findall(r'^\s*[●*-]\s+', section_text, re.MULTILINE)
        if len(maddeler) < 3:
            result.warnings.append(f"Hedefler maddeler halinde belirtilmemiş veya az sayıda ({len(maddeler)} adet) hedef belirtilmiş. Hedeflerinizi ölçülebilir ve net adımlar olarak maddelendirmeniz önerilir.")
        return result

    def validate_yontem(self, section_text: str) -> ValidationResult:
        result = self._create_result("Yöntem")
        kelime_sayisi = len(section_text.split())
        if kelime_sayisi < 200:
            result.warnings.append(f"Yöntem bölümü çok kısa ({kelime_sayisi} kelime). Proje hedeflerine ulaşmak için izlenecek yolu, kullanılacak teknikleri, materyalleri ve veri analiz süreçlerini detaylı bir şekilde açıklamanız beklenir.")
        
        referanslar = re.findall(r'\[\d+(?:,\s*\d+)*\]', section_text)
        if len(referanslar) == 0:
            result.suggestions.append("Yöntem bölümünde kullandığınız spesifik metotlara veya yaklaşımlara referans vermek, metodolojinizin sağlamlığını artırabilir.")

        result.suggestions.append("Kullanacağınız spesifik teorileri (örn: DFT, FEM), yazılımları (örn: VASP, SPSS, MATLAB) ve standartları (örn: ISO, ASTM) açıkça belirttiğinizden emin olun.")
        return result

    def validate_is_zaman_cizelgesi(self, section_text: str) -> ValidationResult:
        result = self._create_result("İş-Zaman Çizelgesi")
        yasakli_ip = ["literatür tarama", "malzeme temini", "rapor yazımı", "makale yazımı", "hazırlık"]
        for ifade in yasakli_ip:
            if re.search(ifade, section_text, re.IGNORECASE):
                result.errors.append(f"'{ifade.title()}' gibi ifadeler tek başına bir iş paketi olarak kabul edilmez. İş paketleri projenin bilimsel/teknik adımları olmalıdır.")
        return result

    def validate_risk_yonetimi(self, section_text: str) -> ValidationResult:
        result = self._create_result("Risk Yönetimi")
        if "b planı" not in section_text.lower():
            result.warnings.append("Riskler için bir 'B Planı' belirtilmemiş. Her olası risk için alternatif bir çözüm yolu (B Planı) sunulmalıdır.")
        if len(section_text.split()) < 20:
             result.warnings.append("Risk Yönetimi bölümü çok kısa. Her iş paketi için potansiyel bir risk ve bu riske yönelik bir B planı tanımlanmalıdır.")
        return result

    def validate_yaygin_etki(self, section_text: str) -> ValidationResult:
        result = self._create_result("Yaygin Etki")
        if len(section_text.split()) < 15:
            result.warnings.append("Yaygın Etki bölümü yeterince detaylı değil. Proje çıktılarının (makale, bildiri, patent, sosyal katkı vb.) neler olabileceğini belirtmeniz beklenir.")
        if not any(keyword in section_text.lower() for keyword in ["makale", "bildiri", "konferans", "tez", "patent"]):
            result.suggestions.append("Akademik çıktılar (makale, bildiri vb.) beklenmiyorsa bile bunu 'proje kapsamında akademik bir yayın hedeflenmemektedir' şeklinde açıkça belirtmeniz faydalı olabilir.")
        return result

    def validate_kaynaklar(self, section_text: str) -> ValidationResult:
        result = self._create_result("Kaynaklar")
        kaynak_sayisi = len(re.findall(r'\[\d+\]', section_text))
        if kaynak_sayisi < 3:
            result.warnings.append(f"Kaynaklar listesi çok kısa ({kaynak_sayisi} adet). Özgün Değer bölümünde yapılan atıflarla tutarlı, yeterli sayıda kaynak listelenmelidir.")
        return result

    def validate_formatting(self, pdf_bytes: bytes, full_text: str) -> ValidationResult:
        result = self._create_result("Genel Format ve Biçim")
        if not PYMUPDF_AVAILABLE:
            result.warnings.append("Format analizi için `PyMuPDF` kütüphanesi kurulamamış.")
            return result
        try:
            with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
                if len(doc) > 20:
                    result.warnings.append(f"Belge toplam {len(doc)} sayfa. Ekler hariç 20 sayfa sınırı olduğunu unutmayın.")
                
                fonts = [s["font"].split('-')[0].split('+')[-1].lower() for p in doc for b in p.get_text("dict")["blocks"] if "lines" in b for l in b["lines"] for s in l["spans"]]
                sizes = [round(s["size"]) for p in doc for b in p.get_text("dict")["blocks"] if "lines" in b for l in b["lines"] for s in l["spans"]]
                
                if not sizes:
                    result.errors.append("Belgeden metin formatı bilgisi alınamadı. Belge taranmış bir resim olabilir veya metin katmanı içermiyor olabilir.")
                else:
                    dominant_size = Counter(sizes).most_common(1)[0][0]
                    dominant_font = Counter(fonts).most_common(1)[0][0]
                    if dominant_size != 9: result.warnings.append(f"Metnin genel punto boyutu '{dominant_size}' olarak algılandı. Tavsiye edilen '9' puntodur.")
                    if "arial" not in dominant_font and "helvetica" not in dominant_font: result.warnings.append(f"Metnin genel yazı tipi '{dominant_font}' olarak algılandı. Tavsiye edilen 'Arial'dir.")
                    result.suggestions.append(f"Algılanan dominant format: {dominant_font.title()}, {dominant_size} punto.")
        except Exception as e:
            result.errors.append(f"Format analizi sırasında bir hata oluştu: {e}")

        # Proje Tipi Tespiti
        project_type = self._detect_project_type(full_text)
        if project_type:
            result.suggestions.append(f"Projenizin '{project_type}' alanında olduğu tahmin edilmektedir. Değerlendirmelerinizin bu alanın dinamiklerine uygun olduğundan emin olun.")
        return result

    def validate_butce(self, section_text: str) -> ValidationResult:
        result = self._create_result("Bütçe")
        try:
            raw_numbers_tl = re.findall(r"([\d\.,]+)\s*(?:tl|₺)", section_text, re.IGNORECASE)
            numbers = [float(locale.atof(n.strip())) for n in raw_numbers_tl if n.strip()]
            total_match = re.search(r"toplam\s*[:\s]*([\d\.,]+)", section_text, re.IGNORECASE)
            total_budget = float(locale.atof(total_match.group(1).strip())) if total_match else (sum(numbers) if numbers else 0)
            if not total_budget:
                result.warnings.append("'TOPLAM' bütçe değeri bulunamadı veya '0' olarak hesaplandı.")
            elif total_budget > self.MAX_BUDGET:
                formatted_total = locale.currency(total_budget, grouping=True)
                formatted_max = locale.currency(self.MAX_BUDGET, grouping=True)
                result.errors.append(f"Toplam talep ({formatted_total}) program limiti olan {formatted_max}'yi aşıyor.")
        except (ValueError, locale.Error) as e:
            result.warnings.append(f"Bütçe tablosundaki sayılar okunamadı. Formatı kontrol edin. Hata: {e}")
        for item in self.BANNED_BUDGET_ITEMS:
            if re.search(r'\b' + re.escape(item) + r'\b', section_text, re.IGNORECASE):
                result.warnings.append(f"Bütçede '{item.title()}' algılandı. Genel amaçlı demirbaşlar genellikle desteklenmez.")
        return result

    def _detect_project_type(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        scores = {"Fen/Mühendislik": 0, "Sağlık Bilimleri": 0, "Sosyal Bilimler": 0}
        scores["Fen/Mühendislik"] += sum(text_lower.count(k) for k in ["dft", "vasp", "simülasyon", "deney", "matlab", "algoritma", "yazılım", "prototip", "malzeme", "kimyasal", "teori"])
        scores["Sağlık Bilimleri"] += sum(text_lower.count(k) for k in ["hasta", "hücre", "klinik", "tedavi", "genetik", "biyolojik", "ilaç", "sağlık", "prevalans"])
        scores["Sosyal Bilimler"] += sum(text_lower.count(k) for k in ["anket", "katılımcı", "nitel", "nicel", "görüşme", "sosyal", "ekonomik", "algı", "tutum", "spss"])
        if sum(scores.values()) < 5: return None
        return max(scores, key=scores.get)

    def validate_document(self, pdf_bytes: bytes) -> Optional[Dict[str, ValidationResult]]:
        try:
            full_text = self.extract_text_from_pdf_bytes(pdf_bytes)
            if not full_text:
                st.error("PDF dosyasından metin alınamadı. Dosyanın bozuk olmadığını veya metin tabanlı olduğunu kontrol edin.")
                return None

            sections = self.parse_document_sections(full_text)
            
            # Doğrulama fonksiyonlarını tanımla
            validation_methods = {
                "genel_bilgiler": self.validate_genel_bilgiler, "ozet": self.validate_ozet, "ozgun_deger": self.validate_ozgun_deger,
                "amac_ve_hedefler": self.validate_amac_ve_hedefler, "yontem": self.validate_yontem, "is_zaman_cizelgesi": self.validate_is_zaman_cizelgesi,
                "risk_yonetimi": self.validate_risk_yonetimi, "yaygin_etki": self.validate_yaygin_etki, "butce": self.validate_butce, "kaynaklar": self.validate_kaynaklar
            }
            results = {}

            # Önce Genel Format'ı kontrol et
            results["format"] = self.validate_formatting(pdf_bytes, full_text)

            # Her bölüm için ilgili doğrulama fonksiyonunu çalıştır
            for section_key, method in validation_methods.items():
                section_text = sections.get(section_key)
                if section_key in self.REQUIRED_SECTIONS and not section_text:
                    pattern_str = self.MAIN_PATTERNS.get(section_key, "Bilinmeyen Desen")
                    results[section_key] = self._create_result(section_key)
                    results[section_key].errors.append(f"Bu zorunlu bölüm belgede bulunamadı veya başlığı ('{pattern_str}') tanınamadı.")
                elif section_text:
                    results[section_key] = method(section_text)
            
            return results
        except Exception:
            st.error("Belge analizi sırasında kritik bir hata oluştu."); st.code(traceback.format_exc()); return None

# ==============================================================================
# STREAMLIT ARAYÜZÜ (BAŞLIK STİLİ GÜNCELLENDİ)
# ==============================================================================
def main():
    st.set_page_config(page_title="TÜBİTAK Proje Ön Değerlendiricisi", layout="wide", initial_sidebar_state="collapsed", page_icon="🚀")

    video_base64 = load_local_file_as_base64('background.mp4')
    logo_path = 'logo.png' 

    # Rocket cursor SVG (emoji-based, base64 not needed for SVG text)
    rocket_cursor = "url('data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"32\" height=\"32\" style=\"font-size:24px;\"><text y=\"24\">🚀</text></svg>'), auto"

    main_styles = f"""
        <style>
            #bg-video {{ position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; object-fit: cover; z-index: -2; opacity: 0.4; }}
            .stApp {{ background: linear-gradient(135deg, rgba(15, 20, 35, 0.85) 0%, rgba(25, 35, 65, 0.85) 100%); }}
            [data-testid="stAppViewContainer"] > .main {{ background: rgba(0, 0, 0, 0); backdrop-filter: blur(2px); }}
            html, body, .stApp, .stApp div, .stApp button, .stApp input, .stApp textarea {{ cursor: {rocket_cursor} !important; }}
            /* DÜZELTME: Başlıktaki parlama efekti kaldırıldı, sadece renk ve font ayarlandı */
            .main-title {{
                font-size: 3.2em; font-weight: 800; text-align: center; margin-bottom: 20px;
                color: #FFD700; /* Sadece altın rengi */
            }}
            .sub-title {{ font-size: 1.4em; color: #E8F4FD; text-align: center; margin-bottom: 40px; text-shadow: 0 2px 4px rgba(0, 0, 0, 0.5); font-weight: 300; }}
            .column-header {{ font-size: 1.8em; font-weight: 700; color: #FFFFFF; padding: 15px 0; border-bottom: 3px solid rgba(255, 215, 0, 0.8); margin-bottom: 25px; text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3); background: linear-gradient(90deg, rgba(255, 215, 0, 0.1) 0%, transparent 100%); padding-left: 15px; border-radius: 5px; }}
            [data-testid="stFileUploader"] > div > div {{ background: rgba(30, 45, 80, 0.9) !important; border: 2px dashed rgba(255, 215, 0, 0.6) !important; border-radius: 15px !important; padding: 30px !important; text-align: center !important; transition: all 0.3s ease !important; }}
            [data-testid="stFileUploader"] > div > div:hover {{ border-color: rgba(255, 215, 0, 1) !important; background: rgba(30, 45, 80, 1) !important; transform: translateY(-2px); box-shadow: 0 8px 25px rgba(255, 215, 0, 0.3); }}
            .stExpander {{ background: rgba(20, 30, 55, 0.95) !important; border: 1px solid rgba(255, 255, 255, 0.1) !important; border-radius: 12px !important; margin-bottom: 15px !important; backdrop-filter: blur(10px) !important; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3) !important; }}
            .stExpander > div:first-child > div > p {{ font-weight: 600 !important; color: #FFFFFF !important; font-size: 1.1em; }}
            [data-testid="stAlert"] {{ background: rgba(30, 45, 80, 0.9) !important; border-radius: 10px !important; color: #FFFFFF !important; border-left: 4px solid rgba(255, 215, 0, 0.8) !important; backdrop-filter: blur(5px) !important; }}
            .footer {{ position: fixed; left: 0; bottom: 0; width: 100%; background: linear-gradient(90deg, rgba(15, 20, 35, 0.95) 0%, rgba(25, 35, 65, 0.95) 100%); color: #B0BEC5; text-align: center; padding: 12px; font-size: 0.85em; z-index: 1000; border-top: 1px solid rgba(255, 215, 0, 0.3); backdrop-filter: blur(10px); }}
            .stMarkdown p, .stMarkdown li {{ color: #E8F4FD !important; }}
            .logo-container {{ display: flex; justify-content: center; margin-bottom: 30px; filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.3)); }}
        </style>
    """
    st.markdown(main_styles, unsafe_allow_html=True)

    if video_base64: st.markdown(f'<video autoplay loop muted id="bg-video"><source src="data:video/mp4;base64,{video_base64}" type="video/mp4"></video>', unsafe_allow_html=True)

    try:
        if os.path.exists(logo_path):
            st.markdown('<div class="logo-container">', unsafe_allow_html=True)
            st.image(logo_path, width=250)
            st.markdown('</div>', unsafe_allow_html=True)
    except Exception: pass

    st.markdown("<h1 class='main-title'>TÜBİTAK 2209-A Proje Ön Değerlendiricisi</h1>", unsafe_allow_html=True)
    st.markdown("<p class='sub-title'>✨ Proje önerinizi yükleyin, yapay zeka destekli mentorunuzla potansiyelini keşfedin ✨</p>", unsafe_allow_html=True)

    uploaded_file = st.file_uploader("Proje PDF dosyanızı yükleyin", type=["pdf"], label_visibility="collapsed")
    
    footer = "<div class='footer'>⚖️ <strong>Yasal Uyarı:</strong> Bu araç, resmi bir TÜBİTAK değerlendirmesi değildir. Yalnızca başvuru sahiplerine yardımcı olmak amacıyla hazırlanmış bir ön kontrol sistemidir.</div>"

    if uploaded_file is None:
        st.markdown("<div style='text-align: center; padding: 50px; background: rgba(30, 45, 80, 0.7); border-radius: 15px; margin: 30px 0; border: 2px dashed rgba(255, 215, 0, 0.5);'><h3 style='color: #FFD700; margin-bottom: 20px;'>🎯 Değerlendirmeye Başlayalım!</h3><p style='color: #E8F4FD; font-size: 1.1em;'>Proje PDF dosyanızı yukarıdaki alana sürükleyip bırakın veya dosya seçin.</p><p style='color: #B0BEC5; font-size: 0.9em; margin-top: 15px;'>💡 Desteklenen format: PDF</p></div>", unsafe_allow_html=True)
        st.markdown(footer, unsafe_allow_html=True)
        return

    col1, col2 = st.columns([5, 6])
    pdf_bytes = uploaded_file.getvalue()
    
    with col1:
        st.markdown("<p class='column-header'>📄 Belge Önizlemesi</p>", unsafe_allow_html=True)
        display_pdf_from_bytes(pdf_bytes)

    with col2:
        st.markdown("<p class='column-header'>🤖 AI Mentor Raporu</p>", unsafe_allow_html=True)
        validator = TubitakFormValidator()
        
        spinner_placeholder = st.empty()
        with spinner_placeholder.container():
            display_custom_spinner('🔍 Projeniz yapay zeka mentoru tarafından titizlikle analiz ediliyor...')
            results = validator.validate_document(pdf_bytes)
        
        spinner_placeholder.empty()

        if results:
            st.success("🎉 Analiz tamamlandı! Detaylı rapor hazır!")
            
            error_sections = sum(1 for r in results.values() if r.errors)
            warning_sections = sum(1 for r in results.values() if r.warnings)

            # YENİ ÖZELLİK: İndirme butonu
            report_data = format_results_for_download(results)
            st.download_button(
               label="📄 Raporu (.txt) İndir",
               data=report_data,
               file_name="TUBITAK_2209A_On_Degerlendirme_Raporu.txt",
               mime="text/plain"
            )

            st.markdown(
                f"""
                <div style='background: rgba(30, 45, 80, 0.9); padding: 20px; border-radius: 12px; margin: 20px 0; border-left: 4px solid #FFD700;'>
                    <h4 style='color: #FFD700; margin-bottom: 15px;'>📊 Analiz Özeti</h4>
                    <p style='color: #FFCDD2; margin: 5px 0;'>🚨 <strong>Kritik Hata Bulunan Bölüm Sayısı:</strong> {error_sections}</p>
                    <p style='color: #FFE0B2; margin: 5px 0;'>⚠️ <strong>Uyarı Bulunan Bölüm Sayısı:</strong> {warning_sections}</p>
                </div>
                """, 
                unsafe_allow_html=True
            )
            
            # Sonuçları sıralı göstermek için
            sorted_keys = list(results.keys())
            for key in sorted_keys:
                result = results[key]
                icon = "✅" if not result.errors and not result.warnings else ("🚨" if result.errors else "⚠️")
                is_expanded = bool(result.errors) or bool(result.warnings)
                
                with st.expander(f"{icon} {result.section_name}", expanded=is_expanded):
                    if not result.errors and not result.warnings:
                         st.success("🎯 Bu bölümde önemli bir sorun veya uyarı tespit edilmedi. Harika iş!")
                    
                    if result.errors:
                        st.error("**Kritik Hatalar (Mutlaka Düzeltilmeli):**")
                        for e in result.errors: st.write(f"  - {e}")
                    
                    if result.warnings:
                        st.warning("**Önemli Uyarılar (Düzeltilmesi Güçlü Tavsiye Edilir):**")
                        for w in result.warnings: st.write(f"  - {w}")
                    
                    if result.suggestions:
                        st.info("**İyileştirme Önerileri:**")
                        for s in result.suggestions: st.write(f"  - {s}")
        else:
            st.error("❌ Analiz sırasında beklenmeyen bir hata oluştu. Lütfen dosyanızı kontrol edip tekrar deneyin.")

    st.markdown(footer, unsafe_allow_html=True)

if __name__ == "__main__":
    if not PDFPLUMBER_AVAILABLE or not PYMUPDF_AVAILABLE:
        st.error("⚠️ Gerekli temel kütüphaneler eksik. Lütfen `pip install pdfplumber PyMuPDF` komutu ile yükleyin.")
    else:
        main()