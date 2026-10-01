"use client";

import { Inter } from "next/font/google";
import {
  AlarmClock,
  ArrowUp,
  Bell,
  Check,
  ChevronRight,
  LayoutGrid,
  Lock,
  Mail,
  Menu,
  Mic,
  Package,
  Repeat,
  Settings,
  Sun,
  Volume2,
  Wallet,
  X,
} from "lucide-react";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
  type SyntheticEvent,
} from "react";

import { useLanguage } from "@/lib/i18n/LanguageProvider";
import { localeForLanguage } from "@/lib/i18n/languages";
import { hmsJson, HmsApiError } from "@/lib/hmsApi";
import { ALERT_PHRASE, nx, type NxKey } from "@/lib/nucleo/copy";
import {
  LIFE_AREAS,
  buildLifeItems,
  isOpenStatus,
  matchesQuery,
  monthMoney,
  urgencyOf,
  type InboxCase,
  type InboxThread,
  type LifeAreaId,
  type LifeItem,
  type Urgency,
} from "@/lib/nucleo/lifeAreas";
import {
  DEFAULT_PREFS,
  mergePrefs,
  readLocalPrefs,
  themeAttribute,
  writeLocalPrefs,
  type AlertRuleKind,
  type NucleoPrefs,
  type NucleoTheme,
} from "@/lib/nucleo/prefs";
import { prefsAfterEdit, prefsAfterLoad } from "@/lib/nucleo/prefsSync";
import { browserName, detectDevice } from "@/lib/nucleo/platform";
import {
  deactivatePush,
  enableWebPush,
  loadPushStatus,
  markPushRead,
  sendTestPush,
  type AppNotification,
  type PushDevice,
} from "@/lib/nucleo/pushClient";
import { itemMatchesRules } from "@/lib/nucleo/rules";
import { playAlertTone, speakText, stopSpeaking, vibrateDevice } from "@/lib/nucleo/speech";
import { supabase } from "@/lib/supabase";

import { Nexto } from "@/components/nucleo/Nexto";
import { Onboarding } from "@/components/nucleo/Onboarding";
import { SettingsView, type SettingsTab } from "@/components/nucleo/SettingsView";

import "./nucleo.css";
import "./shell.css";

const inter = Inter({ subsets: ["latin"], display: "swap" });

type ViewId = "today" | "areas" | "money" | "orders" | "subs" | "alerts" | "settings";
type StatusFilter = "open" | "done" | "all" | "high";

export type NucleoAppProps = {
  userId: string;
  email: string;
  name: string;
  connected: boolean;
  mailboxEmail: string | null;
  provider: string | null;
  syncing: boolean;
  yahooPending: boolean;
  gmailPending: boolean;
  showPlan: boolean;
  planBusy: boolean;
  planNotice: string | null;
  importPending: boolean;
  onSignOut: () => void;
  onConnect: () => void;
  onRefreshMail: () => void;
  onOpenInbox: (messageId?: string | null) => void;
  onOpenImport: () => void;
  onPlan: () => void;
  preview?: boolean;
  previewScreen?: "today" | "settings" | "onboarding";
  previewTheme?: NucleoTheme;
  fixtureItems?: LifeItem[];
};

const NAV: Array<{ id: ViewId; icon: typeof Sun; label: NxKey }> = [
  { id: "today", icon: Sun, label: "navToday" },
  { id: "areas", icon: LayoutGrid, label: "navAreas" },
  { id: "money", icon: Wallet, label: "navMoney" },
  { id: "orders", icon: Package, label: "navOrders" },
  { id: "subs", icon: Repeat, label: "navSubs" },
  { id: "alerts", icon: Bell, label: "navAlerts" },
  { id: "settings", icon: Settings, label: "navSettings" },
];

