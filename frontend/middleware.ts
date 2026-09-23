import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { canonicalAdminRedirectTarget } from "@/lib/adminCanonical";

/**
 * Edge middleware so OpenNext 1.20 (this repo's adapter) emits the redirect.
 * Next 16's proxy.ts runs on Node and that adapter still rejects it.
 */
export function middleware(request: NextRequest) {
  const target = canonicalAdminRedirectTarget(
    request.nextUrl.hostname || request.headers.get("host") || "",
    request.nextUrl.pathname,
    request.nextUrl.search,
  );
  if (!target) {
    return NextResponse.next();
  }
  return NextResponse.redirect(target, 308);
}

export const config = {
  matcher: ["/admin", "/admin/:path*"],
  runtime: "experimental-edge",
};
