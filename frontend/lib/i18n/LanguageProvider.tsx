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
  isAppLanguage,
  languageFromBrowser,
  localeForLanguage,
  readStoredLanguage,
  writeStoredLanguage,
  type AppLanguage,
} from "@/lib/i18n/languages";
import { translate, type MessageKey } from "@/lib/i18n/messages";

type LanguageContextValue = {
  language: AppLanguage;
  locale: string;
  setLanguage: (language: AppLanguage) => Promise<void>;
  t: (key: MessageKey) => string;
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
      readStoredLanguage() || languageFromBrowser(navigator.language);
    writeStoredLanguage(currentLanguage);
    if (typeof document !== "undefined") {
      document.documentElement.lang = currentLanguage;
    }
  }
  return currentLanguage;
}

function applyLanguage(next: AppLanguage) {
  currentLanguage = next;
  writeStoredLanguage(next);
  if (typeof document !== "undefined") {
    document.documentElement.lang = next;
  }
  emit();
}

export function LanguageProvider({
  userId,
  children,
}: {
  userId?: string | null;
  children: ReactNode;
}) {
  const language = useSyncExternalStore(
    subscribe,
    getSnapshot,
    getServerSnapshot,
  );

  useEffect(() => {
    if (!userId) {
      return;
    }
    let cancelled = false;
    void (async () => {
      const { data } = await supabase.auth.getUser();
      const fromMeta = data.user?.user_metadata?.language;
      const stored = readStoredLanguage();
      const next = stored || (isAppLanguage(fromMeta) ? fromMeta : language);
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
  }, [userId]);

  const setLanguage = useCallback(
    async (next: AppLanguage) => {
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
    [userId],
  );

  const value = useMemo<LanguageContextValue>(
    () => ({
      language,
      locale: localeForLanguage(language),
      setLanguage,
      t: (key: MessageKey) => translate(language, key),
    }),
    [language, setLanguage],
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