export function NucleoApp(props: NucleoAppProps) {
  const { language, setLanguage } = useLanguage();
  const t = useCallback(
    (key: NxKey, vars?: Record<string, string | number>) => nx(language, key, vars),
    [language],
  );
  const [prefs, setPrefs] = useState<NucleoPrefs>(() => {
    const local = readLocalPrefs(props.userId) ?? DEFAULT_PREFS;
    return props.previewTheme ? { ...local, theme: props.previewTheme } : local;
  });
  const [view, setView] = useState<ViewId>(props.previewScreen === "settings" ? "settings" : "today");
  const [settingsTab, setSettingsTab] = useState<SettingsTab>("appearance");
  const [items, setItems] = useState<LifeItem[]>(props.fixtureItems ?? []);
  const [loading, setLoading] = useState(!props.preview);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [askHits, setAskHits] = useState<LifeItem[] | null>(null);
  const [caseId, setCaseId] = useState<string | null>(null);
  const [areaFilter, setAreaFilter] = useState<LifeAreaId | "all">("all");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("open");
  const [showAreas, setShowAreas] = useState(false);
  const [drawer, setDrawer] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [shortcuts, setShortcuts] = useState(false);
  const [snoozeFor, setSnoozeFor] = useState<string | null>(null);
  const [bubble, setBubble] = useState<{ title: string; body: string } | null>(null);
  const [caption, setCaption] = useState<string | null>(null);
  const [flash, setFlash] = useState<string | null>(null);
  const [onboard, setOnboard] = useState(props.previewScreen === "onboarding");
  const [pushBusy, setPushBusy] = useState(false);
  const [pushMessage, setPushMessage] = useState<string | null>(null);
  const [devices, setDevices] = useState<PushDevice[]>([]);
  const [notes, setNotes] = useState<AppNotification[]>([]);
  const [localEndpoint, setLocalEndpoint] = useState<string | null>(null);
  const [ruleKind, setRuleKind] = useState<AlertRuleKind>("sender");
  const [ruleValue, setRuleValue] = useState("");
  const [toast, setToast] = useState<string | null>(null);
  const [clock, setClock] = useState(() => Date.now());

  useEffect(() => {
    const timer = window.setInterval(() => setClock(Date.now()), 30_000);
    return () => window.clearInterval(timer);
  }, []);
  const askRef = useRef<HTMLInputElement>(null);
  const seenRef = useRef<Set<string> | null>(null);
  const device = useMemo(() => detectDevice(), []);
  const locale = localeForLanguage(language);

  const hydratedRef = useRef(Boolean(props.preview));
  const dirtyRef = useRef(false);
  const saveTimer = useRef<number | null>(null);

  const uploadPrefs = useCallback((next: NucleoPrefs) => {
    if (props.preview) return;
    if (saveTimer.current !== null) window.clearTimeout(saveTimer.current);
    saveTimer.current = window.setTimeout(() => {
      saveTimer.current = null;
      void hmsJson("/api/hms/preferences", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ preferences: next }),
      }).catch(() => undefined);
    }, 500);
  }, [props.preview]);

  useEffect(() => () => {
    if (saveTimer.current !== null) window.clearTimeout(saveTimer.current);
  }, []);

  const updatePrefs = useCallback((next: NucleoPrefs) => {
    setPrefs(next);
    writeLocalPrefs(props.userId, next);
    if (prefsAfterEdit({ hydrated: hydratedRef.current }) === "upload") {
      uploadPrefs(next);
      return;
    }
    dirtyRef.current = true;
  }, [props.userId, uploadPrefs]);

  useEffect(() => {
    if (props.preview) return;
    let cancelled = false;
    void hmsJson<{ preferences: unknown }>("/api/hms/preferences", { cache: "no-store" })
      .then((payload) => {
        if (cancelled) return;
        const action = prefsAfterLoad({
          dirty: dirtyRef.current,
          hasServer: Boolean(payload?.preferences),
        });
        hydratedRef.current = true;
        if (action === "apply-server" && payload?.preferences) {
          const merged = mergePrefs({ ...readLocalPrefs(props.userId), ...(payload.preferences as object) });
          setPrefs(merged);
          writeLocalPrefs(props.userId, merged);
          return;
        }
        if (action === "upload") {
          dirtyRef.current = false;
          const local = readLocalPrefs(props.userId);
          if (local) uploadPrefs(local);
        }
      })
      .catch(() => {
        if (cancelled) return;
        hydratedRef.current = true;
        if (!dirtyRef.current) return;
        dirtyRef.current = false;
        const local = readLocalPrefs(props.userId);
        if (local) uploadPrefs(local);
      });
    return () => {
      cancelled = true;
    };
  }, [props.preview, props.userId, uploadPrefs]);

  const loadItems = useCallback(async () => {
    if (props.preview) {
      setItems(props.fixtureItems ?? []);
      setLoading(false);
      return;
    }
    if (!props.connected) {
      setItems([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const [casePayload, threadPayload] = await Promise.all([
        hmsJson<{ cases: InboxCase[] }>("/api/hms/cases?limit=100", { cache: "no-store" }),
        hmsJson<{ conversations: InboxThread[] }>("/api/hms/messages/threads?limit=80", { cache: "no-store" }).catch(() => ({ conversations: [] as InboxThread[] })),
      ]);
      setItems(buildLifeItems(casePayload.cases ?? [], threadPayload.conversations ?? []));
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t("loadError"));
    } finally {
      setLoading(false);
    }
  }, [props.connected, props.fixtureItems, props.preview, t]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadItems();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [loadItems]);

  useEffect(() => {
    if (props.preview) return;
    const refresh = () => {
      void loadItems();
    };
    window.addEventListener("hms:data-changed", refresh);
    window.addEventListener("hms:classification-complete", refresh);
    return () => {
      window.removeEventListener("hms:data-changed", refresh);
      window.removeEventListener("hms:classification-complete", refresh);
    };
  }, [loadItems, props.preview]);

  const refreshPush = useCallback(async () => {
    if (props.preview) return;
    try {
      const payload = await loadPushStatus();
      setDevices(payload.status.subscriptions ?? []);
      setNotes(payload.notifications);
      setLocalEndpoint(payload.endpoint);
    } catch {
      /* push is optional until the mailbox session is ready */
    }
  }, [props.preview]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void refreshPush();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [refreshPush]);

  useEffect(() => {
    if (props.preview || prefs.pushOnboardingCompletedAt) return;
    let cancelled = false;
    void supabase.auth.getUser().then(({ data }) => {
      if (cancelled) return;
      const created = data.user?.created_at;
      const done = data.user?.user_metadata?.nucleo_push_onboarding;
      if (done || !created) return;
      const age = Date.now() - new Date(created).getTime();
      if (age >= 0 && age < 1000 * 60 * 60 * 72) setOnboard(true);
    }).catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [prefs.pushOnboardingCompletedAt, props.preview]);

  useEffect(() => {
    if (!prefs.soundEnabled) return;
    const fresh = items.filter((item) => itemMatchesRules(item, prefs.alertRules));
    if (seenRef.current === null) {
      seenRef.current = new Set(items.map((item) => item.id));
      return;
    }
    const newcomers = fresh.filter((item) => !seenRef.current?.has(item.id));
    items.forEach((item) => seenRef.current?.add(item.id));
    if (newcomers.length === 0) return;
    void playAlertTone(language, prefs.volume);
    if (prefs.vibrate) vibrateDevice([80, 40, 80, 40, 160]);
    if (prefs.flash) setFlash(newcomers[0]?.line || t("flashLive"));
    if (prefs.captions) setCaption(newcomers[0]?.line || ALERT_PHRASE[language]);
  }, [items, language, prefs.alertRules, prefs.captions, prefs.flash, prefs.soundEnabled, prefs.vibrate, prefs.volume, t]);

  useEffect(() => {
    if (!flash) return;
    const timer = window.setTimeout(() => setFlash(null), 4000);
    return () => window.clearTimeout(timer);
  }, [flash]);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      const typing = target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.tagName === "SELECT");
      if (event.key === "Escape") {
        stopSpeaking();
        setBubble(null);
        setShortcuts(false);
        setSnoozeFor(null);
        setAskHits(null);
        setDrawer(false);
      }
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        askRef.current?.focus();
      }
      if (!typing && event.key === "?") setShortcuts(true);
    }
    function onMessage(event: MessageEvent) {
      if (event.data?.type !== "donexto-alert") return;
      if (prefs.soundEnabled) void playAlertTone(language, prefs.volume);
      if (prefs.captions) setCaption(String(event.data.body || event.data.title || ""));
      if (prefs.flash) setFlash(String(event.data.title || t("flashLive")));
    }
    window.addEventListener("keydown", onKey);
    navigator.serviceWorker?.addEventListener("message", onMessage);
    return () => {
      window.removeEventListener("keydown", onKey);
      navigator.serviceWorker?.removeEventListener("message", onMessage);
    };
  }, [language, prefs.captions, prefs.flash, prefs.soundEnabled, prefs.volume, t]);

  function onHelp(event: SyntheticEvent) {
    if (!prefs.guide) return;
    const node = (event.target as HTMLElement).closest<HTMLElement>("[data-help]");
    if (!node) return;
    setBubble({
      title: node.dataset.helpTitle || t("guideTitle"),
      body: node.dataset.help || "",
    });
  }

  async function submitAsk(text: string) {
    const clean = text.trim();
    setQuery(clean);
    if (!clean) {
      setAskHits(null);
      return;
    }
    if (props.preview || !props.connected) {
      setAskHits(items.filter((item) => matchesQuery(item, clean)));
      return;
    }
    try {
      const [casePayload, threadPayload] = await Promise.all([
        hmsJson<{ cases: InboxCase[] }>(`/api/hms/cases?limit=50&search=${encodeURIComponent(clean)}`, { cache: "no-store" }),
        hmsJson<{ conversations: InboxThread[] }>(`/api/hms/messages/threads?limit=40&search=${encodeURIComponent(clean)}`, { cache: "no-store" }).catch(() => ({ conversations: [] as InboxThread[] })),
      ]);
      setAskHits(buildLifeItems(casePayload.cases ?? [], threadPayload.conversations ?? []));
    } catch {
      setAskHits(items.filter((item) => matchesQuery(item, clean)));
    }
  }

  function dictate() {
    const host = window as Window & {
      SpeechRecognition?: new () => Dictation;
      webkitSpeechRecognition?: new () => Dictation;
    };
    const Ctor = host.SpeechRecognition || host.webkitSpeechRecognition;
    if (!Ctor) {
      setToast(t("askNoSpeech"));
      return;
    }
    const recognition = new Ctor();
    recognition.lang = locale;
    recognition.onresult = (event) => {
      const transcript = event.results?.[0]?.[0]?.transcript ?? "";
      if (transcript) void submitAsk(transcript);
    };
    recognition.start();
  }

  async function markDone(item: LifeItem) {
    if (!item.caseId || props.preview) {
      setItems((current) => current.map((row) => row.id === item.id ? { ...row, status: "resolved" } : row));
      setToast(t("doneSaved"));
      return;
    }
    try {
      await hmsJson(`/api/hms/cases/${item.caseId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: "resolved" }),
      });
      setItems((current) => current.map((row) => row.id === item.id ? { ...row, status: "resolved" } : row));
      setToast(t("doneSaved"));
    } catch (reason) {
      setToast(reason instanceof HmsApiError ? reason.message : t("errorGeneric"));
    }
  }

  async function snooze(item: LifeItem, hours: number) {
    const until = new Date();
    if (hours === 15) {
      until.setDate(until.getDate() + 1);
      until.setHours(9, 0, 0, 0);
    } else {
      until.setTime(until.getTime() + hours * 36e5);
    }
    updatePrefs({ ...prefs, snooze: { ...prefs.snooze, [item.id]: until.toISOString() } });
    setSnoozeFor(null);
    if (item.caseId && !props.preview) {
      await hmsJson(`/api/hms/cases/${item.caseId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ due_at: until.toISOString() }),
      }).catch((reason: unknown) => {
        setToast(reason instanceof Error ? reason.message : t("errorGeneric"));
      });
    }
    setToast(t("snoozedUntil", { when: formatWhen(until.toISOString(), locale) }));
  }

  async function finishOnboarding(enabled: boolean) {
    const stamp = new Date().toISOString();
    updatePrefs({ ...prefs, pushOnboardingCompletedAt: stamp });
    if (!props.preview) {
      await supabase.auth.updateUser({ data: { nucleo_push_onboarding: stamp } }).catch(() => undefined);
    }
    if (!enabled) setOnboard(false);
  }

  async function enableNotifications() {
    setPushBusy(true);
    setPushMessage(null);
    try {
      if (device.ios && !device.standalone) {
        setPushMessage(t("iosInstallSteps"));
        return;
      }
      if (!device.pushSupported && device.notificationPermission === "unsupported") {
        setPushMessage(t("unsupported"));
        return;
      }
      const result = await enableWebPush({
        deviceLabel: `${device.label} · ${browserName(navigator.userAgent)}`,
        platform: device.platform,
        locale,
      });
      if (!result.configured) {
        setPushMessage(t("vapidMissing"));
        if (prefs.soundEnabled) await playAlertTone(language, prefs.volume);
        return;
      }
      try {
        await sendTestPush({
          endpoint: result.endpoint,
          title: ALERT_PHRASE[language],
          body: t("testSent"),
          lang: language,
        });
        setPushMessage(t("testSent"));
      } catch (reason) {
        setPushMessage(reason instanceof HmsApiError ? reason.message : t("vapidMissing"));
        if (prefs.soundEnabled) await playAlertTone(language, prefs.volume);
      }
      await finishOnboarding(true);
      setOnboard(false);
      await refreshPush();
    } catch (reason) {
      const code = reason instanceof Error ? reason.message : "";
      setPushMessage(code === "denied" ? t("permissionDenied") : code === "unsupported" ? t("unsupported") : t("errorGeneric"));
    } finally {
      setPushBusy(false);
    }
  }

  async function testNotification() {
    setPushBusy(true);
    setPushMessage(null);
    try {
      if (prefs.soundEnabled) await playAlertTone(language, prefs.volume);
      if (prefs.vibrate) vibrateDevice([80, 40, 80, 40, 160]);
      if (prefs.flash) setFlash(ALERT_PHRASE[language]);
      if (prefs.captions) setCaption(ALERT_PHRASE[language]);
      if (!props.preview && localEndpoint) {
        await sendTestPush({
          endpoint: localEndpoint,
          title: ALERT_PHRASE[language],
          body: t("testSent"),
          lang: language,
        });
      }
      setPushMessage(t("testSent"));
    } catch (reason) {
      setPushMessage(reason instanceof HmsApiError ? reason.message : t("vapidMissing"));
    } finally {
      setPushBusy(false);
    }
  }

  function addRule() {
    const value = ruleValue.trim();
    if (!value) return;
    const next = {
      ...prefs,
      alertRules: [
        { id: crypto.randomUUID(), kind: ruleKind, value, enabled: true },
        ...prefs.alertRules,
      ],
    };
    updatePrefs(next);
    setRuleValue("");
    setToast(t("saved"));
  }

  const snoozed = (item: LifeItem) => {
    const until = prefs.snooze[item.id];
    return Boolean(until && new Date(until).getTime() > clock);
  };
  const openItems = items.filter((item) => isOpenStatus(item.status) && !snoozed(item));
  const doNow = [...openItems].sort((left, right) => rank(urgencyOf(left)) - rank(urgencyOf(right)) || left.when.localeCompare(right.when)).slice(0, 3);
  const weekMore = Math.max(0, openItems.length - doNow.length);
  const counts = countAreas(items.filter((item) => isOpenStatus(item.status)));
  const money = monthMoney(items);
  const alertCount = openItems.filter((item) => item.area === "security" || item.priority === "high" || item.priority === "critical" || itemMatchesRules(item, prefs.alertRules)).length + notes.filter((note) => !note.read_at).length;
  const visible = filterItems(items, view, areaFilter, statusFilter, prefs);
  const summaryParts = doNow.map((item) => item.line).filter(Boolean);
  const summary = doNow.length === 0
    ? t("summaryEmpty")
    : `${doNow.length === 1 ? t("summaryOne") : t("summaryMany", { count: doNow.length })} ${summaryParts.join(" ")}`;
  const hour = new Date().getHours();
  const greet = hour < 12 ? t("greetingMorning") : hour < 19 ? t("greetingAfternoon") : t("greetingEvening");
  const provider = providerName(props.provider, props.mailboxEmail);
  const pose = loading ? "thinking" : bubble ? "explaining" : "idle";
  const platformLabel = t(platformKey(device.platform));

  return (
    <div
      className={`nx ${inter.className}`}
      data-theme={themeAttribute(prefs.theme)}
      data-contrast={prefs.highContrast ? "high" : undefined}
      data-motion={prefs.reducedMotion ? "reduce" : undefined}
      data-bot={prefs.guide ? "on" : "off"}
      style={{ ["--fs" as string]: String(prefs.fontScale) }}
      onMouseOver={onHelp}
      onFocus={onHelp}
    >
      <svg width="0" height="0" aria-hidden style={{ position: "absolute" }}>
        <defs>
          <linearGradient id="g-ai" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#A78BFA" />
            <stop offset=".55" stopColor="#7C9CFF" />
            <stop offset="1" stopColor="#22D3EE" />
          </linearGradient>
          <linearGradient id="g-ai-light" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#6366F1" />
            <stop offset="1" stopColor="#4F46E5" />
          </linearGradient>
          <linearGradient id="g-ai-claro" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#8B5CF6" />
            <stop offset=".5" stopColor="#5B5BF0" />
            <stop offset="1" stopColor="#0EA5C6" />
          </linearGradient>
        </defs>
      </svg>
      <div className="ambient" aria-hidden><i className="g1" /><i className="g2" /><i className="g3" /><div className="grid" /></div>
      <div className="sr-only" aria-live="polite">{prefs.screenReader ? toast || caption || "" : ""}</div>
      {props.preview ? <div className="preview-pill">{t("previewBadge")}</div> : null}
      {flash && prefs.visualAlerts ? <div className="flash" role="status">{flash}</div> : null}
      {caption && prefs.captions ? <div className="caption-bar" role="status">{caption}</div> : null}
      <div className="app">
        {drawer ? <button type="button" className="overlay" aria-label={t("close")} onClick={() => setDrawer(false)} /> : null}
        <aside className={drawer ? "sidebar is-open" : "sidebar"} aria-label={t("menu")}>
          <div className="brand">
            <div className="logo-mark" aria-hidden>
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#fff" strokeWidth="2.6">
                <path d="M5 6.5 10.5 12 5 17.5" opacity=".55" />
                <path d="M12.5 6.5 18 12l-5.5 5.5" />
              </svg>
            </div>
            <b>Donexto</b>
          </div>
          <nav className="nav">
            {NAV.map((item) => {
              const Icon = item.icon;
              const count = item.id === "today" ? doNow.length : item.id === "orders" ? counts.orders : item.id === "alerts" ? alertCount : 0;
              return (
                <button
                  key={item.id}
                  type="button"
                  className={view === item.id ? "active" : undefined}
                  aria-current={view === item.id ? "page" : undefined}
                  onClick={() => show(item.id)}
                >
                  <Icon aria-hidden />
                  <span>{t(item.label)}</span>
                  {count > 0 && prefs.badges ? (
                    <span className={item.id === "alerts" ? "count hot" : "count"}>{count}</span>
                  ) : null}
                </button>
              );
            })}
          </nav>
          <div className="side-spacer" />
          <div className="mailbox">
            <div className="mb-row">
              <div className="ms-tile" aria-hidden>{provider.slice(0, 1)}</div>
              <div>
                <div className="t">{props.connected ? t("mailboxConnected", { provider }) : t("mailboxMissing")}</div>
                <div className="s"><span className="live" />{props.syncing ? t("loading") : props.connected ? t("connectedNow") : t("readOnly")}</div>
              </div>
            </div>
            <div className="ro"><Lock className="i sm" />{t("readOnly")}</div>
          </div>
          <div className="me">
            <button type="button" className="me-hit" aria-expanded={profileOpen} aria-haspopup="menu" onClick={() => setProfileOpen((open) => !open)}>
              <div className="avatar" aria-hidden>{initials(props.name || props.email)}</div>
              <div>
                <div className="n">{props.name || props.email}</div>
                <div className="p">{t("personal")}</div>
              </div>
            </button>
            {profileOpen ? (
              <div className="card menu-pop" role="menu">
                <button type="button" className="btn" onClick={() => { show("settings"); setSettingsTab("account"); setProfileOpen(false); }}>{t("account")}</button>
                <button type="button" className="btn" onClick={props.onSignOut}>{t("signOut")}</button>
              </div>
            ) : null}
          </div>
        </aside>
        <main className="main">
          <div className="askbar">
            <form
              className="ask"
              role="search"
              data-help-title={t("askLabel")}
              data-help={t("helpAsk")}
              onSubmit={(event) => {
                event.preventDefault();
                void submitAsk(query);
              }}
            >
              <Spark />
              <span className="lbl">{t("askLabel")}</span>
              <input
                ref={askRef}
                value={query}
                aria-label={t("askLabel")}
                placeholder={t("askPlaceholder")}
                onChange={(event) => {
                  setQuery(event.target.value);
                  if (!event.target.value.trim()) setAskHits(null);
                }}
              />
              <kbd>⌘K</kbd>
              <button type="button" className="mic" aria-label={t("askMic")} onClick={dictate}><Mic className="i" /></button>
              <button type="submit" className="btn primary go">{t("askSubmit")}<ArrowUp className="i" /></button>
            </form>
            <button type="button" className="icon-btn" aria-label={t("navAlerts")} onClick={() => show("alerts")}>
              <Bell className="i lg" />
              {alertCount > 0 && prefs.badges ? <span className="dot" /> : null}
            </button>
            {askHits ? (
              <div className="card results" role="listbox" aria-label={t("askResults")}>
                {askHits.length === 0 ? <p className="empty">{t("askEmpty")}</p> : askHits.slice(0, 8).map((item) => (
                  <button key={item.id} type="button" className="result" onClick={() => openItem(item)}>
                    <span>{item.line || item.title}</span>
                    <small>{areaName(t, item.area)} · {item.sender}</small>
                  </button>
                ))}
                <button type="button" className="btn sm" onClick={() => setAskHits(null)}>{t("searchClear")}</button>
              </div>
            ) : null}
          </div>

          {props.yahooPending ? <Banner title={t("bannerYahooTitle")} body={t("bannerYahooBody")} /> : null}
          {props.gmailPending ? <Banner title={t("bannerGmailTitle")} body={t("bannerGmailBody")} /> : null}
          {props.importPending ? (
            <Banner title={t("bannerImportTitle")} body={t("bannerImportBody")} action={<button type="button" className="btn primary sm" onClick={props.onOpenImport}>{t("bannerImportCta")}</button>} />
          ) : null}
          {toast ? <p className="error-line" role="status">{toast}</p> : null}
          {error ? <p className="error-line" role="alert">{error}</p> : null}

          {caseId ? (
            <CaseDetail
              t={t}
              item={items.find((item) => item.caseId === caseId) ?? null}
              caseId={caseId}
              preview={Boolean(props.preview)}
              locale={locale}
              readAloud={prefs.readAloud}
              language={language}
              rate={prefs.speechRate}
              onBack={() => setCaseId(null)}
              onDone={(item) => void markDone(item)}
              onOpenMail={props.onOpenInbox}
              onCaption={setCaption}
            />
          ) : view === "settings" ? (
            <SettingsView
              t={t}
              tab={settingsTab}
              onTab={setSettingsTab}
              prefs={prefs}
              onChange={updatePrefs}
              email={props.email}
              name={props.name}
              language={language}
              onLanguage={(next) => void setLanguage(next)}
              mailboxEmail={props.mailboxEmail}
              connected={props.connected}
              devices={devices}
              localEndpoint={localEndpoint}
              pushMessage={pushMessage}
              onEnablePush={() => void enableNotifications()}
              onTestPush={() => void testNotification()}
              onRemoveDevice={(endpoint) => {
                void deactivatePush(endpoint).then(refreshPush).catch((reason: unknown) => {
                  setPushMessage(reason instanceof Error ? reason.message : t("errorGeneric"));
                });
              }}
              onReopenGuide={() => setOnboard(true)}
              onSignOut={props.onSignOut}
              onConnect={props.onConnect}
              onRefresh={props.onRefreshMail}
              onInbox={() => props.onOpenInbox(null)}
              onImport={props.onOpenImport}
              showPlan={props.showPlan}
              planBusy={props.planBusy}
              planNotice={props.planNotice}
              onPlan={props.onPlan}
              ruleKind={ruleKind}
              ruleValue={ruleValue}
              onRuleKind={setRuleKind}
              onRuleValue={setRuleValue}
              onAddRule={addRule}
              onDeleteRule={(id) => updatePrefs({ ...prefs, alertRules: prefs.alertRules.filter((rule) => rule.id !== id) })}
              onPreviewVoice={() => {
                speakText(t("voiceSample"), language, prefs.speechRate);
                if (prefs.captions) setCaption(t("voiceSample"));
              }}
              onPreviewSound={() => {
                void playAlertTone(language, prefs.volume);
                if (prefs.captions) setCaption(ALERT_PHRASE[language]);
              }}
            />
          ) : (
            <>
              {view === "today" ? (
                <>
                  <div className="summary" data-help-title={t("listenSummary")} data-help={summary}>
                    <div>
                      <div className="eyebrow">{new Intl.DateTimeFormat(locale, { weekday: "long", day: "numeric", month: "long" }).format(new Date())} · {greet}, {firstName(props.name, props.email)}</div>
                      <div className="ai-line"><Spark /><span>{summary}</span></div>
                    </div>
                    {prefs.readAloud ? (
                      <button type="button" className="listen" onClick={() => { speakText(summary, language, prefs.speechRate); setCaption(summary); }}>
                        <Volume2 className="i" />{t("listenSummary")}
                      </button>
                    ) : null}
                  </div>
                  <section>
                    <div className="sec-h">
                      <h2 data-help-title={t("doNow")} data-help={t("helpDoNow")}><Spark />{t("doNow")} {doNow.length > 0 ? <span className="badge-n">{doNow.length}</span> : null}</h2>
                      <div className="meta">{t("sortedBy")}{weekMore > 0 ? <> · <button type="button" className="link" onClick={() => { show("areas"); setStatusFilter("open"); }}>{t("moreWeek", { count: weekMore })}</button></> : null}</div>
                    </div>
                    {loading ? <p className="empty">{t("loading")}</p> : doNow.length === 0 ? (
                      <Empty t={t} connected={props.connected} onConnect={props.onConnect} />
                    ) : (
                      <div className="donext">
                        {doNow.map((item, index) => (
                          <ActionCard
                            key={item.id}
                            t={t}
                            item={item}
                            lead={index === 0}
                            locale={locale}
                            readAloud={prefs.readAloud}
                            language={language}
                            rate={prefs.speechRate}
                            snoozeOpen={snoozeFor === item.id}
                            onOpen={() => openItem(item)}
                            onDone={() => void markDone(item)}
                            onSnooze={() => setSnoozeFor(item.id)}
                            onPickSnooze={(hours) => void snooze(item, hours)}
                            onCaption={setCaption}
                          />
                        ))}
                      </div>
                    )}
                  </section>
                  <AreaChips
                    t={t}
                    counts={counts}
                    total={items.filter((item) => isOpenStatus(item.status)).length}
                    active={areaFilter}
                    expanded={showAreas}
                    onToggle={() => setShowAreas((value) => !value)}
                    onPick={(area) => {
                      setAreaFilter(area);
                      show(area === "all" ? "areas" : area === "money" || area === "bills" ? "money" : area === "orders" ? "orders" : area === "subscriptions" ? "subs" : "areas");
                    }}
                  />
                  <div className="lower">
                    <Timeline
                      t={t}
                      items={items}
                      loading={loading}
                      locale={locale}
                      readAloud={prefs.readAloud}
                      language={language}
                      rate={prefs.speechRate}
                      onOpen={openItem}
                      onCaption={setCaption}
                    />
                    <MonthCard t={t} money={money} locale={locale} onMoney={() => show("money")} onSubs={() => show("subs")} />
                  </div>
                </>
              ) : (
                <ListView
                  t={t}
                  title={t(NAV.find((item) => item.id === view)?.label || "navAreas")}
                  items={visible}
                  loading={loading}
                  connected={props.connected}
                  statusFilter={statusFilter}
                  onStatus={setStatusFilter}
                  locale={locale}
                  notes={view === "alerts" ? notes : []}
                  onOpen={openItem}
                  onReadNote={(id) => {
                    void markPushRead(id).then(refreshPush).catch(() => undefined);
                  }}
                  onConnect={props.onConnect}
                  empty={emptyCopy(t, view)}
                />
              )}
            </>
          )}
        </main>
      </div>
      <nav className="tabbar" aria-label={t("menu")}>
        <Tab icon={<Sun />} label={t("navToday")} on={view === "today"} onClick={() => show("today")} />
        <Tab icon={<Wallet />} label={t("navMoney")} on={view === "money"} onClick={() => show("money")} />
        <Tab icon={<Package />} label={t("navOrders")} on={view === "orders"} onClick={() => show("orders")} />
        <Tab icon={<Bell />} label={t("navAlerts")} on={view === "alerts"} onClick={() => show("alerts")} />
        <Tab icon={<Menu />} label={t("menu")} on={drawer} onClick={() => setDrawer(true)} />
      </nav>
      {prefs.guide ? (
        <div className="bot-dock">
          {bubble ? (
            <div className="bubble card" role="status">
              <div className="bh"><Spark /><span className="t">{bubble.title}</span><button type="button" className="x" aria-label={t("close")} onClick={() => setBubble(null)}><X className="i sm" /></button></div>
              <p>{bubble.body}</p>
              <div className="bf">
                <span>{t("guideName")}</span>
                {prefs.readAloud ? <button type="button" className="listen" onClick={() => { speakText(`${bubble.title}. ${bubble.body}`, language, prefs.speechRate); setCaption(bubble.body); }}><Volume2 className="i" />{t("listen")}</button> : null}
              </div>
            </div>
          ) : null}
          <button type="button" className="bot" data-help-title={t("guideTitle")} data-help={t("helpGuide")} aria-label={t("guideTitle")} onClick={() => setBubble({ title: t("guideTitle"), body: t("helpGuide") })}>
            <Nexto pose={pose} label="Nexto" />
          </button>
        </div>
      ) : null}
      {onboard ? (
        <Onboarding
          t={t}
          device={device}
          platformLabel={platformLabel}
          busy={pushBusy}
          message={pushMessage}
          onEnable={() => void enableNotifications()}
          onSkip={() => void finishOnboarding(false)}
          onClose={() => void finishOnboarding(false)}
        />
      ) : null}
      {shortcuts ? (
        <div className="onboard" role="dialog" aria-modal="true" aria-labelledby="shortcuts-title">
          <section className="card onboard-card">
            <h2 id="shortcuts-title">{t("shortcutsTitle")}</h2>
            <p>⌘K / Ctrl+K — {t("shortcutSearch")}</p>
            <p>Esc — {t("shortcutClose")}</p>
            <p>? — {t("keyboardHelp")}</p>
            <button type="button" className="btn primary" onClick={() => setShortcuts(false)}>{t("close")}</button>
          </section>
        </div>
      ) : null}
    </div>
  );

  function show(next: ViewId) {
    setView(next);
    setCaseId(null);
    setDrawer(false);
  }

  function openItem(item: LifeItem) {
    setAskHits(null);
    if (item.caseId) {
      setCaseId(item.caseId);
      return;
    }
    if (item.messageId) props.onOpenInbox(item.messageId);
  }
}

