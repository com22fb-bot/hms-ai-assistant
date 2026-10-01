"use client";

import type { ReactNode } from "react";
import {
  Bell,
  Captions,
  Contrast,
  Eye,
  Globe,
  Keyboard,
  Lock,
  Mail,
  Palette,
  Pause,
  RotateCcw,
  Shield,
  Type,
  Volume2,
  Waves,
} from "lucide-react";

import { LANGUAGE_OPTIONS, type AppLanguage } from "@/lib/i18n/languages";
import type { NxKey } from "@/lib/nucleo/copy";
import type { NucleoPrefs, NucleoTheme, AlertRuleKind } from "@/lib/nucleo/prefs";
import { NUCLEO_THEMES } from "@/lib/nucleo/prefs";
import type { PushDevice } from "@/lib/nucleo/pushClient";

import { Nexto } from "@/components/nucleo/Nexto";

type T = (key: NxKey, vars?: Record<string, string | number>) => string;

const THEME_COPY: Record<NucleoTheme, { name: NxKey; hint: NxKey }> = {
  nucleo: { name: "themeNucleo", hint: "themeNucleoHint" },
  "nucleo-claro": { name: "themeClaro", hint: "themeClaroHint" },
  command: { name: "themeCommand", hint: "themeCommandHint" },
  day: { name: "themeDay", hint: "themeDayHint" },
};

const SCALES = [0.9, 1, 1.25, 1.5];

export type SettingsTab =
  | "account"
  | "mail"
  | "notifications"
  | "appearance"
  | "privacy"
  | "alerts";

