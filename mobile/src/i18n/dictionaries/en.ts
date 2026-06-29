import type { PluralForms } from "../translate";

/** English dictionary — source of truth. `keyof typeof en` = `TranslationKey`. */
export const en = {
  // Common
  "common.appName": "Seed Bank",
  "common.tagline": "Check your seeds in seconds",
  "common.retry": "Try again",
  "common.cancel": "Cancel",
  "common.back": "Back",
  "common.loading": "Loading…",
  "common.ok": "OK",

  // Auth
  "auth.signIn": "Sign in",
  "auth.title": "Welcome back",
  "auth.subtitle": "Sign in to check your seeds",
  "auth.email": "Email",
  "auth.emailPlaceholder": "you@farm.org",
  "auth.password": "Password",
  "auth.fillFields": "Enter your email and password.",
  "auth.failed": "Sign-in failed. Check your details and try again.",
  "auth.serverHint": "Tip: set the server address in Settings if you can't sign in.",

  // Tabs
  "tab.capture": "Check",
  "tab.realtime": "Live",
  "tab.history": "History",
  "tab.settings": "Settings",

  // Realtime (live video analysis)
  "realtime.live": "Live · analyzing",
  "realtime.idle": "Paused",
  "realtime.start": "Start live",
  "realtime.stop": "Stop",
  "realtime.frames": "Frames",
  "realtime.frameError": "A frame couldn't be analyzed. Still going…",

  // Camera
  "camera.permTitle": "Camera access needed",
  "camera.permMessage": "Allow camera access to photograph your seeds.",
  "camera.grant": "Allow camera",
  "camera.hint": "Point at the seeds and tap the button",
  "camera.reviewTitle": "Review photos",
  "camera.reviewSubtitle": "Add more or send them for analysis.",
  "camera.addMore": "Add more",
  "camera.analyzeNow": "Check seeds",
  "camera.clear": "Clear",
  "camera.uploading": "Uploading…",
  "camera.uploadError": "Upload failed. Please try again.",
  "camera.noPhotos": "Take a photo to get started.",

  // Result
  "result.title": "Result",
  "result.analyzingTitle": "Analyzing your seeds…",
  "result.analyzingHint": "Detecting seeds and grading quality. This updates automatically.",
  "result.seeds": "Seeds",
  "result.good": "Good",
  "result.bad": "Bad",
  "result.goodRate": "Good rate",
  "result.meanConfidence": "Mean confidence",
  "result.viewHistory": "View history",
  "result.newScan": "New check",
  "result.failedTitle": "Analysis failed",
  "result.failedHint": "Something went wrong while analyzing. Please try again.",
  "result.captured": "Captured",

  // History
  "history.title": "Scan history",
  "history.empty": "No scans yet",
  "history.emptyHint": "Your seed checks will appear here.",
  "history.tapHint": "Tap a scan to see its results.",

  // Settings
  "settings.title": "Settings",
  "settings.language": "Language",
  "settings.appearance": "Appearance",
  "settings.themeSystem": "System",
  "settings.themeLight": "Light",
  "settings.themeDark": "Dark",
  "settings.account": "Account",
  "settings.signedInAs": "Signed in as",
  "settings.signOut": "Sign out",
  "settings.server": "Server address",
  "settings.about": "About",
  "settings.version": "Version",
  "settings.rtlNote": "The app will restart to apply the new layout direction.",

  // Status
  "status.pending": "Queued",
  "status.running": "Running",
  "status.succeeded": "Done",
  "status.failed": "Failed",
  "status.partial": "Partial",

  // Errors
  "error.network": "Can't reach the server. Check your connection.",
  "error.generic": "Something went wrong.",
};

export type TranslationKey = keyof typeof en;

export const enPlurals = {
  photos: { one: "{count} photo", other: "{count} photos" },
  seeds: { one: "{count} seed", other: "{count} seeds" },
} satisfies Record<string, PluralForms>;

export type PluralKey = keyof typeof enPlurals;
