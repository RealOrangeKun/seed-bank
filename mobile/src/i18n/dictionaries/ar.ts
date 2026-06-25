import type { PluralForms } from "../translate";
import type { PluralKey, TranslationKey } from "./en";

/** Arabic (Egyptian-friendly MSA). Typed as a complete map of every key. */
export const ar: Record<TranslationKey, string> = {
  // Common
  "common.appName": "بنك البذور",
  "common.tagline": "افحص بذورك في ثوانٍ",
  "common.retry": "حاول مرة أخرى",
  "common.cancel": "إلغاء",
  "common.back": "رجوع",
  "common.loading": "جارٍ التحميل…",
  "common.ok": "حسنًا",

  // Auth
  "auth.signIn": "تسجيل الدخول",
  "auth.title": "مرحبًا بعودتك",
  "auth.subtitle": "سجّل الدخول لفحص بذورك",
  "auth.email": "البريد الإلكتروني",
  "auth.emailPlaceholder": "you@farm.org",
  "auth.password": "كلمة المرور",
  "auth.fillFields": "أدخل بريدك الإلكتروني وكلمة المرور.",
  "auth.failed": "فشل تسجيل الدخول. تحقّق من بياناتك وحاول مرة أخرى.",
  "auth.serverHint": "تلميح: اضبط عنوان الخادم من الإعدادات إذا تعذّر الدخول.",

  // Tabs
  "tab.home": "الرئيسية",
  "tab.capture": "فحص",
  "tab.history": "السجل",
  "tab.settings": "الإعدادات",

  // Home
  "home.greeting": "مرحبًا بعودتك",
  "home.statScans": "إجمالي الفحوصات",
  "home.statPhotos": "الصور المفحوصة",
  "home.statDone": "المكتملة",
  "home.recent": "أحدث الفحوصات",
  "home.viewAll": "عرض الكل",
  "home.emptyHint": "اضغط «افحص البذور» لتحليل أول دفعة لك.",

  // Camera
  "camera.permTitle": "نحتاج إذن الكاميرا",
  "camera.permMessage": "اسمح بالوصول إلى الكاميرا لتصوير بذورك.",
  "camera.grant": "السماح بالكاميرا",
  "camera.hint": "وجّه الكاميرا نحو البذور واضغط الزر",
  "camera.reviewTitle": "مراجعة الصور",
  "camera.reviewSubtitle": "أضف المزيد أو أرسلها للتحليل.",
  "camera.addMore": "أضف المزيد",
  "camera.analyzeNow": "افحص البذور",
  "camera.clear": "مسح",
  "camera.uploading": "جارٍ الرفع…",
  "camera.uploadError": "فشل الرفع. حاول مرة أخرى.",
  "camera.noPhotos": "التقط صورة للبدء.",
  "camera.torch": "الفلاش",
  "camera.flip": "تبديل الكاميرا",
  "camera.clearAll": "مسح الكل",

  // Result
  "result.title": "النتيجة",
  "result.analyzingTitle": "جارٍ تحليل بذورك…",
  "result.analyzingHint": "اكتشاف البذور وتقييم الجودة. يُحدَّث تلقائيًا.",
  "result.seeds": "البذور",
  "result.good": "جيدة",
  "result.bad": "رديئة",
  "result.goodRate": "نسبة الجيد",
  "result.meanConfidence": "متوسط الثقة",
  "result.viewHistory": "عرض السجل",
  "result.newScan": "فحص جديد",
  "result.failedTitle": "فشل التحليل",
  "result.failedHint": "حدث خطأ أثناء التحليل. حاول مرة أخرى.",
  "result.captured": "وقت الالتقاط",

  // History
  "history.title": "سجل الفحوصات",
  "history.empty": "لا توجد فحوصات بعد",
  "history.emptyHint": "ستظهر فحوصاتك هنا.",
  "history.tapHint": "اضغط على فحص لعرض نتائجه.",
  "history.loadError": "تعذّر تحميل فحوصاتك.",

  // Settings
  "settings.title": "الإعدادات",
  "settings.language": "اللغة",
  "settings.appearance": "المظهر",
  "settings.themeSystem": "النظام",
  "settings.themeLight": "فاتح",
  "settings.themeDark": "داكن",
  "settings.account": "الحساب",
  "settings.signedInAs": "مسجّل الدخول باسم",
  "settings.signOut": "تسجيل الخروج",
  "settings.server": "عنوان الخادم",
  "settings.about": "حول التطبيق",
  "settings.version": "الإصدار",
  "settings.rtlNote": "سيُعاد تشغيل التطبيق لتطبيق اتجاه التخطيط الجديد.",

  // Status
  "status.pending": "في الانتظار",
  "status.running": "جارٍ التنفيذ",
  "status.succeeded": "اكتمل",
  "status.failed": "فشل",
  "status.partial": "جزئي",

  // Errors
  "error.network": "تعذّر الوصول إلى الخادم. تحقّق من اتصالك.",
  "error.generic": "حدث خطأ ما.",
};

export const arPlurals: Record<PluralKey, PluralForms> = {
  photos: {
    zero: "لا صور",
    one: "صورة واحدة",
    two: "صورتان",
    few: "{count} صور",
    many: "{count} صورة",
    other: "{count} صورة",
  },
  seeds: {
    zero: "لا بذور",
    one: "بذرة واحدة",
    two: "بذرتان",
    few: "{count} بذور",
    many: "{count} بذرة",
    other: "{count} بذرة",
  },
};