export function SettingsView(props: {
  t: T;
  tab: SettingsTab;
  onTab: (tab: SettingsTab) => void;
  prefs: NucleoPrefs;
  onChange: (next: NucleoPrefs) => void;
  email: string;
  name: string;
  language: AppLanguage;
  onLanguage: (language: AppLanguage) => void;
  mailboxEmail: string | null;
  connected: boolean;
  devices: PushDevice[];
  localEndpoint: string | null;
  pushMessage: string | null;
  onEnablePush: () => void;
  onTestPush: () => void;
  onRemoveDevice: (endpoint: string) => void;
  onReopenGuide: () => void;
  onSignOut: () => void;
  onConnect: () => void;
  onRefresh: () => void;
  onInbox: () => void;
  onImport: () => void;
  showPlan: boolean;
  planBusy: boolean;
  planNotice: string | null;
  onPlan: () => void;
  ruleKind: AlertRuleKind;
  ruleValue: string;
  onRuleKind: (kind: AlertRuleKind) => void;
  onRuleValue: (value: string) => void;
  onAddRule: () => void;
  onDeleteRule: (id: string) => void;
  onPreviewVoice: () => void;
  onPreviewSound: () => void;
}) {
  const { t, prefs, onChange } = props;
  const patch = (partial: Partial<NucleoPrefs>) => onChange({ ...prefs, ...partial });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div className="set-head">
        <div className="crumbs">
          <span>{t("settingsCrumb")}</span>
          <b>{tabTitle(t, props.tab)}</b>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
          <div>
            <h1>{tabTitle(t, props.tab)}</h1>
            <p>{props.tab === "appearance" ? t("settingsHelp") : t("notifHelp")}</p>
          </div>
          <div className="tabs" role="tablist">
            {(["account", "mail", "notifications", "appearance", "privacy", "alerts"] as SettingsTab[]).map((tab) => (
              <button
                key={tab}
                type="button"
                role="tab"
                aria-selected={props.tab === tab}
                className={props.tab === tab ? "on" : undefined}
                onClick={() => props.onTab(tab)}
                style={{ background: "transparent", border: 0, color: "inherit", font: "inherit" }}
              >
                {tabLabel(t, tab)}
              </button>
            ))}
          </div>
        </div>
      </div>

      {props.tab === "appearance" ? (
        <Appearance t={t} prefs={prefs} patch={patch} onPreviewVoice={props.onPreviewVoice} onReset={() => onChange({ ...prefs, theme: "nucleo", fontScale: 1, highContrast: false, reducedMotion: false, speechRate: 1, guide: true, readAloud: true, screenReader: true, visualAlerts: true, badges: true, flash: true, vibrate: true, captions: true, transcript: true, soundEnabled: true, volume: 0.8 })} />
      ) : null}

      {props.tab === "account" ? (
        <section className="card set-card">
          <div className="set-row">
            <span className="ic"><Globe className="i" /></span>
            <div>
              <div className="t">{t("accountEmail")}</div>
              <div className="d">{props.email}</div>
            </div>
          </div>
          <div className="field">
            <label htmlFor="nx-lang">{t("language")}</label>
            <select
              id="nx-lang"
              value={props.language}
              onChange={(event) => props.onLanguage(event.target.value as AppLanguage)}
            >
              {LANGUAGE_OPTIONS.map((option) => (
                <option key={option.code} value={option.code}>
                  {option.nativeName}
                </option>
              ))}
            </select>
          </div>
          {props.showPlan ? (
            <div className="set-row">
              <span className="ic"><Shield className="i" /></span>
              <div>
                <div className="t">{t("planTitle")}</div>
                <div className="d">{props.planNotice || t("planBody")}</div>
              </div>
              <button type="button" className="btn primary sm" disabled={props.planBusy} onClick={props.onPlan}>
                {props.planBusy ? t("planBusy") : t("planCta")}
              </button>
            </div>
          ) : null}
          <div className="set-row">
            <span className="ic"><Lock className="i" /></span>
            <div>
              <div className="t">{props.name}</div>
              <div className="d">{t("personal")}</div>
            </div>
            <button type="button" className="btn" onClick={props.onSignOut}>{t("signOut")}</button>
          </div>
        </section>
      ) : null}

      {props.tab === "mail" ? (
        <section className="card set-card">
          <div className="set-row">
            <span className="ic"><Mail className="i" /></span>
            <div>
              <div className="t">{props.connected ? props.mailboxEmail : t("mailboxMissing")}</div>
              <div className="d">{t("mailReadOnly")}</div>
            </div>
          </div>
          <div className="onboard-actions" style={{ padding: "0 20px 16px" }}>
            <button type="button" className="btn primary sm" onClick={props.onConnect}>{t("connect")}</button>
            <button type="button" className="btn sm" onClick={props.onRefresh}>{t("refreshMail")}</button>
            <button type="button" className="btn sm" onClick={props.onInbox}>{t("openInbox")}</button>
            <button type="button" className="btn sm" onClick={props.onImport}>{t("importMail")}</button>
          </div>
        </section>
      ) : null}

      {props.tab === "notifications" ? (
        <section className="card set-card">
          <div className="card-h">
            <h3><Bell className="i" />{t("notifTitle")}</h3>
          </div>
          <p style={{ padding: "0 20px 12px", color: "var(--text-2)" }}>{t("notifHelp")}</p>
          {props.pushMessage ? <p className="error-line" style={{ padding: "0 20px 12px" }} role="status">{props.pushMessage}</p> : null}
          <div className="onboard-actions" style={{ padding: "0 20px 16px" }}>
            <button type="button" className="btn primary sm" onClick={props.onEnablePush}>{t("enable")}</button>
            <button type="button" className="btn sm" onClick={props.onTestPush}>{t("test")}</button>
            <button type="button" className="btn sm" onClick={props.onReopenGuide}>{t("reopenGuide")}</button>
          </div>
          <div className="set-row">
            <span className="ic"><Volume2 className="i" /></span>
            <div>
              <div className="t">{t("sound")}</div>
              <div className="d">{t("soundHelp")}</div>
            </div>
            <Switch on={prefs.soundEnabled} label={t("sound")} onToggle={() => patch({ soundEnabled: !prefs.soundEnabled })} t={t} />
          </div>
          <div className="field">
            <label htmlFor="nx-volume">{t("volume")} {Math.round(prefs.volume * 100)}%</label>
            <input
              id="nx-volume"
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={prefs.volume}
              onChange={(event) => patch({ volume: Number(event.target.value) })}
            />
            <button type="button" className="listen" data-help-title={t("previewSound")} data-help={t("helpSound")} onClick={props.onPreviewSound}>
              <Volume2 className="i" />{t("previewSound")}
            </button>
          </div>
          <h3 style={{ padding: "8px 20px" }}>{t("devices")}</h3>
          {props.devices.filter((device) => device.is_active).length === 0 ? (
            <p style={{ padding: "0 20px 16px", color: "var(--text-3)" }}>{t("noDevices")}</p>
          ) : (
            props.devices.filter((device) => device.is_active).map((device) => (
              <div className="rule" key={device.id}>
                <div>
                  <b>{device.device_label || device.platform || t("thisDevice")}</b>
                  {device.endpoint && device.endpoint === props.localEndpoint ? (
                    <div className="d">{t("thisDevice")}</div>
                  ) : null}
                </div>
                {device.endpoint ? (
                  <button type="button" className="btn sm" onClick={() => props.onRemoveDevice(device.endpoint || "")}>
                    {t("removeDevice")}
                  </button>
                ) : null}
              </div>
            ))
          )}
        </section>
      ) : null}

      {props.tab === "privacy" ? (
        <section className="card set-card">
          <div className="card-h"><h3><Shield className="i" />{t("privacyTitle")}</h3></div>
          <p style={{ padding: "0 20px 18px", color: "var(--text-2)", lineHeight: 1.5 }}>{t("privacyBody")}</p>
        </section>
      ) : null}

      {props.tab === "alerts" ? (
        <section className="card set-card">
          <div className="card-h"><h3><Bell className="i" />{t("rulesTitle")}</h3></div>
          <p style={{ padding: "0 20px 12px", color: "var(--text-2)" }}>{t("rulesHelp")}</p>
          <div className="field">
            <label htmlFor="nx-rule-kind">{t("ruleCase")}</label>
            <select id="nx-rule-kind" value={props.ruleKind} onChange={(event) => props.onRuleKind(event.target.value as AlertRuleKind)}>
              <option value="sender">{t("ruleSender")}</option>
              <option value="case_type">{t("ruleCase")}</option>
              <option value="subject">{t("ruleSubject")}</option>
              <option value="concept">{t("ruleConcept")}</option>
            </select>
            <label htmlFor="nx-rule-value">{t("ruleValue")}</label>
            <input id="nx-rule-value" value={props.ruleValue} placeholder={t("rulePlaceholder")} onChange={(event) => props.onRuleValue(event.target.value)} />
            <button type="button" className="btn primary sm" onClick={props.onAddRule}>{t("ruleAdd")}</button>
          </div>
          {prefs.alertRules.length === 0 ? (
            <p style={{ padding: "0 20px 16px", color: "var(--text-3)" }}>{t("ruleEmpty")}</p>
          ) : (
            prefs.alertRules.map((rule) => (
              <div className="rule" key={rule.id}>
                <div>
                  <b>{ruleLabel(t, rule.kind)}</b>
                  <div className="d">{rule.value}</div>
                </div>
                <button type="button" className="btn sm" aria-label={t("ruleRemove")} onClick={() => props.onDeleteRule(rule.id)}>
                  {t("ruleRemove")}
                </button>
              </div>
            ))
          )}
        </section>
      ) : null}

      <div className="set-foot">
        <span><Keyboard className="i sm" />{t("keyboardNote")}</span>
        <span><Shield className="i sm" />{t("a11yNote")}</span>
      </div>
    </div>
  );
}

