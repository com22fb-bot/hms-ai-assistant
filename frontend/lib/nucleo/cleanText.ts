/**
 * Defensive clean-up for text derived from HTML emails (titles, summaries,
 * previews). Some senders (e.g. Microsoft/Azure newsletters) put CSS in the
 * body, and naive tag stripping leaves "table {width:640px} @media …" as the
 * preview. This removes CSS rules, @media blocks, comments and stray braces.
 * Mirrors backend/app/utils/html_text.py::strip_css_noise.
 */

const TAGS = new Set([
  "html", "body", "table", "tbody", "thead", "tfoot", "tr", "td", "th", "div", "span", "p", "a",
  "img", "ul", "ol", "li", "h1", "h2", "h3", "h4", "h5", "h6", "center", "font", "b", "i", "u",
  "strong", "em", "section", "header", "footer", "main", "article", "nav", "sup", "sub", "hr",
  "br", "blockquote", "pre", "code", "input", "button", "form", "label", "o", "v", "*",
]);
const MEDIA_WORDS = new Set(["only", "screen", "and", "not", "print", "all", "speech", "or", ">", "+", "~", ","]);

function selectorToken(token: string): boolean {
  const lower = token.toLowerCase();
  if (TAGS.has(lower) || MEDIA_WORDS.has(lower)) return true;
  if (/^[\w-]+:[\w-]+$/.test(lower) && !/^https?:/.test(lower)) return true; // a:hover, o:p
  return /[.#[\]>:*+~@(),]/.test(token) && !/[a-z]{3,}[.?!]$/i.test(token);
}

/** Drops trailing selector-looking tokens from `prefix` (the text before a `{`). */
function trimSelector(prefix: string): string {
  const parts = prefix.split(/(\s+)/);
  let end = parts.length;
  while (end > 0) {
    const token = parts[end - 1];
    if (!token.trim()) {
      end -= 1;
      continue;
    }
    if (!selectorToken(token)) break;
    end -= 1;
  }
  return parts.slice(0, end).join("");
}

function looksLikeDeclarations(inner: string): boolean {
  const body = inner.trim();
  if (!body) return true;
  return /^(?:\s*[-\w]+\s*:\s*[^;{}]*;?)+\s*$/.test(body);
}

export function stripCssNoise(input: string | null | undefined): string {
  if (!input) return "";
  let text = String(input)
    .replace(/\/\*[\s\S]*?\*\//g, " ")
    .replace(/<!--|-->/g, " ")
    .replace(/&nbsp;/gi, " ")
    .replace(/&amp;/gi, "&")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .replace(/&quot;/gi, '"')
    .replace(/&#39;/g, "'");
  if (!/[{}]/.test(text)) return text.replace(/\s+/g, " ").trim();
  for (let guard = 0; guard < 50; guard++) {
    const match = /\{([^{}]*)\}/.exec(text);
    if (!match) break;
    const before = text.slice(0, match.index);
    const after = text.slice(match.index + match[0].length);
    if (looksLikeDeclarations(match[1])) {
      text = `${trimSelector(before)} ${after}`;
    } else {
      // Not CSS: keep the content, drop only the braces.
      text = `${before} ${match[1]} ${after}`;
    }
  }
  // Unterminated trailing rule ("… { .outer-wrapper {width:100%" cut at 500 chars).
  for (let guard = 0; guard < 10; guard++) {
    const open = text.lastIndexOf("{");
    if (open < 0) break;
    const rest = text.slice(open + 1);
    const restTokens = rest.split(/\s+/).filter(Boolean);
    const cssRest = restTokens.every((token) => selectorToken(token) || /[:;]/.test(token) || /^[\d.]+(?:px|em|rem|%)?;?$/.test(token) || /^!important/.test(token));
    text = cssRest ? trimSelector(text.slice(0, open)) : `${text.slice(0, open)} ${rest}`;
  }
  // Leftover "@media … " preludes and stray braces.
  text = text.replace(/(?:^|\s)@(?:media|font-face|import|supports|keyframes|page)\b[^{}]*?(?=$|[A-ZÁÉÍÓÚÑ¿¡])/g, " ").replace(/[{}]/g, " ");
  text = text.replace(/\s+/g, " ").trim();
  // What is left after removing rules is only selectors ("body[data-x] .container-wide").
  const rest = text.split(" ").filter(Boolean);
  if (rest.length && rest.every(selectorToken) && rest.some((token) => /[.#[\]>]/.test(token))) return "";
  return text;
}

/** Clean display text, falling back when nothing readable is left. */
export function cleanDisplayText(value: string | null | undefined, fallback = ""): string {
  const clean = stripCssNoise(value);
  return clean.length >= 2 ? clean : fallback;
}
