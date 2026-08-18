/** Supabase Auth no trae Yahoo de fábrica. Se agrega como proveedor custom. */
export const YAHOO_CUSTOM_PROVIDER = "custom:yahoo" as const;

export const YAHOO_SUPABASE_CALLBACK =
  "https://tgirnpystoydvbxlvlzz.supabase.co/auth/v1/callback";

export const YAHOO_PROVIDER_SETUP_MESSAGE =
  "Yahoo no es un proveedor nativo de Supabase (por eso salió el JSON). " +
  "En Authentication → Sign In / Providers → New Provider crea custom:yahoo " +
  "(OAuth2) con Client ID y Secret de developer.yahoo.com. " +
  "Authorization: https://api.login.yahoo.com/oauth2/request_auth · " +
  "Token: https://api.login.yahoo.com/oauth2/get_token · " +
  "UserInfo: https://api.login.yahoo.com/openid/v1/userinfo · " +
  `Callback: ${YAHOO_SUPABASE_CALLBACK} · Scopes: openid email profile.`;
