"use client";

import Image from "next/image";
import {
  Check,
  GitCompareArrows,
  Info,
  LoaderCircle,
  Mail,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import { useState } from "react";

import { hmsJson } from "@/lib/hmsApi";


type Category = {
  key: string;
  label: string;
  count: number;
  count_source: "profile" | "label" | "query_estimate";
  sensitive: boolean;
};

type Inventory = {
  email: string;
  messages_total: number;
  threads_total: number;
  categories: Category[];
  notice: string;
};

type Preview = {
  selected: string[];
  query: string;
  unique_estimate: number;
  notice: string;
};

type Comparison = {
  status: string;
  mode: "read_only_comparison";
  snapshot_at: string;
  email: string;
  history_id: string;
  account_id: string;
  gmail: {
    profile_total: number;
    listed_rows: number;
    unique_ids: number;
    profile_matches_list: boolean;
    duplicate_ids: string[];
  };
  hms: {
    stored_rows: number;
    unique_ids: number;
    duplicate_ids: string[];
  };
  comparison: {
    present_in_both: number;
    missing_in_hms: number;
    only_in_hms: number;
  };
  ids: {
    missing_in_hms: string[];
    only_in_hms: string[];
    duplicate_in_gmail: string[];
    duplicate_in_hms: string[];
  };
  notice: string;
};

const API = "/api/hms/gmail/import";

function readableError(reason: unknown, fallback: string) {
  return reason instanceof Error ? reason.message : fallback;
}

export function GuidedImportWizard({
  onClose,
}: {
  onClose: () => void;
}) {
  const [inventory, setInventory] = useState<Inventory | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [loadingInventory, setLoadingInventory] = useState(false);
  const [calculating, setCalculating] = useState(false);
  const [comparing, setComparing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadInventory() {
    setLoadingInventory(true);
    setError(null);

    try {
      const data = await hmsJson<Inventory>(
        `${API}/inventory`,
        { cache: "no-store" },
      );
      setInventory(data);
      setSelected([]);
      setPreview(null);
      setComparison(null);
    } catch (reason) {
      setError(
        readableError(
          reason,
          "No fue posible contar el buzón de Gmail.",
        ),
      );
    } finally {
      setLoadingInventory(false);
    }
  }

  function toggle(key: string) {
    setPreview(null);

    if (key === "all") {
      setSelected((current) =>
        current.includes("all") ? [] : ["all"],
      );
      return;
    }

    setSelected((current) =>
      current.includes(key)
        ? current.filter((item) => item !== key)
        : [
            ...current.filter((item) => item !== "all"),
            key,
          ],
    );
  }

  async function calculatePreview() {
    setCalculating(true);
    setError(null);

    try {
      if (selected.includes("all")) {
        if (!inventory) {
          throw new Error(
            "El inventario todavía no está disponible.",
          );
        }

        setPreview({
          selected: ["all"],
          query: "in:anywhere",
          unique_estimate: inventory.messages_total,
          notice:
            "Conteo total exacto reportado por Gmail.",
        });
        return;
      }

      const data = await hmsJson<Preview>(
        `${API}/preview`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ categories: selected }),
        },
      );
      setPreview(data);
    } catch (reason) {
      setError(
        readableError(
          reason,
          "No fue posible calcular la selección única.",
        ),
      );
    } finally {
      setCalculating(false);
    }
  }

  async function compareWithHms() {
    setComparing(true);
    setError(null);

    try {
      const data = await hmsJson<Comparison>(
        `${API}/compare`,
        { cache: "no-store" },
      );
      setComparison(data);
    } catch (reason) {
      setError(
        readableError(
          reason,
          "No fue posible comparar Gmail con HMS.",
        ),
      );
    } finally {
      setComparing(false);
    }
  }

  function saveComparisonReport() {
    if (!comparison) {
      return;
    }

    const blob = new Blob(
      [JSON.stringify(comparison, null, 2)],
      { type: "application/json" },
    );
    const href = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    const stamp = comparison.snapshot_at
      .replace(/[:.]/g, "-")
      .replace(/\+00:00$/, "Z");

    anchor.href = href;
    anchor.download = `hms-comparador-gmail-${stamp}.json`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(href);
  }

  return (
    <div
      className="hms-import-backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="hms-import-title"
    >
      <section className="hms-import-modal">
        <button
          className="hms-import-close"
          type="button"
          onClick={onClose}
          aria-label="Cerrar inventario"
        >
          <X size={22} />
        </button>

        <div className="hms-import-hero">
          <Image
            src="/hms-import-robot.png"
            alt="Robot HMS organizando documentos en una laptop"
            width={1536}
            height={1024}
            priority
            sizes="(max-width: 720px) 100vw, 420px"
          />

          <div>
            <span>INVENTARIO PREVIO A LA IMPORTACIÓN</span>
            <h2 id="hms-import-title">
              Primero revisamos. Después tú decides.
            </h2>
            <p>
              HMS contará el buzón y calculará una selección sin
              importar, borrar, archivar ni modificar correos.
            </p>
          </div>
        </div>

        {!inventory ? (
          <div className="hms-import-empty">
            <ShieldCheck size={34} />
            <h3>Revisión segura del buzón</h3>
            <p>
              La consulta utiliza la conexión autorizada con Google.
              HMS nunca solicitará la contraseña de Gmail.
            </p>
            <button
              type="button"
              disabled={loadingInventory}
              onClick={() => void loadInventory()}
            >
              {loadingInventory ? (
                <LoaderCircle className="app-spin" size={20} />
              ) : (
                <RefreshCw size={20} />
              )}
              {loadingInventory
                ? "Contando registros…"
                : "Contar mi buzón"}
            </button>
          </div>
        ) : null}

        {error ? (
          <div className="hms-import-error" role="alert">
            {error}
          </div>
        ) : null}

        {inventory ? (
          <>
            <div className="hms-import-account">
              <Mail size={18} />
              <div>
                <strong>{inventory.email}</strong>
                <span>
                  {inventory.messages_total.toLocaleString()} mensajes
                  {" · "}
                  {inventory.threads_total.toLocaleString()} conversaciones
                </span>
              </div>
            </div>

            <div className="hms-import-comparator-actions">
              <button
                type="button"
                disabled={comparing}
                onClick={() => void compareWithHms()}
              >
                {comparing ? (
                  <LoaderCircle className="app-spin" size={19} />
                ) : (
                  <GitCompareArrows size={19} />
                )}
                {comparing
                  ? "Comparando identificadores…"
                  : comparison
                    ? "Repetir comparación"
                    : "Comparar Gmail con HMS"}
              </button>

              {comparison ? (
                <button
                  type="button"
                  className="secondary"
                  onClick={saveComparisonReport}
                >
                  Guardar reporte JSON
                </button>
              ) : null}
            </div>

            {comparison ? (
              <section className="hms-import-comparison" aria-live="polite">
                <header>
                  <div>
                    <span>COMPARACIÓN POR IDENTIFICADORES ÚNICOS</span>
                    <h3>Gmail frente a HMS</h3>
                  </div>
                  <small>
                    {new Date(comparison.snapshot_at).toLocaleString()}
                  </small>
                </header>

                <div className="hms-import-comparison-grid">
                  <article>
                    <span>Gmail reportado</span>
                    <strong>
                      {comparison.gmail.profile_total.toLocaleString()}
                    </strong>
                    <small>
                      {comparison.gmail.profile_matches_list
                        ? "Coincide con la lista completa"
                        : `La lista devolvió ${comparison.gmail.unique_ids.toLocaleString()} IDs`}
                    </small>
                  </article>

                  <article>
                    <span>Almacenados en HMS</span>
                    <strong>
                      {comparison.hms.unique_ids.toLocaleString()}
                    </strong>
                    <small>IDs únicos existentes</small>
                  </article>

                  <article>
                    <span>Presentes en ambos</span>
                    <strong>
                      {comparison.comparison.present_in_both.toLocaleString()}
                    </strong>
                    <small>Coincidencias exactas</small>
                  </article>

                  <article className="is-warning">
                    <span>Faltan en HMS</span>
                    <strong>
                      {comparison.comparison.missing_in_hms.toLocaleString()}
                    </strong>
                    <small>Serían candidatos para importar</small>
                  </article>

                  <article className="is-neutral">
                    <span>Solo existen en HMS</span>
                    <strong>
                      {comparison.comparison.only_in_hms.toLocaleString()}
                    </strong>
                    <small>No se borrarán automáticamente</small>
                  </article>

                  <article>
                    <span>Duplicados HMS</span>
                    <strong>
                      {comparison.ids.duplicate_in_hms.length.toLocaleString()}
                    </strong>
                    <small>Por ID externo de Gmail</small>
                  </article>
                </div>

                <p>{comparison.notice}</p>
              </section>
            ) : null}

            <div className="hms-import-grid">
              {inventory.categories.map((category) => (
                <label
                  key={category.key}
                  className={[
                    selected.includes(category.key)
                      ? "is-selected"
                      : "",
                    category.sensitive
                      ? "is-sensitive"
                      : "",
                  ].filter(Boolean).join(" ")}
                >
                  <input
                    type="checkbox"
                    checked={selected.includes(category.key)}
                    onChange={() => toggle(category.key)}
                  />

                  <span className="hms-import-check">
                    {selected.includes(category.key) ? (
                      <Check size={16} />
                    ) : null}
                  </span>

                  <span>
                    <strong>{category.label}</strong>
                    <small>
                      {category.sensitive
                        ? "Contenido sensible · "
                        : ""}
                      {category.count_source === "query_estimate"
                        ? "Estimación de Gmail"
                        : "Conteo reportado por Gmail"}
                    </small>
                  </span>

                  <b>{category.count.toLocaleString()}</b>
                </label>
              ))}
            </div>

            <div className="hms-import-notice">
              <Sparkles size={20} />
              <p>
                La primera importación traerá únicamente lo aprobado.
                Después HMS sincronizará mensajes nuevos y evitará
                duplicados. Esa importación todavía está bloqueada.
              </p>
            </div>

            {preview ? (
              <div className="hms-import-preview">
                <span>
                  {preview.selected.includes("all")
                    ? "Total exacto seleccionado"
                    : "Total único estimado"}
                </span>
                <strong>
                  {preview.unique_estimate.toLocaleString()}
                </strong>
                <small>
                  {preview.selected.includes("all")
                    ? "Este total corresponde al conteo completo reportado por Gmail."
                    : "Los mensajes presentes en varias categorías se cuentan una sola vez. Esta cifra es la estimación reportada por Gmail."}
                </small>
              </div>
            ) : null}

            <div className="hms-import-review-lock">
              <Info size={20} />
              <div>
                <strong>Importación bloqueada por seguridad</strong>
                <span>
                  Revisaremos estos conteos antes de limpiar datos
                  históricos o iniciar cualquier importación.
                </span>
              </div>
            </div>

            <div className="hms-import-actions">
              <button
                type="button"
                className="secondary"
                onClick={onClose}
              >
                Cerrar
              </button>

              <button
                type="button"
                disabled={!selected.length || calculating}
                onClick={() => void calculatePreview()}
              >
                {calculating ? (
                  <LoaderCircle className="app-spin" size={19} />
                ) : null}
                {calculating
                  ? "Calculando…"
                  : preview
                    ? "Recalcular selección"
                    : "Calcular selección única"}
              </button>
            </div>
          </>
        ) : null}
      </section>
    </div>
  );
}
