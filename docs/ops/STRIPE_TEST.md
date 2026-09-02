# Stripe Test — Plan Normal $19.99

No se commitean secretos. Tras mergear este PR, en el servicio
`hms-ai-assistant-production` de Railway:

```text
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PRICE_NORMAL_MONTHLY=price_...
STRIPE_SUCCESS_URL=https://app.donexto.com/?donexto=billing_ok
STRIPE_CANCEL_URL=https://app.donexto.com/?donexto=billing_cancel
```

- Solo Test Mode (`sk_test_`). Una clave `sk_live_` responde 503.
- Crea un Price de suscripción **USD 19.99 / month** en Stripe Test y pega el `price_…`.
- Sin esas variables, `GET /billing/plan` y `POST /billing/checkout` responden 503 con `falta STRIPE_SECRET_KEY en Railway` (o el precio). La app muestra ese texto; no finge un pago.
- No hay PayPal ni Stripe Live en este PR.