function Appearance({
  t,
  prefs,
  patch,
  onPreviewVoice,
  onReset,
}: {
  t: T;
  prefs: NucleoPrefs;
  patch: (partial: Partial<NucleoPrefs>) => void;
  onPreviewVoice: () => void;
  onReset: () => void;
}) {
  const scaleIndex = Math.max(0, SCALES.indexOf(prefs.fontScale));
  return (
    <>
      <div className="set-grid">
        <section className="card set-card" style={{ gridColumn: "1 / span 2" }}>
          <div className="card-h"><h3><Palette className="i" />{t("themeTitle")}</h3><span className="meta">{t("themeDefault")}: {t("themeNucleo")}</span></div>
          <div className="themes four" role="radiogroup" aria-label={t("themeTitle")}>
            {NUCLEO_THEMES.map((theme) => (
              <button
                key={theme}
                type="button"
                className={prefs.theme === theme ? "theme sel" : "theme"}
                role="radio"
                aria-checked={prefs.theme === theme}
                onClick={() => patch({ theme })}
              >
                <span className="nm">
                  <b>{t(THEME_COPY[theme].name)}</b>
                  <span>{t(THEME_COPY[theme].hint)}</span>
                </span>
                {prefs.theme === theme ? <span className="ck" aria-hidden><span>✓</span></span> : null}
              </button>
            ))}
          </div>
        </section>
        <aside className="card preview">
          <div className="lbl"><span>{t("captionsLive")}</span><span>{Math.round(prefs.fontScale * 100)}%</span></div>
          <article className="card dn lead">
            <div className="dn-top"><span className="urg u-med">{t("urgentMed")}</span></div>
            <h3>{t("voiceSample")}</h3>
          </article>
        </aside>
        <section className="card set-card">
          <div className="card-h"><h3><Eye className="i" />{t("reading")}</h3></div>
          <div className="set-row">
            <span className="ic"><Type className="i" /></span>
            <div>
              <div className="t">{t("textSize")}</div>
              <div className="d">{t("textSizeHelp")}</div>
            </div>
            <span className="valtag">{Math.round(prefs.fontScale * 100)}%</span>
          </div>
          <div className="slider">
            <span className="a1">A</span>
            <input
              aria-label={t("textSize")}
              type="range"
              min={0}
              max={3}
              step={1}
              value={scaleIndex}
              onChange={(event) => patch({ fontScale: SCALES[Number(event.target.value)] ?? 1 })}
            />
            <span className="a2">A</span>
          </div>
          <ToggleRow icon={<Contrast className="i" />} title={t("contrast")} help={t("contrastHelp")} on={prefs.highContrast} t={t} onToggle={() => patch({ highContrast: !prefs.highContrast })} />
          <ToggleRow icon={<Pause className="i" />} title={t("motion")} help={t("motionHelp")} on={prefs.reducedMotion} t={t} onToggle={() => patch({ reducedMotion: !prefs.reducedMotion })} />
        </section>
        <section className="card set-card">
          <div className="card-h"><h3><Waves className="i" />{t("voiceTitle")}</h3></div>
          <ToggleRow icon={<Eye className="i" />} title={t("screenReader")} help={t("screenReaderHelp")} on={prefs.screenReader} t={t} onToggle={() => patch({ screenReader: !prefs.screenReader })} />
          <ToggleRow icon={<Volume2 className="i" />} title={t("readAloud")} help={t("readAloudHelp")} on={prefs.readAloud} t={t} onToggle={() => patch({ readAloud: !prefs.readAloud })} />
          <div className="voice">
            <label className="select">
              {t("volume")}
              <select aria-label={t("voicePreview")} value={String(prefs.speechRate)} onChange={(event) => patch({ speechRate: Number(event.target.value) })}>
                <option value="0.8">0.8×</option>
                <option value="1">1.0×</option>
                <option value="1.2">1.2×</option>
              </select>
            </label>
            <button type="button" className="listen" onClick={onPreviewVoice}><Volume2 className="i" />{t("voicePreview")}</button>
          </div>
        </section>
        <section className="card set-card" style={{ gridColumn: "1 / span 2" }}>
          <div className="card-h"><h3><Bell className="i" />{t("alertsAudio")}</h3><span className="meta">{t("soundNote")}</span></div>
          <ToggleRow icon={<Bell className="i" />} title={t("visualAlerts")} help={t("visualHelp")} on={prefs.visualAlerts} t={t} onToggle={() => patch({ visualAlerts: !prefs.visualAlerts })} />
          <div className="subopts" style={{ padding: "0 20px 12px 68px" }}>
            <Opt on={prefs.badges} label={t("badges")} onClick={() => patch({ badges: !prefs.badges })} />
            <Opt on={prefs.flash} label={t("flash")} onClick={() => patch({ flash: !prefs.flash })} />
            <Opt on={prefs.vibrate} label={t("vibrateOpt")} onClick={() => patch({ vibrate: !prefs.vibrate })} />
          </div>
          <ToggleRow icon={<Captions className="i" />} title={t("captions")} help={t("captionsHelp")} on={prefs.captions} t={t} onToggle={() => patch({ captions: !prefs.captions })} />
          <div className="subopts" style={{ padding: "0 20px 12px 68px" }}>
            <Opt on={prefs.captions} label={t("subtitles")} onClick={() => patch({ captions: !prefs.captions })} />
            <Opt on={prefs.transcript} label={t("transcript")} onClick={() => patch({ transcript: !prefs.transcript })} />
          </div>
        </section>
        <section className="card set-card">
          <div className="set-row">
            <span style={{ width: 64, height: 72, display: "block" }}>
              <Nexto pose="idle" label="Nexto" />
            </span>
            <div>
              <div className="t">{t("guideTitle")}</div>
              <div className="d">{t("guideHelp")}</div>
            </div>
            <Switch on={prefs.guide} label={t("guideTitle")} t={t} onToggle={() => patch({ guide: !prefs.guide })} />
          </div>
        </section>
      </div>
      <button type="button" className="btn sm" onClick={onReset}><RotateCcw className="i" />{t("reset")}</button>
    </>
  );
}

