// Cabeceras de seguridad para app.donexto.com y www.donexto.com/admin.
// La CSP va en Report-Only: el navegador avisa en consola sin bloquear nada.
// Cuando no haya avisos se puede pasar a Content-Security-Policy.

export const APP_CSP = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob: https:",
  "font-src 'self' data:",
  "connect-src 'self' https://*.supabase.co wss://*.supabase.co",
  "frame-src 'self' about: blob: data:",
  "worker-src 'self' blob:",
  "manifest-src 'self'",
  "form-action 'self' https://accounts.google.com https://login.microsoftonline.com https://api.login.yahoo.com",
  "base-uri 'self'",
  "object-src 'none'",
  "frame-ancestors 'self'",
].join("; ");

export const SECURITY_HEADERS = [
  {
    key: "Strict-Transport-Security",
    value: "max-age=31536000; includeSubDomains",
  },
  { key: "X-Frame-Options", value: "SAMEORIGIN" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  {
    key: "Permissions-Policy",
    value:
      "camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()",
  },
  { key: "Content-Security-Policy-Report-Only", value: APP_CSP },
];
