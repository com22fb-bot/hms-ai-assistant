import { NextRequest, NextResponse } from "next/server";

type RouteContext = {
  params: Promise<{
    path: string[];
  }>;
};

const INTERNAL_API_BASE_URL =
  process.env.HMS_INTERNAL_API_BASE_URL?.replace(/\/$/, "") ??
  "http://127.0.0.1:8000";

async function proxy(
  request: NextRequest,
  context: RouteContext,
): Promise<NextResponse> {
  const { path } = await context.params;
  const target = new URL(
    `${INTERNAL_API_BASE_URL}/${path.join("/")}`,
  );

  target.search = request.nextUrl.search;

  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.delete("content-length");
  headers.delete("connection");
  // El navegador no puede fingir ser el Worker ni elegir su IP.
  headers.delete("x-donexto-proxy");
  headers.delete("x-donexto-client-ip");
  const proxySecret = process.env.HMS_PROXY_SECRET?.trim();
  if (proxySecret) {
    headers.set("x-donexto-proxy", proxySecret);
  }
  const visitorIp = request.headers.get("cf-connecting-ip")?.trim();
  if (visitorIp) {
    headers.set("x-donexto-client-ip", visitorIp);
  }

  const method = request.method.toUpperCase();
  const body =
    method === "GET" || method === "HEAD"
      ? undefined
      : await request.arrayBuffer();

  try {
    const response = await fetch(target, {
      method,
      headers,
      body,
      cache: "no-store",
      redirect: "manual",
    });

    const responseHeaders = new Headers(response.headers);
    responseHeaders.delete("content-encoding");
    responseHeaders.delete("content-length");

    return new NextResponse(response.body, {
      status: response.status,
      headers: responseHeaders,
    });
  } catch (error) {
    return NextResponse.json(
      {
        status: "error",
        message: "No fue posible comunicar con el backend interno.",
      },
      {
        status: 502,
      },
    );
  }
}

export async function GET(
  request: NextRequest,
  context: RouteContext,
) {
  return proxy(request, context);
}

export async function POST(
  request: NextRequest,
  context: RouteContext,
) {
  return proxy(request, context);
}

export async function PUT(
  request: NextRequest,
  context: RouteContext,
) {
  return proxy(request, context);
}

export async function PATCH(
  request: NextRequest,
  context: RouteContext,
) {
  return proxy(request, context);
}

export async function DELETE(
  request: NextRequest,
  context: RouteContext,
) {
  return proxy(request, context);
}
