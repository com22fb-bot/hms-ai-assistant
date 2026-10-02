"use client";

import { Inter } from "next/font/google";
import {
  ArrowUp,
  Bell,
  Check,
  ChevronRight,
  CircleHelp,
  LayoutGrid,
  Lock,
  LogOut,
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
import { askLocal, needsActionToday, summaryParts, type AskResult } from "@/lib/nucleo/commandCenter";
import {
  areaChip,
  buildLifeItems,
  isOpenStatus,
  urgencyOf,
  type InboxCase,
  type InboxThread,
  type LifeAreaId,
  type LifeItem,
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

import { CommandCenter, areaLabel } from "@/components/nucleo/CommandCenter";
import { Nexto } from "@/components/nucleo/Nexto";
import { NextoDock } from "@/components/nucleo/NextoDock";
import { helpForKey, matchHelp, type HelpMatch, type HelpTarget } from "@/lib/nucleo/helpKb";
import { cleanDisplayText, stripCssNoise } from "@/lib/nucleo/cleanText";
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
  const [askHits, setAskHits] = useState<AskResult | null>(null);
  const [askHelp, setAskHelp] = useState<HelpMatch[]>([]);
  const [pendingFocus, setPendingFocus] = useState<string | null>(null);
  const [caseId, setCaseId] = useState<string | null>(null);
  const [areaFilter, setAreaFilter] = useState<LifeAreaId | "all">("all");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("open");
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
  const hoverTimer = useRef<number | null>(null);
  const lastHelpNode = useRef<HTMLElement | null>(null);
  const explainedNode = useRef<HTMLElement | null>(null);
  const highlightTimer = useRef<number | null>(null);
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
        lastHelpNode.current = null;
        setShortcuts(false);
        setSnoozeFor(null);
        setAskHits(null);
        setAskHelp([]);
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

  /** Title/body for an element with `data-help-key` (5-language KB) or inline `data-help`. */
  const describe = useCallback((node: HTMLElement | null): { title: string; body: string } | null => {
    if (!node) return null;
    const copy = helpForKey(node.dataset.helpKey, language);
    const title = node.dataset.helpTitle || copy?.title || "";
    const base = node.dataset.help || copy?.body || "";
    const body = [node.dataset.helpDetail, base].filter(Boolean).join(" ");
    return title || body ? { title: title || t("guideTitle"), body } : null;
  }, [language, t]);

  useEffect(() => () => {
    if (hoverTimer.current !== null) window.clearTimeout(hoverTimer.current);
  }, []);

  function onHelp(event: SyntheticEvent) {
    if (!prefs.guide) return;
    const target = event.target as HTMLElement;
    // The robot and its bubble never replace what it is saying (it explains on drop/click).
    if (target.closest(".bot-dock")) return;
    const node = target.closest<HTMLElement>("[data-help-key],[data-help]");
    if (!node || node === lastHelpNode.current) return;
    if (hoverTimer.current !== null) window.clearTimeout(hoverTimer.current);
    const immediate = event.type === "focus";
    const run = () => {
      hoverTimer.current = null;
      const help = describe(node);
      if (!help) return;
      lastHelpNode.current = node;
      setBubble(help);
    };
    if (immediate) run();
    else hoverTimer.current = window.setTimeout(run, 260);
  }

  /** Nexto was dropped (or moved with the keyboard) over an element. */
  function explainDropped(node: HTMLElement | null) {
    const help = describe(node);
    lastHelpNode.current = node;
    setBubble(help ?? { title: t("guideTitle"), body: t("guideNothing") });
    // Outline only the element Nexto is explaining right now.
    explainedNode.current?.classList.remove("nx-explained");
    explainedNode.current = node && help ? node : null;
    if (node && help) {
      node.classList.add("nx-explained");
      window.setTimeout(() => node.classList.remove("nx-explained"), 1800);
    }
  }

  /** Help answer CTA: open the view/tab and highlight the exact option. */
  function goToHelp(target: HelpTarget) {
    setAskHits(null);
    setAskHelp([]);
    if (target.action === "shortcuts") {
      setShortcuts(true);
      return;
    }
    if (target.action === "ask") {
      askRef.current?.focus();
      return;
    }
    if (target.view) show(target.view);
    if (target.tab) setSettingsTab(target.tab);
    if (target.focus) setPendingFocus(target.focus);
  }

  useEffect(() => () => {
    if (highlightTimer.current !== null) window.clearTimeout(highlightTimer.current);
  }, []);

  useEffect(() => {
    if (!pendingFocus) return;
    let tries = 0;
    const timer = window.setInterval(() => {
      tries += 1;
      const nodes = Array.from(document.querySelectorAll<HTMLElement>(`[data-help-key="${CSS.escape(pendingFocus)}"]`));
      const visible = nodes.filter((node) => {
        const rect = node.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0 && rect.right > 0 && rect.left < window.innerWidth;
      });
      // Prefer the copy inside the main area (e.g. Settings › Account › Sign out).
      const node = visible.find((item) => item.closest("main")) ?? visible[0];
      if (!node && tries < 20) return;
      window.clearInterval(timer);
      setPendingFocus(null);
      if (!node) return;
      node.scrollIntoView({ block: "center", behavior: prefs.reducedMotion ? "auto" : "smooth" });
      const focusable = node.matches("button, a, input, select, textarea, [tabindex]") ? node : node.querySelector<HTMLElement>("button, a, input, select, textarea, [tabindex]");
      focusable?.focus({ preventScroll: true });
      node.classList.add("nx-highlight");
      // Kept in a ref: clearing pendingFocus re-runs this effect and must not cancel the removal.
      if (highlightTimer.current !== null) window.clearTimeout(highlightTimer.current);
      highlightTimer.current = window.setTimeout(() => {
        highlightTimer.current = null;
        node.classList.remove("nx-highlight");
      }, 2800);
    }, 60);
    return () => window.clearInterval(timer);
  }, [pendingFocus, prefs.reducedMotion]);

  /**
   * "Pregunta a Donexto" is a local, rule-based search over the cases and
   * threads already loaded from the user's own mailbox. No LLM, no new call.
   */
  function submitAsk(text: string) {
    const clean = text.trim();
    setQuery(clean);
    if (!clean) {
      setAskHits(null);
      setAskHelp([]);
      return;
    }
    // How-to questions about the app first (local rules), then the user's cases.
    setAskHelp(matchHelp(clean, 3));
    setAskHits(askLocal(items, clean, new Date()));
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
      if (transcript) submitAsk(transcript);
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
  const actionToday = needsActionToday(items, new Date(clock), snoozed);
  const ordersOpen = openItems.filter((item) => item.area === "orders").length;
  const alertCount = openItems.filter((item) => item.area === "security" || item.priority === "high" || item.priority === "critical" || itemMatchesRules(item, prefs.alertRules)).length + notes.filter((note) => !note.read_at).length;
  const visible = filterItems(items, view, areaFilter, statusFilter, prefs);
  const spoken = summaryParts(actionToday.map((item) => item.line), actionToday.length, 3);
  const summary = actionToday.length === 0
    ? t("summaryEmpty")
    : [
        actionToday.length === 1 ? t("summaryOne") : t("summaryMany", { count: actionToday.length }),
        ...spoken.named,
        spoken.more > 0 ? t("summaryMore", { count: spoken.more }) : "",
      ].filter(Boolean).join(" ");
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
              const count = item.id === "today" ? actionToday.length : item.id === "orders" ? ordersOpen : item.id === "alerts" ? alertCount : 0;
              return (
                <button
                  key={item.id}
                  type="button"
                  className={view === item.id ? "active" : undefined}
                  aria-current={view === item.id ? "page" : undefined}
                  data-help-key={`nav-${item.id}`}
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
          <div className="mailbox" data-help-key="mailbox">
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
            <button type="button" className="me-hit" data-help-key="profile" aria-expanded={profileOpen} aria-haspopup="menu" onClick={() => setProfileOpen((open) => !open)}>
              <div className="avatar" aria-hidden>{initials(props.name || props.email)}</div>
              <div>
                <div className="n">{props.name || props.email}</div>
                <div className="p">{t("personal")}</div>
              </div>
            </button>
            {profileOpen ? (
              <div className="card menu-pop" role="menu">
                <button type="button" className="btn" onClick={() => { show("settings"); setSettingsTab("account"); setProfileOpen(false); }}>{t("account")}</button>
                <button type="button" className="btn" onClick={props.onSignOut}><LogOut className="i" />{t("signOut")}</button>
              </div>
            ) : null}
          </div>
          <button type="button" className="me-out" data-help-key="logout" onClick={props.onSignOut}>
            <LogOut className="i" aria-hidden />
            <span>{t("signOut")}</span>
          </button>
        </aside>
        <main className={caseId ? "main is-reading" : view === "today" ? "main is-today" : "main"}>
          <div className="askbar">
            <form
              className="ask"
              role="search"
              data-help-key="ask"
              onSubmit={(event) => {
                event.preventDefault();
                submitAsk(query);
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
                  if (!event.target.value.trim()) {
                    setAskHits(null);
                    setAskHelp([]);
                  }
                }}
              />
              <kbd>⌘K</kbd>
              <button type="button" className="mic" data-help-key="dictate" aria-label={t("askMic")} onClick={dictate}><Mic className="i" /></button>
              <button type="submit" className="btn primary go" aria-label={t("askSubmit")}><span className="go-t">{t("askSubmit")}</span><ArrowUp className="i" /></button>
            </form>
            <button type="button" className="icon-btn" data-help-key="alerts" aria-label={t("navAlerts")} onClick={() => show("alerts")}>
              <Bell className="i lg" />
              {alertCount > 0 && prefs.badges ? <span className="dot" /> : null}
            </button>
            {askHits || askHelp.length ? (
              <div className="results" role="region" aria-live="polite" aria-label={t("askResults")}>
                <div className="results-top">
                  <span className="results-q" title={query}>“{query}”</span>
                  <button type="button" className="btn sm results-clear" onClick={clearAsk}><X className="i sm" />{t("searchClear")}</button>
                </div>
                <div className="results-body">
                  {askHelp.length ? (
                    <section className="results-help" aria-label={t("askHelpTitle")}>
                      <h3 className="results-sec"><CircleHelp className="i sm" aria-hidden />{t("askHelpTitle")}</h3>
                      {askHelp.map(({ entry }) => {
                        const copy = entry.copy[language] ?? entry.copy.es;
                        return (
                          <article key={entry.id} className="help-card">
                            <b>{copy.title}</b>
                            <p>{copy.body}</p>
                            {copy.cta ? (
                              <button type="button" className="btn primary sm help-go" onClick={() => goToHelp(entry.target)}>
                                {copy.cta}<ChevronRight className="i sm" aria-hidden />
                              </button>
                            ) : null}
                          </article>
                        );
                      })}
                    </section>
                  ) : null}
                  {askHits && !(askHelp.length && (askHits.vague || askHits.hits.length === 0)) ? (
                    <section className="results-cases" aria-label={t("askCasesTitle")}>
                      <div className="results-h">
                        {askHelp.length ? <span className="results-sec">{t("askCasesTitle")}</span> : null}
                        {askHits.vague ? null : <span className="results-n">{askHits.hits.length === 1 ? t("askCountOne") : t("askCount", { count: askHits.hits.length })}</span>}
                        {intentLabels(t, askHits.intent).length ? <span className="results-f">{t("askFilters", { filters: intentLabels(t, askHits.intent).join(" · ") })}</span> : null}
                      </div>
                      {askHits.vague ? <p className="results-empty">{t("askVague")}</p> : askHits.hits.length === 0 ? <p className="results-empty">{t("askEmpty")}</p> : askHits.hits.slice(0, 8).map((item) => (
                        <button key={item.id} type="button" className="result" data-help-key="openCase" onClick={() => openItem(item)}>
                          <span>{cleanDisplayText(item.line || item.title, item.sender || "—")}</span>
                          <small>{areaLabel(t, item.area)}{item.sender ? ` · ${item.sender}` : ""}{item.amountRaw ? ` · ${item.amountRaw}` : ""}</small>
                        </button>
                      ))}
                    </section>
                  ) : null}
                </div>
                <div className="results-f2">
                  <small>{t("askLocalNote")}</small>
                </div>
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
                <CommandCenter
                  t={t}
                  locale={locale}
                  language={language}
                  items={items}
                  notes={notes}
                  loading={loading}
                  connected={props.connected}
                  readAloud={prefs.readAloud}
                  speechRate={prefs.speechRate}
                  badges={prefs.badges}
                  now={clock}
                  eyebrow={`${new Intl.DateTimeFormat(locale, { weekday: "long", day: "numeric", month: "long" }).format(new Date(clock))} · ${greet}, ${firstName(props.name, props.email)}`}
                  summary={summary}
                  snoozed={snoozed}
                  matchesRule={(item) => itemMatchesRules(item, prefs.alertRules)}
                  snoozeFor={snoozeFor}
                  onSnoozeOpen={setSnoozeFor}
                  onSnooze={(item, hours) => void snooze(item, hours)}
                  onDone={(item) => void markDone(item)}
                  onOpen={openItem}
                  onReadNote={(id) => {
                    void markPushRead(id).then(refreshPush).catch(() => undefined);
                  }}
                  onPickArea={(area) => {
                    setAreaFilter(area);
                    setStatusFilter("open");
                    show("areas");
                  }}
                  onViewAlerts={() => show("alerts")}
                  onViewOpen={() => {
                    setAreaFilter("all");
                    setStatusFilter("open");
                    show("areas");
                  }}
                  onConnect={props.onConnect}
                  onCaption={setCaption}
                />
              ) : (
                <ListView
                  t={t}
                  title={view === "areas" && areaFilter !== "all" ? areaLabel(t, areaFilter) : t(NAV.find((item) => item.id === view)?.label || "navAreas")}
                  onClearArea={view === "areas" && areaFilter !== "all" ? () => setAreaFilter("all") : undefined}
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
        <Tab icon={<Sun />} helpKey="nav-today" label={t("navToday")} on={view === "today"} onClick={() => show("today")} />
        <Tab icon={<Wallet />} helpKey="nav-money" label={t("navMoney")} on={view === "money"} onClick={() => show("money")} />
        <Tab icon={<Package />} helpKey="nav-orders" label={t("navOrders")} on={view === "orders"} onClick={() => show("orders")} />
        <Tab icon={<Bell />} helpKey="nav-alerts" label={t("navAlerts")} on={view === "alerts"} onClick={() => show("alerts")} />
        <Tab icon={<Menu />} helpKey="nav-settings" label={t("menu")} on={drawer} onClick={() => setDrawer(true)} />
      </nav>
      {prefs.guide ? (
        <NextoDock
          label={t("guideTitle")}
          hint={t("guideDragHint")}
          onActivate={() => setBubble({ title: t("guideTitle"), body: `${t("helpGuide")} ${t("guideDragHint")}` })}
          onExplain={explainDropped}
          robot={<Nexto pose={pose} label="Nexto" />}
          bubble={bubble ? (
            <div className="bubble card" role="status">
              <div className="bh"><Spark /><span className="t">{bubble.title}</span><button type="button" className="x" aria-label={t("close")} onClick={() => { setBubble(null); lastHelpNode.current = null; }}><X className="i sm" /></button></div>
              <p>{bubble.body}</p>
              <div className="bf">
                <span>{t("guideName")}</span>
                {prefs.readAloud ? <button type="button" className="listen" onClick={() => { speakText(`${bubble.title}. ${bubble.body}`, language, prefs.speechRate); setCaption(bubble.body); }}><Volume2 className="i" />{t("listen")}</button> : null}
              </div>
            </div>
          ) : null}
        />
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

  function clearAsk() {
    setAskHits(null);
    setAskHelp([]);
    setQuery("");
    askRef.current?.focus();
  }

  function openItem(item: LifeItem) {
    setAskHits(null);
    setAskHelp([]);
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

function ListView(props: {
  t: (key: NxKey, vars?: Record<string, string | number>) => string;
  title: string;
  onClearArea?: () => void;
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
      <div className="sec-h">
        <h2>{props.title}</h2>
        {props.onClearArea ? <button type="button" className="btn sm" onClick={props.onClearArea}><X className="i" />{props.t("clearFilter")}</button> : null}
      </div>
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
            <button key={item.id} type="button" className="ev" data-help-key="openCase" style={{ width: "100%", background: "transparent", border: 0, color: "inherit", textAlign: "left" }} onClick={() => props.onOpen(item)}>
              <span className="tm">{formatClock(item.when, props.locale)}</span>
              <span className={`dot ${areaChip(item.area)}`}><i /></span>
              <div className="tile">{(item.sender || "D").slice(0, 1)}</div>
              <div style={{ minWidth: 0 }}>
                <div className="st">{item.line || item.title}</div>
                <div className="mt">{areaLabel(props.t, item.area)}{item.sender ? ` · ${item.sender}` : ""}</div>
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
  const line = props.item?.line || stripCssNoise(detail?.summary) || "";
  return (
    <div className="case-view">
      <header className="topbar case-top">
        <div className="crumbs">
          <button type="button" className="back" aria-label={props.t("caseBack")} onClick={props.onBack}><X className="i" /></button>
          <b>{props.item?.title || props.t("openCase")}</b>
        </div>
        <div className="bar-actions">
          <span className="ro-pill"><Lock className="i sm" />{props.t("caseReadOnly")}</span>
          {props.item ? <button type="button" className="btn" onClick={() => props.onDone(props.item as LifeItem)}><Check className="i" />{props.t("done")}</button> : null}
        </div>
      </header>
      <section className="card hero case-hero">
        <div>
          <div className="chips">
            {props.item ? <span className={`chip ${areaChip(props.item.area)}`}>{areaLabel(props.t, props.item.area)}</span> : null}
            {props.item?.reconciled ? <span className="pill ok">{props.t("reconciled")}</span> : null}
          </div>
          <div className="ai-label"><Spark />{props.t("caseOneLine")}</div>
          <div className="case-line">
            <h1 className="statement">{line}</h1>
            {props.readAloud ? (
              <button type="button" className="listen" onClick={() => { speakText(line, props.language, props.rate); props.onCaption(line); }}>
                <Volume2 className="i" />{props.t("listen")}
              </button>
            ) : null}
          </div>
          <p className="case-note">{props.t("caseNotBalance")}</p>
        </div>
      </section>
      <div className="case-grid case-body">
        <section className="card">
          <div className="card-h"><h3>{props.t("caseEvents")}</h3></div>
          <div className="tl">
            {(detail?.events ?? []).length === 0 ? <p className="empty">{props.t("timelineEmpty")}</p> : detail?.events?.map((event) => (
              <div className="step" key={event.id}>
                <div className="node" />
                <div>
                  <div className="hd"><div className="ttl">{event.title}</div><span className="when">{formatWhen(event.created_at, props.locale)}</span></div>
                  {event.description && stripCssNoise(event.description) ? <div className="ds">{stripCssNoise(event.description)}</div> : null}
                </div>
              </div>
            ))}
          </div>
        </section>
        <aside className="case-side">
          <section className="card next-box">
            <div className="ai-label">{props.t("caseNext")}</div>
            <div className="big">{detail?.requested_action || props.item?.requestedAction || props.t("actionFallback")}</div>
          </section>
          <section className="card">
            <div className="card-h"><h3><Mail className="i" />{props.t("caseSources")}</h3></div>
            {(detail?.messages ?? []).length === 0 ? <p className="empty">{props.t("timelineEmpty")}</p> : detail?.messages?.map((message) => (
              <button key={message.id} type="button" className="src" onClick={() => props.onOpenMail(message.id)}>
                <Mail className="i" />
                <div className="src-text">
                  <div className="sj">{cleanDisplayText(message.subject) || cleanDisplayText(message.snippet)}</div>
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

function Tab({ icon, helpKey, label, on, onClick }: { icon: ReactNode; helpKey?: string; label: string; on: boolean; onClick: () => void }) {
  return (
    <button type="button" className={on ? "on" : undefined} data-help-key={helpKey} onClick={onClick}>
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

function intentLabels(t: (key: NxKey, vars?: Record<string, string | number>) => string, intent: AskResult["intent"]): string[] {
  const labels = intent.areas.map((area) => areaLabel(t, area));
  if (intent.time === "today") labels.push(t("askTimeToday"));
  if (intent.time === "tomorrow") labels.push(t("askTimeTomorrow"));
  if (intent.time === "week") labels.push(t("askTimeWeek"));
  if (intent.time === "overdue") labels.push(t("askTimeOverdue"));
  if (intent.time === "month") labels.push(t("askTimeMonth"));
  if (intent.status === "open") labels.push(t("askStatusOpen"));
  if (intent.status === "done") labels.push(t("askStatusDone"));
  if (intent.amount !== null) labels.push(`$${intent.amount.toFixed(2)}`);
  return labels;
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
