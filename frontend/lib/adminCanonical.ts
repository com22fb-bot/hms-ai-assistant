/**
 * Canonical admin lives on the marketing host. The product app keeps `/`.
 * Worker path routes (not this module) are what actually serve `/admin` on www.
 */

export const PRODUCT_APP_ORIGIN = "https://app.donexto.com";
export const CANONICAL_ADMIN_ORIGIN = "https://www.donexto.com";
export const PRODUCT_APP_HOST = "app.donexto.com";

export type BrowserLocation = {
  origin: string;
  hostname: string;
  pathname: string;
};

export function hostnameOf(hostHeader: string): string {
  const trimmed = hostHeader.trim().toLowerCase();
  if (trimmed.startsWith("[")) {
    const end = trimmed.indexOf("]");
    return end === -1 ? trimmed : trimmed.slice(0, end + 1);
  }
  return trimmed.split(":")[0] ?? "";
}

export function isAdminPath(pathname: string): boolean {
  return pathname === "/admin" || pathname.startsWith("/admin/");
}

/** HTTP target for app.donexto.com/admin → www. Null means serve the request. */
export function canonicalAdminRedirectTarget(
  hostHeader: string,
  pathname: string,
  search = "",
): string | null {
  if (hostnameOf(hostHeader) !== PRODUCT_APP_HOST) {
    return null;
  }
  if (!isAdminPath(pathname)) {
    return null;
  }
  const query = search
    ? search.startsWith("?")
      ? search
      : `?${search}`
    : "";
  return `${CANONICAL_ADMIN_ORIGIN}${pathname}${query}`;
}

export function authReturnUrl(location: BrowserLocation): string {
  if (!isAdminPath(location.pathname)) {
    return `${location.origin}/`;
  }
  if (hostnameOf(location.hostname) === PRODUCT_APP_HOST) {
    return `${CANONICAL_ADMIN_ORIGIN}/admin`;
  }
  return `${location.origin}/admin`;
}

export function verifyEmailRedirectUrl(location: BrowserLocation): string {
  const url = new URL(authReturnUrl(location));
  url.searchParams.set("donexto_verify", "1");
  return url.toString();
}

type HostCondition = { type: "host"; value: string };

export type AdminRedirectRule = {
  source: string;
  has: HostCondition[];
  destination: string;
  permanent: true;
};

/** 308 from the product host. www and the apex serve the panel in place. */
export function appHostAdminRedirects(): AdminRedirectRule[] {
  return [
    {
      source: "/admin",
      has: [{ type: "host", value: PRODUCT_APP_HOST }],
      destination: `${CANONICAL_ADMIN_ORIGIN}/admin`,
      permanent: true,
    },
    {
      source: "/admin/:path*",
      has: [{ type: "host", value: PRODUCT_APP_HOST }],
      destination: `${CANONICAL_ADMIN_ORIGIN}/admin/:path*`,
      permanent: true,
    },
  ];
}
