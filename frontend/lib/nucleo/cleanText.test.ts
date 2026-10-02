import assert from "node:assert/strict";
import test from "node:test";

import { cleanDisplayText, stripCssNoise } from "./cleanText.ts";

const AZURE =
  "table {width:640px} body[data-outlook-cycle] .container-wide .main-container > table {width:888px} } " +
  "@media only screen and (max-width: 640px) { .outer-wrapper {width:100% !important} .inner {padding:0} } " +
  "Tu factura de Azure está lista. Revisa el cobro de $12.40.";

test("cleanText: Azure email CSS is removed, the sentence stays", () => {
  assert.equal(stripCssNoise(AZURE), "Tu factura de Azure está lista. Revisa el cobro de $12.40.");
});

test("cleanText: a title that is only (truncated) CSS falls back", () => {
  assert.equal(stripCssNoise(AZURE.slice(0, 150)), "");
  assert.equal(cleanDisplayText(AZURE.slice(0, 150), "Microsoft Azure"), "Microsoft Azure");
  assert.equal(cleanDisplayText("table {width:640px} body[data-outlook-cycle] .container-wide", "—"), "—");
});

test("cleanText: normal text is left alone", () => {
  for (const text of [
    "Reunión a las 10:30 a.m. con el cliente.",
    "Tu pedido llega el jueves: $58.47.",
    "Hola Maya. Tu código es 123456.",
    "Re: Factura #4411 (marzo)",
  ]) {
    assert.equal(stripCssNoise(text), text);
  }
  assert.equal(stripCssNoise("Pedido {123} listo"), "Pedido 123 listo");
  assert.equal(stripCssNoise(null), "");
});

test("cleanText: Outlook class rules and entities", () => {
  assert.equal(
    stripCssNoise(".ExternalClass {width:100%} .ExternalClass p, .ExternalClass span {line-height:100%} Your Microsoft Azure invoice"),
    "Your Microsoft Azure invoice",
  );
});
