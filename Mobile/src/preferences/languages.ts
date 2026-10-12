export const LANGUAGES = [
  { code: "en", name: "English", native: "English" },
  { code: "zh", name: "Mandarin Chinese", native: "简体中文" },
  { code: "hi", name: "Hindi", native: "हिन्दी" },
  { code: "es", name: "Spanish", native: "Español" },
  { code: "fr", name: "French", native: "Français" },
  { code: "ar", name: "Arabic", native: "العربية" },
  { code: "bn", name: "Bengali", native: "বাংলা" },
  { code: "pt", name: "Portuguese", native: "Português" },
  { code: "ru", name: "Russian", native: "Русский" },
  { code: "ur", name: "Urdu", native: "اردو" },
  { code: "id", name: "Indonesian", native: "Bahasa Indonesia" },
  { code: "de", name: "German", native: "Deutsch" },
  { code: "ja", name: "Japanese", native: "日本語" },
  { code: "tr", name: "Turkish", native: "Türkçe" },
  { code: "vi", name: "Vietnamese", native: "Tiếng Việt" },
  { code: "ko", name: "Korean", native: "한국어" },
  { code: "ta", name: "Tamil", native: "தமிழ்" },
  { code: "te", name: "Telugu", native: "తెలుగు" },
  { code: "mr", name: "Marathi", native: "मराठी" },
  { code: "pa", name: "Punjabi", native: "ਪੰਜਾਬੀ" },
  { code: "it", name: "Italian", native: "Italiano" },
] as const;
export type Language = typeof LANGUAGES[number]["code"];
export type Label = "settings" | "personal" | "language" | "currency" | "preferences" | "light" | "dark" | "home" | "history" | "chat" | "add" | "insights" | "back" | "transactions";
const keys: Label[] = ["settings", "personal", "language", "currency", "preferences", "light", "dark", "home", "history", "chat", "add", "insights", "back"];
const translations: Record<Language, string[]> = {
  en: ["Settings", "Personal Details", "Language", "Currency", "Preferences", "Light mode", "Dark mode", "Home", "History", "AI Chat", "Add", "Insights", "Back"],
  zh: ["设置", "个人信息", "语言", "货币", "偏好设置", "浅色模式", "深色模式", "首页", "记录", "AI 聊天", "添加", "分析", "返回"],
  hi: ["सेटिंग्स", "व्यक्तिगत विवरण", "भाषा", "मुद्रा", "प्राथमिकताएँ", "लाइट मोड", "डार्क मोड", "होम", "इतिहास", "AI चैट", "जोड़ें", "विश्लेषण", "वापस"],
  es: ["Ajustes", "Datos personales", "Idioma", "Moneda", "Preferencias", "Modo claro", "Modo oscuro", "Inicio", "Historial", "Chat IA", "Añadir", "Análisis", "Atrás"],
  fr: ["Paramètres", "Informations personnelles", "Langue", "Devise", "Préférences", "Mode clair", "Mode sombre", "Accueil", "Historique", "Chat IA", "Ajouter", "Analyses", "Retour"],
  ar: ["الإعدادات", "البيانات الشخصية", "اللغة", "العملة", "التفضيلات", "الوضع الفاتح", "الوضع الداكن", "الرئيسية", "السجل", "دردشة الذكاء الاصطناعي", "إضافة", "التحليلات", "رجوع"],
  bn: ["সেটিংস", "ব্যক্তিগত তথ্য", "ভাষা", "মুদ্রা", "পছন্দসমূহ", "লাইট মোড", "ডার্ক মোড", "হোম", "ইতিহাস", "AI চ্যাট", "যোগ করুন", "বিশ্লেষণ", "ফিরে যান"],
  pt: ["Configurações", "Dados pessoais", "Idioma", "Moeda", "Preferências", "Modo claro", "Modo escuro", "Início", "Histórico", "Chat IA", "Adicionar", "Análises", "Voltar"],
  ru: ["Настройки", "Личные данные", "Язык", "Валюта", "Предпочтения", "Светлая тема", "Тёмная тема", "Главная", "История", "Чат ИИ", "Добавить", "Аналитика", "Назад"],
  ur: ["ترتیبات", "ذاتی تفصیلات", "زبان", "کرنسی", "ترجیحات", "لائٹ موڈ", "ڈارک موڈ", "ہوم", "تاریخ", "AI چیٹ", "شامل کریں", "تجزیہ", "واپس"],
  id: ["Pengaturan", "Data pribadi", "Bahasa", "Mata uang", "Preferensi", "Mode terang", "Mode gelap", "Beranda", "Riwayat", "Chat AI", "Tambah", "Analisis", "Kembali"],
  de: ["Einstellungen", "Persönliche Daten", "Sprache", "Währung", "Präferenzen", "Heller Modus", "Dunkler Modus", "Start", "Verlauf", "KI-Chat", "Hinzufügen", "Analysen", "Zurück"],
  ja: ["設定", "個人情報", "言語", "通貨", "環境設定", "ライトモード", "ダークモード", "ホーム", "履歴", "AIチャット", "追加", "分析", "戻る"],
  tr: ["Ayarlar", "Kişisel bilgiler", "Dil", "Para birimi", "Tercihler", "Açık mod", "Koyu mod", "Ana sayfa", "Geçmiş", "AI sohbet", "Ekle", "Analizler", "Geri"],
  vi: ["Cài đặt", "Thông tin cá nhân", "Ngôn ngữ", "Tiền tệ", "Tùy chọn", "Chế độ sáng", "Chế độ tối", "Trang chủ", "Lịch sử", "Trò chuyện AI", "Thêm", "Phân tích", "Quay lại"],
  ko: ["설정", "개인 정보", "언어", "통화", "환경설정", "라이트 모드", "다크 모드", "홈", "기록", "AI 채팅", "추가", "분석", "뒤로"],
  ta: ["அமைப்புகள்", "தனிப்பட்ட விவரங்கள்", "மொழி", "நாணயம்", "விருப்பங்கள்", "ஒளி முறை", "இருள் முறை", "முகப்பு", "வரலாறு", "AI அரட்டை", "சேர்", "பகுப்பாய்வு", "பின்செல்"],
  te: ["సెట్టింగ్‌లు", "వ్యక్తిగత వివరాలు", "భాష", "కరెన్సీ", "ప్రాధాన్యతలు", "లైట్ మోడ్", "డార్క్ మోడ్", "హోమ్", "చరిత్ర", "AI చాట్", "జోడించు", "విశ్లేషణ", "వెనుకకు"],
  mr: ["सेटिंग्ज", "वैयक्तिक तपशील", "भाषा", "चलन", "प्राधान्ये", "लाइट मोड", "डार्क मोड", "मुख्यपृष्ठ", "इतिहास", "AI चॅट", "जोडा", "विश्लेषण", "मागे"],
  pa: ["ਸੈਟਿੰਗਾਂ", "ਨਿੱਜੀ ਵੇਰਵੇ", "ਭਾਸ਼ਾ", "ਮੁਦਰਾ", "ਤਰਜੀਹਾਂ", "ਲਾਈਟ ਮੋਡ", "ਡਾਰਕ ਮੋਡ", "ਮੁੱਖ ਪੰਨਾ", "ਇਤਿਹਾਸ", "AI ਚੈਟ", "ਸ਼ਾਮਲ ਕਰੋ", "ਵਿਸ਼ਲੇਸ਼ਣ", "ਪਿੱਛੇ"],
  it: ["Impostazioni", "Dati personali", "Lingua", "Valuta", "Preferenze", "Modalità chiara", "Modalità scura", "Home", "Cronologia", "Chat IA", "Aggiungi", "Analisi", "Indietro"],
};
const transactionsLabels: Record<Language, string> = {
  en: "Transactions", zh: "交易", hi: "लेन-देन", es: "Transacciones", fr: "Transactions",
  ar: "المعاملات", bn: "লেনদেন", pt: "Transações", ru: "Транзакции", ur: "لین دین",
  id: "Transaksi", de: "Transaktionen", ja: "取引", tr: "İşlemler", vi: "Giao dịch",
  ko: "거래", ta: "பரிவர்த்தனைகள்", te: "లావాదేవీలు", mr: "व्यवहार", pa: "ਲੈਣ-ਦੇਣ", it: "Transazioni",
};
export function translate(language: Language, key: Label) {
  if (key === "transactions") return transactionsLabels[language];
  return translations[language][keys.indexOf(key)] ?? translations.en[keys.indexOf(key)];
}