function Spark() {
  return (
    <svg className="i spark" viewBox="0 0 24 24" aria-hidden>
      <path d="M10 2.5c.55 4.9 2.6 6.95 7.5 7.5-4.9.55-6.95 2.6-7.5 7.5-.55-4.9-2.6-6.95-7.5-7.5 4.9-.55 6.95-2.6 7.5-7.5Z" />
    </svg>
  );
}

function Banner({ title, body, action }: { title: string; body: string; action?: ReactNode }) {
  return (
    <section className="banner" role="status">
      <div>
        <strong>{title}</strong>
        <p>{body}</p>
      </div>
      {action}
    </section>
  );
}

function Empty({ t, connected, onConnect }: { t: (key: NxKey, vars?: Record<string, string | number>) => string; connected: boolean; onConnect: () => void }) {
  return (
    <div className="card empty">
      <strong>{t("emptyTitle")}</strong>
      <span>{t("emptyBody")}</span>
      {!connected ? <button type="button" className="btn primary sm" onClick={onConnect}>{t("emptyConnect")}</button> : null}
    </div>
  );
}

function ActionCard(props: {
  t: (key: NxKey, vars?: Record<string, string | number>) => string;
  item: LifeItem;
  lead: boolean;
  locale: string;
  readAloud: boolean;
  language: Parameters<typeof speakText>[1];
  rate: number;
  snoozeOpen: boolean;
  onOpen: () => void;
  onDone: () => void;
  onSnooze: () => void;
  onPickSnooze: (hours: number) => void;
  onCaption: (text: string) => void;
}) {
  const { t, item } = props;
  const urgency = urgencyOf(item);
  const chip = LIFE_AREAS.find((area) => area.id === item.area)?.chip ?? "a-events";
  return (
    <article className={props.lead ? "card dn lead" : "card dn"}>
      <div className="dn-top">
        <span className={`urg u-${urgency === "high" ? "high" : urgency === "med" ? "med" : "low"}`}>{dueLabel(t, item, props.locale)}</span>
        <span className={`chip ${chip}`}>{areaName(t, item.area)}</span>
      </div>
      <div>
        <h3>{item.line || item.title}</h3>
        <div className="sub">{item.sender || t("readOnly")}{item.amountRaw ? <> <span className="sep" />{item.amountRaw}</> : null}</div>
      </div>
      <div className="next"><ChevronRight className="i" /><span>{item.requestedAction || t("actionFallback")}</span></div>
      <div className="dn-actions">
        <button type="button" className={props.lead ? "btn primary sm" : "btn sm"} onClick={props.onSnooze}><AlarmClock className="i" />{t("remind")}</button>
        {props.readAloud ? (
          <button type="button" className="listen" onClick={() => { speakText(item.line || item.title, props.language, props.rate); props.onCaption(item.line || item.title); }}>
            <Volume2 className="i" />{t("listen")}
          </button>
        ) : null}
        <button type="button" className="btn sm sq" aria-label={t("done")} onClick={props.onDone}><Check className="i" /></button>
        <button type="button" className="btn sm" onClick={props.onOpen}>{t("openCase")}</button>
      </div>
      {props.snoozeOpen ? (
        <div className="card snooze-pop">
          <button type="button" className="btn sm" onClick={() => props.onPickSnooze(1)}>{t("snoozeHour")}</button>
          <button type="button" className="btn sm" onClick={() => props.onPickSnooze(15)}>{t("snoozeTomorrow")}</button>
          <button type="button" className="btn sm" onClick={() => props.onPickSnooze(72)}>{t("snooze3d")}</button>
        </div>
      ) : null}
    </article>
  );
}

