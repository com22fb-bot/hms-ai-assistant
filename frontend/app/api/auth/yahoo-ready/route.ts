import { NextResponse } from "next/server";

import { YAHOO_CUSTOM_PROVIDER } from "@/lib/yahooAuth";

export async function GET() {
  const base = process.env.NEXT_PUBLIC_SUPABASE_URL?.replace(/\/$/, "");
  const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
  if (!base || !key) {
    return NextResponse.json({ ready: false, status: 0 });
  }

  const authorize = new URL(`${base}/auth/v1/authorize`);
  authorize.searchParams.set("provider", YAHOO_CUSTOM_PROVIDER);
  authorize.searchParams.set("redirect_to", "https://app.donexto.com/");

  try {
    const response = await fetch(authorize, {
      method: "GET",
      redirect: "manual",
      headers: {
        apikey: key,
        Authorization: `Bearer ${key}`,
      },
      cache: "no-store",
    });
    const ready = response.status >= 300 && response.status < 400;
    return NextResponse.json({ ready, status: response.status });
  } catch {
    return NextResponse.json({ ready: false, status: 0 });
  }
}
