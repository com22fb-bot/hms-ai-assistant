"use client";

import { Check, Globe, Languages, LogOut, X } from "lucide-react";

import { LANGUAGE_OPTIONS } from "@/lib/i18n/languages";
import { useLanguage } from "@/lib/i18n/LanguageProvider";

import "./user-settings.css";

export function LanguageStrip({ className }: { className?: string }) {
  const { language, setLanguage, t } = useLanguage();

  return (
    <div
      className={["dx-lang-strip", className].filter(Boolean).join(" ")}
      role="group"
      aria-label={t("language")}
    >
      {LANGUAGE_OPTIONS.map((option) => (
        <button
          key={option.code}
          type="button"
          className={
            option.code === language
              ? "dx-lang-strip__btn is-selected"
              : "dx-lang-strip__btn"
          }
          onClick={() => {
            void setLanguage(option.code);
          }}
        >
          {option.nativeName}
        </button>
      ))}
    </div>
  );
}

type UserSettingsPanelProps = {
  email: string;
  name: string;
  onClose: () => void;
  onSignOut: () => void;
};

export function UserSettingsPanel({
  email,
  name,
  onClose,
  onSignOut,
}: UserSettingsPanelProps) {
  const { language, setLanguage, t } = useLanguage();

  return (
    <div className="dx-settings-overlay" role="dialog" aria-modal="true">
      <section className="dx-settings-card">
        <header className="dx-settings-header">
          <div>
            <span>{t("settingsKicker")}</span>
            <h2>{t("settingsTitle")}</h2>
          </div>
          <button
            type="button"
            className="dx-settings-icon-btn"
            onClick={onClose}
            aria-label={t("settingsClose")}
          >
            <X size={20} />
          </button>
        </header>

        <div className="dx-settings-account">
          <Globe size={18} aria-hidden />
          <div>
            <strong>{name}</strong>
            <small>{email}</small>
          </div>
        </div>

        <section className="dx-settings-language" aria-labelledby="dx-language-title">
          <div className="dx-settings-language__intro">
            <Languages size={18} aria-hidden />
            <div>
              <h3 id="dx-language-title">{t("settingsLanguage")}</h3>
              <p>{t("settingsLanguageHelp")}</p>
            </div>
          </div>

          <div className="dx-settings-language__grid" role="listbox" aria-label={t("language")}>
            {LANGUAGE_OPTIONS.map((option) => {
              const selected = option.code === language;
              return (
                <button
                  key={option.code}
                  type="button"
                  role="option"
                  aria-selected={selected}
                  className={
                    selected
                      ? "dx-settings-lang is-selected"
                      : "dx-settings-lang"
                  }
                  onClick={() => {
                    void setLanguage(option.code);
                  }}
                >
                  <span className="dx-settings-lang__code">
                    {option.code.toUpperCase()}
                  </span>
                  <span className="dx-settings-lang__names">
                    <strong>{option.nativeName}</strong>
                    <small>{option.englishName}</small>
                  </span>
                  {selected ? (
                    <Check size={18} aria-hidden className="dx-settings-lang__check" />
                  ) : null}
                </button>
              );
            })}
          </div>
        </section>

        <button
          type="button"
          className="dx-settings-signout"
          onClick={onSignOut}
        >
          <LogOut size={17} />
          {t("profileSignOut")}
        </button>
      </section>
    </div>
  );
}