function AreaChips(props: {
  t: (key: NxKey, vars?: Record<string, string | number>) => string;
  counts: Record<LifeAreaId, number>;
  total: number;
  active: LifeAreaId | "all";
  expanded: boolean;
  onToggle: () => void;
  onPick: (area: LifeAreaId | "all") => void;
}) {
  const visible = props.expanded ? LIFE_AREAS : LIFE_AREAS.slice(0, 7);
  const hidden = LIFE_AREAS.length - visible.length;
  return (
    <div className="areas" data-help-title={props.t("areas")} data-help={props.t("helpAreas")}>
      <span className="lbl">{props.t("areas")}</span>
      <button type="button" className={props.active === "all" ? "cnt all" : "cnt all"} onClick={() => props.onPick("all")}>{props.t("all")} <b>{props.total}</b></button>
      {visible.map((area) => (
        <button key={area.id} type="button" className={`cnt ${area.chip}`} onClick={() => props.onPick(area.id)}>
          {areaName(props.t, area.id)} <b>{props.counts[area.id] || 0}</b>
        </button>
      ))}
      {hidden > 0 || props.expanded ? (
        <button type="button" className="cnt more" onClick={props.onToggle}>
          {props.expanded ? props.t("lessAreas") : props.t("moreAreas", { count: hidden })}
        </button>
      ) : null}
    </div>
  );
}