function ToggleRow({
  icon,
  title,
  help,
  on,
  onToggle,
  t,
}: {
  icon: ReactNode;
  title: string;
  help: string;
  on: boolean;
  onToggle: () => void;
  t: T;
}) {
  return (
    <div className="set-row">
      <span className="ic">{icon}</span>
      <div>
        <div className="t">{title}</div>
        <div className="d">{help}</div>
      </div>
      <Switch on={on} label={title} onToggle={onToggle} t={t} />
    </div>
  );
}

function Switch({ on, label, onToggle, t }: { on: boolean; label: string; onToggle: () => void; t: T }) {
  return (
    <span className="ctl">
      <span className={on ? "state on" : "state"}>{on ? t("yes") : t("no")}</span>
      <button type="button" className={on ? "switch on" : "switch"} role="switch" aria-checked={on} aria-label={label} onClick={onToggle} />
    </span>
  );
}

function Opt({ on, label, onClick }: { on: boolean; label: string; onClick: () => void }) {
  return (
    <button type="button" className={on ? "opt" : "opt off"} aria-pressed={on} onClick={onClick}>
      {label}
    </button>
  );
}

function tabLabel(t: T, tab: SettingsTab): string {
  const map: Record<SettingsTab, NxKey> = {
    account: "tabAccount",
    mail: "tabMail",
    notifications: "tabNotifications",
    appearance: "tabAppearance",
    privacy: "tabPrivacy",
    alerts: "tabAlerts",
  };
  return t(map[tab]);
}

function tabTitle(t: T, tab: SettingsTab): string {
  if (tab === "appearance") return t("settingsTitle");
  return tabLabel(t, tab);
}

function ruleLabel(t: T, kind: AlertRuleKind): string {
  if (kind === "sender") return t("ruleSender");
  if (kind === "case_type") return t("ruleCase");
  if (kind === "subject") return t("ruleSubject");
  return t("ruleConcept");
}
