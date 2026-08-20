"""
Catálogo canónico de clasificación Donexto.

Las claves de triage en base de datos no cambian. Los verticales
(bancos, pedidos, reservas, social, publicidad) dicen QUÉ es el
correo; el triage dice SI hay que actuar ahora, después o en silencio.

Producto: México y Estados Unidos primero. Canadá, UE y LATAM
entran en las bases de remitentes aunque el país aún no esté a la venta.
"""

from __future__ import annotations

from typing import Any

TRIAGE_KEYS = (
    "action_required",
    "notice",
    "review",
    "waiting_external",
    "informational",
    "promotional",
    "social",
    "automated",
    "unreviewed",
)

N1_KEYS = ("action_required", "notice", "review")
N2_KEYS = ("waiting_external", "informational")
N3_KEYS = ("social", "promotional", "automated")

TRIAGE_CATALOG: dict[str, dict[str, Any]] = {
    "action_required": {
        "label_es": "Requieren atención",
        "n_level": "N1",
        "belongs": [
            "Una persona te pide algo concreto (enviar, confirmar, revisar).",
            "Pago, factura o colegiatura que tú debes cubrir.",
            "Seguimiento de un caso que ya está abierto.",
        ],
        "examples_mx": [
            "El colegio pide el comprobante de pago.",
            "Un cliente pide la factura CFDI.",
        ],
        "examples_us": [
            "Please confirm the meeting time.",
            "Invoice due — please send payment.",
        ],
        "does_not_belong": [
            "Alertas automáticas de banco o paquete (eso es notice).",
            "Likes, follows o resúmenes de LinkedIn (eso es social).",
        ],
    },
    "notice": {
        "label_es": "Avisos importantes",
        "n_level": "N1",
        "belongs": [
            "Bancos: cargos, depósitos, SPEI, estados de cuenta, 2FA, fraude.",
            "Pedidos y compras: orden confirmada, enviado, entregado, reembolso.",
            "Reservas y viajes: confirmación, check-in, cambio de vuelo, boarding pass.",
            "Seguridad de cuentas: nuevo dispositivo, reset de contraseña, código.",
            "Plazos y cortes de servicio (CFE, internet, suscripción que vence).",
        ],
        "examples_mx": [
            "Citibanamex: alerta de compra o estado de cuenta.",
            "Mercado Libre: tu paquete ya va en camino.",
            "Aeroméxico: tu reservación está confirmada.",
        ],
        "examples_us": [
            "Chase: your statement is ready / unusual sign-in.",
            "Amazon: your order has shipped.",
            "United: check-in is now open.",
        ],
        "does_not_belong": [
            "Ofertas de tarjeta, millas o 'hasta 40% off' del mismo banco o tienda (publicidad).",
            "Notificaciones de redes (social).",
        ],
    },
    "review": {
        "label_es": "Revisión humana",
        "n_level": "N1",
        "belongs": [
            "Correo personal ambiguo: no está claro si hay que actuar.",
            "Donexto no debe decidir solo.",
        ],
        "examples_mx": ["Un conocido escribe sin pedir nada concreto."],
        "examples_us": ["A personal note without a clear ask."],
        "does_not_belong": ["Bancos, pedidos o redes ya identificados."],
    },
    "waiting_external": {
        "label_es": "Esperando respuesta",
        "n_level": "N2",
        "belongs": ["Tú ya respondiste; el siguiente paso es de la otra parte."],
        "examples_mx": ["Enviaste la cotización y esperas al cliente."],
        "examples_us": ["You replied; waiting on the vendor."],
        "does_not_belong": ["Correo nuevo de un banco o una tienda."],
    },
    "informational": {
        "label_es": "Informativos",
        "n_level": "N2",
        "belongs": [
            "Útil, sin acción ni plazo.",
            "Foros, acuses, copias de mensajes enviados sin caso abierto.",
        ],
        "examples_mx": ["Acuse de recibo sin siguiente paso."],
        "examples_us": ["FYI thread with no ask."],
        "does_not_belong": ["Estados de cuenta, tracking, boarding pass."],
    },
    "social": {
        "label_es": "Redes sociales",
        "n_level": "N3",
        "belongs": [
            "LinkedIn, Facebook, Instagram, X, TikTok, YouTube, Reddit, Pinterest, Snapchat, WhatsApp Business masivo, Threads, Twitch.",
            "Likes, comentarios, alguien empezó a seguirte, resúmenes semanales, 'people you may know'.",
        ],
        "examples_mx": ["LinkedIn: 12 personas vieron tu perfil."],
        "examples_us": ["Instagram: John started following you."],
        "does_not_belong": [
            "Citibanamex, Banamex, Chase, BBVA ni ningún banco (aunque el dominio contenga x.com).",
            "Amazon, Mercado Libre, aerolíneas, hoteles.",
            "Código de verificación o 'nuevo inicio de sesión' — eso es notice, aunque venga de una red.",
        ],
    },
    "promotional": {
        "label_es": "Publicidad",
        "n_level": "N3",
        "belongs": [
            "Newsletters, campañas, descuentos, vacantes masivas, 'hasta 40%'.",
            "Ofertas de banco o tienda (aumenta tu línea, Black Friday) cuando el remitente es marketing/ofertas.",
        ],
        "examples_mx": ["Liverpool: Hot Sale 50% en pantallas."],
        "examples_us": ["Chase marketing: earn 5% cash back this weekend."],
        "does_not_belong": [
            "Alerta de cargo, estado de cuenta, pedido enviado, boarding pass.",
        ],
    },
    "automated": {
        "label_es": "Automatizados",
        "n_level": "N3",
        "belongs": [
            "no-reply genérico sin banco/pedido/reserva detrás.",
            "Welcome/updates de un SaaS que no pide un acto.",
        ],
        "examples_mx": ["Bienvenido a una app nueva, sin código ni cargo."],
        "examples_us": ["Product updates from a tool you barely use."],
        "does_not_belong": [
            "no-reply@banamex.com con un cargo — sigue siendo notice (banco gana).",
        ],
    },
    "unreviewed": {
        "label_es": "Pendientes de clasificar",
        "n_level": "—",
        "belongs": ["Aún en el pipeline."],
        "examples_mx": [],
        "examples_us": [],
        "does_not_belong": [],
    },
}

