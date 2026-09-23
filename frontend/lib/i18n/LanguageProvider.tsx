"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useSyncExternalStore,
  type ReactNode,
} from "react";

import { supabase } from "@/lib/supabase";
import {
  languageFromBrowser,
  localeForLanguage,
  noteUiLanguage,
  readRememberedLoginLanguage,
  readStoredLanguage,
  rememberLoginLanguage,
  type AppLanguage,
} from "@/lib/i18n/languages";
import { translate, type MessageKey } from "@/lib/i18n/messages";

type LanguageContextValue = {
  language: AppLanguage;
  locale: string;
  setLanguage: (language: AppLanguage) => Promise<void>;
  t: (key: MessageKey) => string;
  /** /admin locks Spanish and hides the language switcher. */
  languageLocked: boolean;
};

const LanguageContext = createContext<LanguageContextValue | null>(null);

const listeners = new Set<() => void>();
let currentLanguage: AppLanguage = "es";
let hydrated = false;

function emit() {
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function getServerSnapshot(): AppLanguage {
  return "es";
}

function getSnapshot(): AppLanguage {
  if (!hydrated) {
    hydrated = true;
    currentLanguage =
      readStoredLanguage() ||
      readRememberedLoginLanguage() ||
      languageFromBrowser(navigator.language);
    noteUiLanguage(currentLanguage);
    rememberLoginLanguage(currentLanguage);
    if (typeof document !== "undefined") {
      document.documentElement.lang = currentLanguage;
    }
  }
  return currentLanguage;
}

function applyLanguage(next: AppLanguage) {
  currentLanguage = next;
  rememberLoginLanguage(next);
  if (typeof document !== "undefined") {
    document.documentElement.lang = next;
  }
  emit();
}

export function LanguageProvider({
  userId,
  lockedLanguage,
  children,
}: {
  userId?: string | null;
  /** Fixed copy for a route. Does not write the visitor's stored language. */
  lockedLanguage?: AppLanguage;
  children: ReactNode;
}) {
  const storedLanguage = useSyncExternalStore(
    subscribe,
    getSnapshot,
    getServerSnapshot,
  );
  const language = lockedLanguage ?? storedLanguage;

  useEffect(() => {
    if (!lockedLanguage || typeof document === "undefined") {
      return;
    }
    const root = document.documentElement;
    const previous = root.lang;
    root.lang = lockedLanguage;
    return () => {
      root.lang = previous;
    };
  }, [lockedLanguage]);

  useEffect(() => {
    if (lockedLanguage || !userId) {
      return;
    }
    let cancelled = false;
    void (async () => {
      // Keep the login screen language. Do not copy user_metadata.language
      // over it: that field can stay "en" after a Spanish login.
      const stored = readStoredLanguage();
      const next = stored || readRememberedLoginLanguage() || language;
      if (!cancelled) {
        applyLanguage(next);
        try {
          await supabase.auth.updateUser({
            data: { language: next, locale: localeForLanguage(next) },
          });
          await supabase
            .from("profiles")
            .update({ language: next, locale: localeForLanguage(next) })
            .eq("id", userId);
        } catch {
          /* La preferencia local sigue activa si el perfil no se puede actualizar. */
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [userId, lockedLanguage]);

  const setLanguage = useCallback(
    async (next: AppLanguage) => {
      if (lockedLanguage) {
        return;
      }
      applyLanguage(next);
      const locale = localeForLanguage(next);
      try {
        await supabase.auth.updateUser({
          data: { language: next, locale },
        });
      } catch {
        /* local preference still applies */
      }
      if (!userId) {
        return;
      }
      try {
        await supabase
          .from("profiles")
          .update({ language: next, locale })
          .eq("id", userId);
      } catch {
        /* RLS may be select-only; auth metadata is enough */
      }
    },
    [userId, lockedLanguage],
  );

  const value = useMemo<LanguageContextValue>(
    () => ({
      language,
      locale: localeForLanguage(language),
      setLanguage,
      t: (key: MessageKey) => translate(language, key),
      languageLocked: lockedLanguage != null,
    }),
    [language, lockedLanguage, setLanguage],
  );

  return (
    <LanguageContext.Provider value={value}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage(): LanguageContextValue {
  const value = useContext(LanguageContext);
  if (!value) {
    throw new Error("useLanguage must be used within LanguageProvider");
  }
  return value;
}

export function useOptionalLanguage(): LanguageContextValue | null {
  return useContext(LanguageContext);
}