function Timeline(props: {
  t: (key: NxKey) => string;
  items: LifeItem[];
  loading: boolean;
  locale: string;
  readAloud: boolean;
  language: Parameters<typeof speakText>[1];
  rate: number;
  onOpen: (item: LifeItem) => void;
  onCaption: (text: string) => void;
}) {
  const groups = groupByDay(props.items.slice(0, 12), props.locale);
  return (
    <section className="card timeline" aria-label={props.t("areas")}>
      {props.loading ? <p className="empty">{props.t("loading")}</p> : groups.length === 0 ? <p className="empty">{props.t("timelineEmpty")}</p> : groups.map((group) => (
        <div key={group.label}>
          <div className="grp">{group.label}</div>
          {group.items.map((item) => {
            const chip = LIFE_AREAS.find((area) => area.id === item.area)?.chip ?? "a-events";
            return (
              <button key={item.id} type="button" className="ev" onClick={() => props.onOpen(item)} style={{ width: "100%", background: "transparent", border: 0, color: "inherit", textAlign: "left" }}>
                <span className="tm">{formatClock(item.when, props.locale)}</span>
                <span className={`dot ${chip}`}><i /></span>
                <div className="tile" aria-hidden>{(item.sender || "D").slice(0, 1).toUpperCase()}</div>
                <div style={{ minWidth: 0 }}>
                  <div className="st">{item.line || item.title}</div>
                  <div className="mt"><span className={`chip ${chip}`}>{areaName(props.t, item.area)}</span>{item.sender}</div>
                </div>
                <div className="pills">
                  {item.reconciled ? <span className="pill ok">{props.t("reconciled")}</span> : null}
                  {item.area === "security" ? <span className="pill warn">{props.t("youQuestion")}</span> : null}
                  {item.amountRaw ? <span className="pill num">{item.amountRaw}</span> : null}
                </div>
                {props.readAloud ? (
                  <span
                    className="listen icon bare"
                    role="button"
                    tabIndex={0}
                    aria-label={props.t("listen")}
                    onClick={(event) => {
                      event.stopPropagation();
                      speakText(item.line || item.title, props.language, props.rate);
                      props.onCaption(item.line || item.title);
                    }}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") {
                        event.stopPropagation();
                        speakText(item.line || item.title, props.language, props.rate);
                      }
                    }}
                  >
                    <Volume2 className="i" />
                  </span>
                ) : <span />}
              </button>
            );
          })}
        </div>
      ))}
    </section>
  );
}

