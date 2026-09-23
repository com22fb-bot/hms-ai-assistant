export const APP_LANGUAGES = ["es", "en", "fr", "it", "pt"] as const;

export type AppLanguage = (typeof APP_LANGUAGES)[number];

export type LanguageOption = {
  code: AppLanguage;
  locale: string;
  nativeName: string;
  englishName: string;
};

export const LANGUAGE_OPTIONS: LanguageOption[] = [
  {
    code: "es",
    locale: "es-MX",
    nativeName: "Español",
    englishName: "Spanish",
  },
  {
    code: "en",
    locale: "en-US",
    nativeName: "English",
    englishName: "English",
  },
  {
    code: "fr",
    locale: "fr-FR",
    nativeName: "Français",
    englishName: "French",
  },
  {
    code: "it",
    locale: "it-IT",
    nativeName: "Italiano",
    englishName: "Italian",
  },
  {
    code: "pt",
    locale: "pt-BR",
    nativeName: "Português",
    englishName: "Portuguese",
  },
];

export const LANGUAGE_STORAGE_KEY = "donexto-language";

export function isAppLanguage(value: unknown): value is AppLanguage {
  return (
    typeof value === "string" &&
    (APP_LANGUAGES as readonly string[]).includes(value)
  );
}

export function localeForLanguage(language: AppLanguage): string {
  return (
    LANGUAGE_OPTIONS.find((option) => option.code === language)?.locale ||
    "es-MX"
  );
}

export function languageFromBrowser(
  raw?: string | null,
): AppLanguage {
  const value = (raw || "").toLowerCase();
  if (value.startsWith("es")) return "es";
  if (value.startsWith("en")) return "en";
  if (value.startsWith("fr")) return "fr";
  if (value.startsWith("it")) return "it";
  if (value.startsWith("pt")) return "pt";
  return "es";
}

export function readStoredLanguage(): AppLanguage | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    const stored = window.localStorage.getItem(LANGUAGE_STORAGE_KEY);
    return isAppLanguage(stored) ? stored : null;
  } catch {
    return null;
  }
}

export function writeStoredLanguage(language: AppLanguage): void {
  if (typeof window === "undefined") {
    return;
  }
  try {
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, language);
  } catch {
    /* ignore quota / private mode */
  }
}

/** Last language the login screen actually showed, including before redirect. */
const LOGIN_LANGUAGE_SESSION_KEY = "donexto-login-language";

let notedUiLanguage: AppLanguage | null = null;

export function coerceAppLanguage(value: unknown): AppLanguage | null {
  if (typeof value !== "string") {
    return null;
  }
  const base = value.trim().toLowerCase().split(/[-_]/)[0] ?? "";
  return isAppLanguage(base) ? base : null;
}

export function noteUiLanguage(language: AppLanguage): void {
  notedUiLanguage = language;
}

export function rememberLoginLanguage(language: AppLanguage): void {
  noteUiLanguage(language);
  writeStoredLanguage(language);
  if (typeof window === "undefined") {
    return;
  }
  try {
    window.sessionStorage.setItem(LOGIN_LANGUAGE_SESSION_KEY, language);
  } catch {
    /* ignore quota / private mode */
  }
}

export function readRememberedLoginLanguage(): AppLanguage | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    return coerceAppLanguage(
      window.sessionStorage.getItem(LOGIN_LANGUAGE_SESSION_KEY),
    );
  } catch {
    return null;
  }
}

/**
 * Language for the Donexto verification email.
 *
 * The login UI wins. Account metadata and the browser language are ignored:
 * after Microsoft/Yahoo signup, `user_metadata.language` can stay `en` while
 * the login strip is Spanish, and an English browser must not replace that
 * screen. With no UI choice at all, the login default is Spanish.
 */
export function chooseVerificationLanguage(input: {
  ui?: unknown;
  stored?: unknown;
  remembered?: unknown;
  metadata?: unknown;
  browser?: unknown;
}): AppLanguage {
  // Account metadata and Accept-Language/navigator must not choose the mail.
  void input.metadata;
  void input.browser;
  return (
    coerceAppLanguage(input.ui) ||
    coerceAppLanguage(input.stored) ||
    coerceAppLanguage(input.remembered) ||
    "es"
  );
}

export function languageForDonextoVerifyEmail(): AppLanguage {
  return chooseVerificationLanguage({
    ui: notedUiLanguage,
    stored: readStoredLanguage(),
    remembered: readRememberedLoginLanguage(),
  });
}
