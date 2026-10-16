"use client";

import { AlertTriangle, RefreshCw, X } from "lucide-react";
import { useEffect, useState } from "react";

import { useLanguage } from "@/lib/i18n/LanguageProvider";
import { oauthReturnReason, oauthReturnText, type OAuthReturnReason } from "@/lib/i18n/oauthReturn";

/** Lee ?donexto=oauth_error&provider=google&reason=… una sola vez (antes de que otro efecto limpie la URL). */
function readGoogleReturn(): OAuthReturnReason | null {
  if (typeof window === "undefined") return null;
  const params = new URLSearchParams(window.location.search);
  if (params.get("donexto") !== "oauth_error" || params.get("provider") !== "google") return null;
  return oauthReturnReason(params.get("reason"));
}

export function OAuthReturnNotice({ onRetry }: { onRetry?: () => void }) {
  const { language } = useLanguage();
  const [reason, setReason] = useState<OAuthReturnReason | null>(null);

  useEffect(() => {
    const found = readGoogleReturn();
    if (!found) return;
    const url = new URL(window.location.href);
    for (const key of ["donexto", "provider", "reason"]) url.searchParams.delete(key);
    window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}` || "/");
    // Sin cancelar: en StrictMode la segunda pasada ya no encuentra los parámetros.
    window.requestAnimationFrame(() => setReason(found));
  }, []);

  if (!reason) return null;
  const T = (key: Parameters<typeof oauthReturnText>[1]) => oauthReturnText(language, key);

  return (
    <div className="dx-oauth-return" role="alertdialog" aria-modal="true" aria-labelledby="dx-oauth-return-title">
      <section>
        <button type="button" className="dx-oauth-return__close" aria-label={T("close")} onClick={() => setReason(null)}>
          <X size={20} />
        </button>
        <AlertTriangle size={30} aria-hidden="true" />
        <h2 id="dx-oauth-return-title">{T("title")}</h2>
        <p>{T(reason)}</p>
        <button
          type="button"
          className="dx-oauth-return__retry"
          onClick={() => {
            setReason(null);
            onRetry?.();
          }}
        >
          <RefreshCw size={18} /> {T("retry")}
        </button>
      </section>
    </div>
  );
}