function MonthCard({
  t,
  money,
  locale,
  onMoney,
  onSubs,
}: {
  t: (key: NxKey, vars?: Record<string, string | number>) => string;
  money: ReturnType<typeof monthMoney>;
  locale: string;
  onMoney: () => void;
  onSubs: () => void;
}) {
  const cash = new Intl.NumberFormat(locale, {
    style: "currency",
    currency: "USD",
    currencyDisplay: "narrowSymbol",
  }).format(money.outflows);
  return (
    <aside className="card mini" data-help-title={t("monthTitle")} data-help={t("helpMonth")}>
      <div className="h">
        <div>
          <h3>{t("monthTitle")}</h3>
          <div className="note">{t("monthNote")}</div>
        </div>
      </div>
      {money.movements === 0 && money.subscriptions === 0 ? <p className="empty">{t("monthEmpty")}</p> : (
        <>
          <button type="button" className="mrow a-money" onClick={onMoney}>
            <span className="ic"><Wallet className="i" /></span>
            <div>
              <div className="k">{t("monthOut")}</div>
              <div className="v">{cash}</div>
              <div className="s">{t("monthRefunds", { amount: new Intl.NumberFormat(locale, { style: "currency", currency: "USD", currencyDisplay: "narrowSymbol" }).format(money.refunds), count: money.movements })}</div>
            </div>
            <ChevronRight className="i sm" />
          </button>
          <button type="button" className="mrow a-subs" onClick={onSubs}>
            <span className="ic"><Repeat className="i" /></span>
            <div>
              <div className="k">{t("monthSubs", { count: money.subscriptions })}</div>
              <div className="s">{money.priceIncreases ? t("monthIncrease", { count: money.priceIncreases }) : t("activeSubs", { count: money.subscriptions })}</div>
            </div>
            <ChevronRight className="i sm" />
          </button>
        </>
      )}
    </aside>
  );
}