VERTICALS: dict[str, dict[str, Any]] = {
    "bank": {
        "label_es": "Bancos, tarjetas y dinero",
        "triage_default": "notice",
        "triage_if_marketing": "promotional",
        "triage_if_action": "action_required",
        "includes": [
            "Bancos, fintech, tarjetas, SPEI, PayPal, Nu, Mercado Pago.",
            "Estados de cuenta, cargos, depósitos, 2FA bancario, fraude.",
        ],
        "regions": ["MX", "US", "CA", "EU", "LATAM", "GLOBAL"],
    },
    "commerce": {
        "label_es": "Pedidos y compras",
        "triage_default": "notice",
        "triage_if_marketing": "promotional",
        "triage_if_action": "action_required",
        "includes": [
            "Órdenes, envíos, entregas, devoluciones, reembolsos.",
            "Amazon, Mercado Libre, Walmart, Liverpool, DHL, UPS.",
        ],
        "regions": ["MX", "US", "CA", "EU", "LATAM", "GLOBAL"],
    },
    "travel": {
        "label_es": "Reservas y viajes",
        "triage_default": "notice",
        "triage_if_marketing": "promotional",
        "triage_if_action": "action_required",
        "includes": [
            "Vuelos, hoteles, Airbnb, Booking, autobús, rent a car, eventos.",
            "Confirmación, check-in, cambio de horario, boarding pass.",
        ],
        "regions": ["MX", "US", "CA", "EU", "LATAM", "GLOBAL"],
    },
    "social": {
        "label_es": "Redes sociales",
        "triage_default": "social",
        "triage_if_marketing": "social",
        "triage_if_action": "notice",
        "includes": ["Redes de difusión. Un 2FA o login raro se eleva a notice."],
        "regions": ["GLOBAL"],
    },
}

SECURITY_NOTICE_TERMS = (
    "security alert",
    "alerta de seguridad",
    "verify your email",
    "verifica tu correo",
    "confirm your email",
    "confirme la dirección de correo",
    "password reset",
    "restablecer contraseña",
    "contraseña restablecida",
    "verification code",
    "código de verificación",
    "codigo de verificacion",
    "one-time code",
    "one time password",
    "código de un solo uso",
    "nuevo inicio de sesión",
    "new sign-in",
    "new sign in",
    "unrecognized device",
    "dispositivo no reconocido",
    "nuevo dispositivo",
    "two-factor",
    "two factor",
    "autenticación en dos pasos",
    "clave dinámica",
    "cargo no reconocido",
    "unrecognized charge",
    "fraud",
    "fraude",
)
