"use client";

import { ChevronLeft, ChevronRight, Pause, Play } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";

import { useLanguage } from "@/lib/i18n/LanguageProvider";
import {
  GMAIL_GUIDE_INTERVAL_MS,
  GMAIL_GUIDE_STEPS,
  gmailGuideText,
  nextGuideStep,
  type GmailGuideKey,
} from "@/lib/i18n/gmailGuide";

import "./gmail-guide.css";

type Props = { email?: string };

/** Carrusel tipo video con pantallas de Google dibujadas en HTML/CSS (traducibles, sin datos reales). */
export function GmailAppPasswordGuide({ email }: Props) {
  const { language } = useLanguage();
  const t = (key: GmailGuideKey, vars?: Record<string, string | number>) => gmailGuideText(language, key, vars);
  const [step, setStep] = useState(0);
  const [playing, setPlaying] = useState(true);
  const [open, setOpen] = useState(true);
  const total = GMAIL_GUIDE_STEPS.length;
  const address = email?.trim() || "nombre@gmail.com";

  useEffect(() => {
    if (!playing) return;
    const timer = window.setTimeout(() => setStep((s) => nextGuideStep(s, 1, total)), GMAIL_GUIDE_INTERVAL_MS);
    return () => window.clearTimeout(timer);
  }, [playing, step, total]);

  const go = (delta: number) => {
    setPlaying(false);
    setStep((s) => nextGuideStep(s, delta, total));
  };

  return (
    <section className={open ? "dx-gguide" : "dx-gguide is-collapsed"} aria-label={t("title")}>
      <header className="dx-gguide__head">
        <strong>{t("title")}</strong>
        <button type="button" className="dx-gguide__toggle" onClick={() => setOpen((v) => !v)} aria-expanded={open}>
          {open ? t("hide") : t("show")}
        </button>
      </header>
      {open ? (
        <>
          <div className="dx-gguide__screen" aria-live="polite">
            <Mock step={step} t={t} address={address} />
          </div>
          <p className="dx-gguide__count">{t("stepOf", { n: step + 1, total })}</p>
          <p className="dx-gguide__caption">{t(GMAIL_GUIDE_STEPS[step])}</p>
          <div className="dx-gguide__controls">
            <button type="button" onClick={() => go(-1)} aria-label={t("prev")}><ChevronLeft size={18} /></button>
            <button type="button" onClick={() => setPlaying((p) => !p)} aria-label={playing ? t("pause") : t("play")}>
              {playing ? <Pause size={18} /> : <Play size={18} />}
            </button>
            <button type="button" onClick={() => go(1)} aria-label={t("next")}><ChevronRight size={18} /></button>
            <div className="dx-gguide__dots" role="tablist">
              {GMAIL_GUIDE_STEPS.map((key, index) => (
                <button
                  key={key}
                  type="button"
                  role="tab"
                  aria-selected={index === step}
                  aria-label={t("stepOf", { n: index + 1, total })}
                  className={index === step ? "is-active" : undefined}
                  onClick={() => {
                    setPlaying(false);
                    setStep(index);
                  }}
                />
              ))}
            </div>
          </div>
          <p className="dx-gguide__note">{t("sameAccount")}</p>
        </>
      ) : null}
    </section>
  );
}

function Browser({ url, children }: { url: string; children: ReactNode }) {
  return (
    <div className="dx-gm">
      <div className="dx-gm__bar">
        <span className="dx-gm__dots" aria-hidden="true"><i /><i /><i /></span>
        <span className="dx-gm__url">{url}</span>
      </div>
      <div className="dx-gm__body">{children}</div>
    </div>
  );
}

function Mock({ step, t, address }: { step: number; t: (k: GmailGuideKey) => string; address: string }) {
  const initial = address.charAt(0).toUpperCase();
  switch (step) {
    case 0:
      return (
        <Browser url="myaccount.google.com">
          <div className="dx-gm__account">
            <span className="dx-gm__brand">{t("mGoogleAccount")}</span>
            <span className="dx-gm__who dx-gm__hl"><b className="dx-gm__avatar">{initial}</b>{address}</span>
          </div>
          <ul className="dx-gm__nav"><li className="is-on">{t("mHome")}</li><li>{t("mSecurity")}</li></ul>
        </Browser>
      );
    case 1:
      return (
        <Browser url="myaccount.google.com/security">
          <ul className="dx-gm__nav"><li>{t("mHome")}</li><li className="is-on">{t("mSecurity")}</li></ul>
          <div className="dx-gm__row">
            <span>{t("mTwoStep")}<small>{t("mOff")}</small></span>
            <span className="dx-gm__btn dx-gm__hl">{t("mTurnOn")}</span>
          </div>
        </Browser>
      );
    case 2:
      return (
        <Browser url="myaccount.google.com/apppasswords">
          <span className="dx-gm__url-hl dx-gm__hl">myaccount.google.com/apppasswords</span>
          <h4 className="dx-gm__h">{t("mAppPasswords")}</h4>
        </Browser>
      );
    case 3:
      return (
        <Browser url="myaccount.google.com/apppasswords">
          <h4 className="dx-gm__h">{t("mAppPasswords")}</h4>
          <label className="dx-gm__field"><small>{t("mAppName")}</small><span className="dx-gm__input">Donexto</span></label>
          <span className="dx-gm__btn dx-gm__hl">{t("mCreate")}</span>
        </Browser>
      );
    case 4:
      return (
        <Browser url="myaccount.google.com/apppasswords">
          <h4 className="dx-gm__h">{t("mGenerated")}</h4>
          <span className="dx-gm__code dx-gm__hl">abcd efgh ijkl mnop</span>
          <span className="dx-gm__btn">{t("mDone")}</span>
        </Browser>
      );
    default:
      return (
        <Browser url="app.donexto.com">
          <label className="dx-gm__field"><small>{t("mEmail")}</small><span className="dx-gm__input">{address}</span></label>
          <label className="dx-gm__field"><small>{t("mPassword")}</small><span className="dx-gm__input">•••• •••• •••• ••••</span></label>
          <span className="dx-gm__btn dx-gm__btn--primary dx-gm__hl">{t("mConnect")}</span>
        </Browser>
      );
  }
}