function ListView(props: {
  t: (key: NxKey, vars?: Record<string, string | number>) => string;
  title: string;
  items: LifeItem[];
  loading: boolean;
  connected: boolean;
  statusFilter: StatusFilter;
  onStatus: (filter: StatusFilter) => void;
  locale: string;
  notes: AppNotification[];
  onOpen: (item: LifeItem) => void;
  onReadNote: (id: string) => void;
  onConnect: () => void;
  empty: string;
}) {
  return (
    <section>
      <div className="sec-h"><h2>{props.title}</h2></div>
      <div className="filters" role="toolbar">
        {(["open", "high", "done", "all"] as StatusFilter[]).map((filter) => (
          <button key={filter} type="button" className={props.statusFilter === filter ? "btn primary sm" : "btn sm"} onClick={() => props.onStatus(filter)}>
            {props.t(filter === "open" ? "filtersOpen" : filter === "done" ? "filtersDone" : filter === "high" ? "filtersHigh" : "filtersAll")}
          </button>
        ))}
      </div>
      {props.loading ? <p className="empty">{props.t("loading")}</p> : props.items.length === 0 && props.notes.length === 0 ? (
        <Empty t={props.t} connected={props.connected} onConnect={props.onConnect} />
      ) : (
        <div className="card">
          {props.notes.map((note) => (
            <button key={note.id} type="button" className="ev" style={{ width: "100%", background: "transparent", border: 0, color: "inherit" }} onClick={() => props.onReadNote(note.id)}>
              <span className="tm">{formatClock(note.created_at, props.locale)}</span>
              <span className="dot a-security"><i /></span>
              <div className="tile">!</div>
              <div style={{ minWidth: 0 }}>
                <div className="st">{note.title}</div>
                <div className="mt">{note.body}</div>
              </div>
              <span />
              <span />
            </button>
          ))}
          {props.items.map((item) => (
            <button key={item.id} type="button" className="ev" style={{ width: "100%", background: "transparent", border: 0, color: "inherit", textAlign: "left" }} onClick={() => props.onOpen(item)}>
              <span className="tm">{formatClock(item.when, props.locale)}</span>
              <span className={`dot ${LIFE_AREAS.find((area) => area.id === item.area)?.chip ?? ""}`}><i /></span>
              <div className="tile">{(item.sender || "D").slice(0, 1)}</div>
              <div style={{ minWidth: 0 }}>
                <div className="st">{item.line || item.title}</div>
                <div className="mt">{areaName(props.t, item.area)} · {item.sender}</div>
              </div>
              <span className="pill">{item.status}</span>
              <ChevronRight className="i" />
            </button>
          ))}
          {props.items.length === 0 ? <p className="empty">{props.empty}</p> : null}
        </div>
      )}
    </section>
  );
}

