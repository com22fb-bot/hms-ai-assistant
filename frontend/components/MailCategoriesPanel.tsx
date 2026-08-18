"use client";

import {
  AlertTriangle,
  BellRing,
  Bot,
  BriefcaseBusiness,
  CircleHelp,
  Info,
  LoaderCircle,
  Mail,
  Megaphone,
  RefreshCw,
  Send,
  Users,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { hmsJson } from "@/lib/hmsApi";


type TriageCategory = {
  key: string;
  count: number;
};

type TriageSummary = {
  status: string;
  total: number;
  categories: TriageCategory[];
};

const CATEGORY_ORDER = [
  "action_required",
  "waiting_external",
  "review",
  "notice",
  "social",
  "promotional",
  "automated",
  "informational",
  "unreviewed",
];

const CATEGORY_CONFIG: Record<
  string,
  {
    label: string;
    description: string;
    icon: typeof Mail;
    tone: string;
  }
> = {
  action_required: {
    label: "Requieren atención",
    description: "Solicitudes humanas que sí pueden convertirse en casos.",
    icon: BriefcaseBusiness,
    tone: "action",
  },
  waiting_external: {
    label: "Esperando respuesta",
    description: "Mensajes enviados dentro de un caso abierto.",
    icon: Send,
    tone: "waiting",
  },
  review: {
    label: "Revisión humana",
    description: "Mensajes personales ambiguos que Donexto no debe decidir solo.",
    icon: CircleHelp,
    tone: "review",
  },
  notice: {
    label: "Avisos importantes",
    description:
      "Bancos, pedidos, reservas, pagos, seguridad y plazos. Un Citibanamex no es una red social.",
    icon: BellRing,
    tone: "notice",
  },
  social: {
    label: "Redes sociales",
    description:
      "LinkedIn, Instagram, X, TikTok, YouTube. Likes y resúmenes — no bancos ni compras.",
    icon: Users,
    tone: "social",
  },
  promotional: {
    label: "Publicidad",
    description: "Promociones, vacantes masivas y campañas comerciales.",
    icon: Megaphone,
    tone: "promo",
  },
  automated: {
    label: "Automatizados",
    description: "Notificaciones automáticas sin solicitud humana directa.",
    icon: Bot,
    tone: "automated",
  },
  informational: {
    label: "Informativos",
    description: "Mensajes útiles que no requieren una acción inmediata.",
    icon: Info,
    tone: "info",
  },
  unreviewed: {
    label: "Pendientes de clasificar",
    description: "Mensajes que todavía no han terminado el proceso.",
    icon: AlertTriangle,
    tone: "pending",
  },
};

function errorMessage(reason: unknown): string {
  return reason instanceof Error
    ? reason.message
    : "No fue posible consultar las categorías del correo.";
}

export function MailCategoriesPanel({
  onOpenCategory,
}: {
  onOpenCategory: (category: string | null) => void;
}) {
  const [summary, setSummary] = useState<TriageSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadSummary = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await hmsJson<TriageSummary>(
        "/api/hms/messages/triage-summary?limit_per_category=1",
        { cache: "no-store" },
      );
      setSummary(data);
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadSummary();
    }, 0);
    const interval = window.setInterval(() => {
      if (document.visibilityState === "visible") {
        void loadSummary();
      }
    }, 30000);

    const refresh = () => {
      void loadSummary();
    };
    window.addEventListener("hms:classification-complete", refresh);
    window.addEventListener("hms:data-changed", refresh);

    return () => {
      window.clearTimeout(timer);
      window.clearInterval(interval);
      window.removeEventListener("hms:classification-complete", refresh);
      window.removeEventListener("hms:data-changed", refresh);
    };
  }, [loadSummary]);

  const categories = useMemo(() => {
    const rows = summary?.categories ?? [];
    const byKey = new Map(rows.map((item) => [item.key, item]));

    return CATEGORY_ORDER.map((key) =>
      byKey.get(key) ?? { key, count: 0 },
    );
  }, [summary]);

  return (
    <section className="hms-mail-categories">
      <header className="hms-mail-categories-heading">
        <div>
          <span>CLASIFICACIÓN DEL CORREO</span>
          <h2>Cada mensaje en su lugar</h2>
          <p>
            Correos conserva todo el inventario descargado. Casos muestra
            únicamente lo que requiere atención.
          </p>
        </div>

        <div className="hms-mail-category-actions">
          <button
            type="button"
            className="secondary"
            onClick={() => onOpenCategory(null)}
          >
            <Mail size={19} />
            Ver todos los correos
          </button>
          <button
            type="button"
            onClick={() => void loadSummary()}
            disabled={loading}
          >
            {loading ? (
              <LoaderCircle className="app-spin" size={19} />
            ) : (
              <RefreshCw size={19} />
            )}
            Actualizar
          </button>
        </div>
      </header>

      {error ? (
        <div className="hms-mail-categories-error" role="alert">
          <AlertTriangle size={19} />
          {error}
        </div>
      ) : null}

      <div className="hms-mail-category-total">
        <Mail size={22} />
        <span>Todos los correos descargados</span>
        <strong>{(summary?.total ?? 0).toLocaleString()}</strong>
      </div>

      <div className="hms-mail-category-grid">
        {categories.map((category) => {
          const config = CATEGORY_CONFIG[category.key];
          const Icon = config.icon;

          return (
            <button
              key={category.key}
              type="button"
              className={`hms-mail-category-card tone-${config.tone}`}
              onClick={() => onOpenCategory(category.key)}
            >
              <span className="hms-mail-category-icon">
                <Icon size={22} />
              </span>
              <span className="hms-mail-category-copy">
                <strong>{config.label}</strong>
                <small>{config.description}</small>
              </span>
              <b>{category.count.toLocaleString()}</b>
            </button>
          );
        })}
      </div>
    </section>
  );
}
