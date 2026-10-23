// Contraste del semáforo de /admin (WCAG AA ≥ 4.5:1) en VERIFICANDO, VERDE, AMARILLO y ROJO,
// y que el panel claro no herede el texto casi blanco del tema oscuro (--a-text).
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const css = readFileSync(new URL("../app/admin/admin.css", import.meta.url), "utf8");

function rule(selector: string): Record<string, string> {
  const esc = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const m = css.match(new RegExp(`(^|\\n|\\})\\s*${esc}\\s*\\{([^}]*)\\}`));
  assert.ok(m, `falta la regla ${selector}`);
  const out: Record<string, string> = {};
  for (const d of m[2].split(";")) {
    const [k, ...v] = d.split(":");
    if (k && v.length) out[k.trim()] = v.join(":").trim();
  }
  return out;
}
function lum(hex: string): number {
  const h = hex.replace("#", "");
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16) / 255)
    .map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
export function ratio(a: string, b: string): number {
  const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p);
  return (x + 0.05) / (y + 0.05);
}
const hex = (v: string | undefined, what: string) => {
  assert.match(v ?? "", /^#[0-9a-f]{6}$/i, `${what}: color explícito en hex, no heredado (${v})`);
  return v as string;
};

const STATES = ["verificando", "verde", "amarillo", "rojo"];
export const measured: Array<[string, number]> = [];
function check(name: string, fg: string, bg: string) {
  const r = ratio(fg, bg);
  measured.push([name, Math.round(r * 100) / 100]);
  assert.ok(r >= 4.5, `${name}: ${r.toFixed(2)} < 4.5`);
}

test("cada estado define fondo y texto explícitos con AA", () => {
  for (const s of STATES) {
    const r = rule(`.dx-health--${s}`);
    const bg = hex(r.background, `${s} fondo`);
    check(`${s}: texto`, hex(r.color, `${s} texto`), bg);
    check(`${s}: nota`, hex(rule(".dx-health__note").color, "nota"), bg);
    check(`${s}: meta`, hex(rule(".dx-health__meta").color, "meta"), bg);
    check(`${s}: política`, hex(rule(".dx-health__policy").color, "política"), bg);
    check(`${s}: títulos`, hex(rule(".dx-health__detail h3").color, "h3"), bg);
    const label = s === "verificando" ? rule(".dx-health__label") : rule(`.dx-health--${s} .dx-health__label`);
    check(`${s}: etiqueta`, hex(label.color, "etiqueta"), bg);
    check(`${s}: botón`, hex(rule(".dx-health .dx-admin__btn, .dx-health .dx-admin__btn--ghost").color, "botón"), "#ffffff");
  }
});

test("tarjetas de incidentes y comprobaciones con AA (incluye enlaces)", () => {
  const li = rule(".dx-health__list li");
  check("tarjeta base", hex(li.color, "li"), hex(li.background, "li fondo"));
  const ok = rule(".dx-health__list li.is-ok");
  check("tarjeta ok", hex(ok.color, "ok"), hex(ok.background, "ok fondo"));
  const f = rule(".dx-health__list li.is-falla");
  check("tarjeta falla", hex(f.color, "falla"), hex(f.background, "falla fondo"));
  const d = rule(".dx-health__list li.is-degradado, .dx-health__list li.is-sin_verificar");
  check("tarjeta degradado/sin verificar", hex(d.color, "degradado"), hex(d.background, "degradado fondo"));
  const a = hex(rule(".dx-health a, .dx-health__list li a").color, "enlace");
  for (const bg of [li.background, f.background, d.background]) check(`enlace sobre ${bg}`, a, bg);
});

test("el panel no usa opacity para atenuar texto ni hereda --a-text", () => {
  const block = css.slice(css.indexOf(".dx-health {"), css.indexOf("@keyframes dx-health-pulse"));
  assert.doesNotMatch(block, /opacity:\s*0\.[0-9]/);
  assert.doesNotMatch(block, /var\(--a-text\)|var\(--a-muted\)/);
  assert.match(rule(".dx-health").color, /^#111827$/);
});

test.after(() => { console.log("CONTRASTE " + JSON.stringify(measured)); });