function CaseDetail(props: {
  t: (key: NxKey, vars?: Record<string, string | number>) => string;
  item: LifeItem | null;
  caseId: string;
  preview: boolean;
  locale: string;
  readAloud: boolean;
  language: Parameters<typeof speakText>[1];
  rate: number;
  onBack: () => void;
  onDone: (item: LifeItem) => void;
  onOpenMail: (messageId?: string | null) => void;
  onCaption: (text: string) => void;
}) {
  const [detail, setDetail] = useState<{
    summary?: string | null;
    requested_action?: string | null;
    events?: Array<{ id: string; title: string; description: string | null; created_at: string }>;
    messages?: Array<{ id: string; subject?: string; sender?: string; snippet?: string; received_at?: string }>;
  } | null>(null);
  useEffect(() => {
    if (props.preview) return;
    let cancelled = false;
    void hmsJson<typeof detail>(`/api/hms/cases/${props.caseId}`, { cache: "no-store" })
      .then((payload) => {
        if (!cancelled) setDetail(payload);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [props.caseId, props.preview]);
  const line = props.item?.line || detail?.summary || "";
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <header className="topbar">
        <div className="crumbs">
          <button type="button" className="back" aria-label={props.t("caseBack")} onClick={props.onBack}><X className="i" /></button>
          <b>{props.item?.title || props.t("openCase")}</b>
        </div>
        <div className="bar-actions">
          <span className="ro-pill"><Lock className="i sm" />{props.t("caseReadOnly")}</span>
          {props.item ? <button type="button" className="btn" onClick={() => props.onDone(props.item as LifeItem)}><Check className="i" />{props.t("done")}</button> : null}
        </div>
      </header>
      <section className="card hero">
        <div>
          <div className="chips">
            {props.item ? <span className={`chip ${LIFE_AREAS.find((area) => area.id === props.item?.area)?.chip}`}>{areaName(props.t, props.item.area)}</span> : null}
            {props.item?.reconciled ? <span className="pill ok">{props.t("reconciled")}</span> : null}
          </div>
          <div className="ai-label"><Spark />{props.t("caseOneLine")}</div>
          <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
            <h1 className="statement">{line}</h1>
            {props.readAloud ? (
              <button type="button" className="listen" onClick={() => { speakText(line, props.language, props.rate); props.onCaption(line); }}>
                <Volume2 className="i" />{props.t("listen")}
              </button>
            ) : null}
          </div>
          <p style={{ marginTop: 10, color: "var(--text-3)" }}>{props.t("caseNotBalance")}</p>
        </div>
      </section>
      <div className="case-grid">
        <section className="card">
          <div className="card-h"><h3>{props.t("caseEvents")}</h3></div>
          <div className="tl">
            {(detail?.events ?? []).length === 0 ? <p className="empty">{props.t("timelineEmpty")}</p> : detail?.events?.map((event) => (
              <div className="step" key={event.id}>
                <div className="node" />
                <div>
                  <div className="hd"><div className="ttl">{event.title}</div><span className="when">{formatWhen(event.created_at, props.locale)}</span></div>
                  {event.description ? <div className="ds">{event.description}</div> : null}
                </div>
              </div>
            ))}
          </div>
        </section>
        <aside style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <section className="card next-box">
            <div className="ai-label">{props.t("caseNext")}</div>
            <div className="big">{detail?.requested_action || props.item?.requestedAction || props.t("actionFallback")}</div>
          </section>
          <section className="card">
            <div className="card-h"><h3><Mail className="i" />{props.t("caseSources")}</h3></div>
            {(detail?.messages ?? []).length === 0 ? <p className="empty">{props.t("timelineEmpty")}</p> : detail?.messages?.map((message) => (
              <button key={message.id} type="button" className="src" style={{ width: "100%", background: "transparent", color: "inherit", textAlign: "left" }} onClick={() => props.onOpenMail(message.id)}>
                <Mail className="i" />
                <div>
                  <div className="sj">{message.subject || message.snippet}</div>
                  <div className="fr">{message.sender}</div>
                </div>
                <span className="dt">{props.t("caseOpenMail")}</span>
              </button>
            ))}
          </section>
        </aside>
      </div>
    </div>
  );
}

function Tab({ icon, label, on, onClick }: { icon: ReactNode; label: string; on: boolean; onClick: () => void }) {
  return (
    <button type="button" className={on ? "on" : undefined} onClick={onClick}>
      {icon}
      <span>{label}</span>
    </button>
  );
}

type Dictation = {
  lang: string;
  start: () => void;
  onresult: ((event: { results?: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
};

function rank(urgency: Urgency): number {
  if (urgency === "high") return 0;
  if (urgency === "med") return 1;
  return 2;
}

function countAreas(items: LifeItem[]): Record<LifeAreaId, number> {
  const counts = Object.fromEntries(LIFE_AREAS.map((area) => [area.id, 0])) as Record<LifeAreaId, number>;
  for (const item of items) counts[item.area] += 1;
  return counts;
}

function filterItems(items: LifeItem[], view: ViewId, area: LifeAreaId | "all", status: StatusFilter, prefs: NucleoPrefs): LifeItem[] {
  return items.filter((item) => {
    if (view === "money" && item.area !== "money" && item.area !== "bills") return false;
    if (view === "orders" && item.area !== "orders") return false;
    if (view === "subs" && item.area !== "subscriptions") return false;
    if (view === "alerts" && !(item.area === "security" || item.priority === "high" || item.priority === "critical" || itemMatchesRules(item, prefs.alertRules))) return false;
    if (view === "areas" && area !== "all" && item.area !== area) return false;
    if (status === "open" && !isOpenStatus(item.status)) return false;
    if (status === "done" && isOpenStatus(item.status)) return false;
    if (status === "high" && item.priority !== "high" && item.priority !== "critical" && urgencyOf(item) !== "high") return false;
    return true;
  });
}

const AREA_LABELS: Record<LifeAreaId, Record<string, string>> = {
  money: { es: "Dinero", en: "Money", fr: "Argent", it: "Denaro", pt: "Dinheiro" },
  orders: { es: "Pedidos", en: "Orders", fr: "Commandes", it: "Ordini", pt: "Pedidos" },
  subscriptions: { es: "Suscripciones", en: "Subscriptions", fr: "Abonnements", it: "Abbonamenti", pt: "Assinaturas" },
  work: { es: "Trabajo", en: "Work", fr: "Travail", it: "Lavoro", pt: "Trabalho" },
  home: { es: "Hogar y familia", en: "Home & family", fr: "Foyer", it: "Casa e famiglia", pt: "Casa e família" },
  health: { es: "Salud", en: "Health", fr: "Santé", it: "Salute", pt: "Saúde" },
  bills: { es: "Facturas", en: "Bills", fr: "Factures", it: "Fatture", pt: "Faturas" },
  travel: { es: "Viajes", en: "Travel", fr: "Voyages", it: "Viaggi", pt: "Viagens" },
  security: { es: "Seguridad", en: "Security", fr: "Sécurité", it: "Sicurezza", pt: "Segurança" },
  government: { es: "Gobierno", en: "Government", fr: "Administration", it: "Governo", pt: "Governo" },
  insurance: { es: "Seguros", en: "Insurance", fr: "Assurance", it: "Assicurazione", pt: "Seguros" },
  education: { es: "Educación", en: "Education", fr: "Éducation", it: "Istruzione", pt: "Educação" },
  social: { es: "Social", en: "Social", fr: "Social", it: "Social", pt: "Social" },
  events: { es: "Eventos", en: "Events", fr: "Événements", it: "Eventi", pt: "Eventos" },
  promos: { es: "Promociones", en: "Promotions", fr: "Promotions", it: "Promozioni", pt: "Promoções" },
};

function areaName(_t: (key: NxKey) => string, area: LifeAreaId): string {
  if (typeof document === "undefined") return AREA_LABELS[area].es;
  const lang = document.documentElement.lang?.slice(0, 2) || "es";
  return AREA_LABELS[area][lang] || AREA_LABELS[area].en;
}

function dueLabel(t: (key: NxKey, vars?: Record<string, string | number>) => string, item: LifeItem, locale: string): string {
  if (!item.dueAt) return urgencyOf(item) === "high" ? t("urgentHigh") : t("noDue");
  const due = new Date(item.dueAt);
  if (due.getTime() < Date.now()) return t("overdue");
  return t("dueIn", { when: new Intl.DateTimeFormat(locale, { day: "numeric", month: "short" }).format(due) });
}

function formatWhen(iso: string, locale: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat(locale, { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" }).format(date);
}

function formatClock(iso: string, locale: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat(locale, { hour: "numeric", minute: "2-digit" }).format(date);
}

function groupByDay(items: LifeItem[], locale: string): Array<{ label: string; items: LifeItem[] }> {
  const groups = new Map<string, LifeItem[]>();
  for (const item of items) {
    const label = new Intl.DateTimeFormat(locale, { weekday: "long", day: "numeric", month: "short" }).format(new Date(item.when));
    const bucket = groups.get(label) ?? [];
    bucket.push(item);
    groups.set(label, bucket);
  }
  return [...groups.entries()].map(([label, rows]) => ({ label, items: rows }));
}

function initials(value: string): string {
  return value.split(/\s+|@/).filter(Boolean).slice(0, 2).map((part) => part[0]?.toUpperCase() ?? "").join("") || "DX";
}

function firstName(name: string, email: string): string {
  return (name || email).split(/[\s@]/)[0] || "Donexto";
}

function providerName(provider: string | null, email: string | null): string {
  const value = `${provider || ""} ${email || ""}`.toLowerCase();
  if (value.includes("outlook") || value.includes("hotmail") || value.includes("microsoft") || value.includes("live.")) return "Outlook";
  if (value.includes("yahoo")) return "Yahoo";
  if (value.includes("gmail") || value.includes("google")) return "Gmail";
  return "Mail";
}

function platformKey(platform: string): NxKey {
  if (platform === "ios") return "platformIos";
  if (platform === "android") return "platformAndroid";
  if (platform === "macos") return "platformMac";
  if (platform === "windows") return "platformWindows";
  if (platform === "linux") return "platformLinux";
  return "platformDesktop";
}

function emptyCopy(t: (key: NxKey) => string, view: ViewId): string {
  if (view === "orders") return t("ordersEmpty");
  if (view === "subs") return t("subsEmpty");
  if (view === "money") return t("moneyEmpty");
  if (view === "alerts") return t("alertsEmpty");
  return t("emptyTitle");
}
