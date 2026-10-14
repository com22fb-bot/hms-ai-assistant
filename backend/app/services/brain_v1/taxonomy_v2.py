"""Taxonomía v2 (ASTRA, 13-oct-2026, aprobada por Héctor). Solo la usa el cerebro v1 (BRAIN_V1_ENABLED).

- 7 áreas temáticas en 3 sombreros (Ocupación · Hogar · Personal).
- Seguridad NO es área: es la señal transversal ``security_flag`` (N1/N2) + etiquetas de seguridad.
- "Por revisar" es un estado: ``area = None`` con ``review_reason``. No existe "Otros".
- Etiquetas de vocabulario cerrado: una etiqueta que no está en el catálogo del área elegida se descarta.
Ver docs/TAXONOMIA_V2.md.
"""
from __future__ import annotations

import re
from typing import Any

AREAS = {
    "trabajo": "Trabajo y negocios",
    "hogar": "Hogar y familia",
    "dinero": "Dinero y facturas",
    "compras": "Compras y suscripciones",
    "salud": "Salud y seguros",
    "viajes": "Viajes y eventos",
    "promociones": "Promociones y social",
}
HATS = {"trabajo": "ocupacion", "hogar": "hogar", "dinero": "hogar", "compras": "hogar",
        "salud": "personal", "viajes": "personal", "promociones": "personal"}

CATALOG: dict[str, tuple[str, ...]] = {
    "trabajo": ("Clientes", "Prospectos y ventas", "Proveedores", "Proyectos", "Contratos", "Facturación empresarial",
                "Cobros empresariales", "Gastos empresariales", "Contabilidad y auditoría", "Nómina laboral",
                "Recursos humanos", "Empleo y contratación", "Reuniones y tareas", "Legal y cumplimiento",
                "Sistemas y soporte laboral", "Licencias y permisos comerciales", "Logística y operaciones",
                "Socios e inversionistas"),
    "hogar": ("Familia", "Escuela", "Colegiatura escolar", "Guardería y cuidado infantil", "Vivienda", "Renta",
              "Administración del edificio", "Mantenimiento", "Servicios domésticos", "Mascotas", "Compras para el hogar",
              "Mudanza", "Seguridad del hogar", "Documentos familiares", "Actividades familiares"),
    "dinero": ("Banco", "Cuenta corriente o débito", "Tarjeta de crédito", "Tarjeta de débito", "Transferencias",
               "Depósitos e ingresos", "Nómina", "Pagos y comprobantes", "Factura pendiente", "Factura pagada",
               "Electricidad", "Agua", "Gas", "Internet y telefonía", "Renta", "Colegiatura", "Impuestos", "Gobierno",
               "Préstamos y créditos", "Hipoteca", "Inversiones", "Ahorro y pensión", "Reembolsos",
               "Comisiones e intereses", "Conciliación", "Deudas y cobranza", "Recibos fiscales", "Multas y sanciones",
               "Donaciones", "Gastos compartidos",
               "Seguros"),  # ASTRA: "Prima pendiente o pagada: Dinero y facturas (Seguros)"
    "compras": ("Pedido confirmado", "Envío", "Entrega", "Recogida en tienda", "Devolución", "Reembolso de compra",
                "Garantía", "Suscripción digital", "Membresía", "Periodo de prueba", "Renovación automática",
                "Cancelación de suscripción", "Disponibilidad de producto", "Recibo de compra", "Reserva de producto",
                "Compra recurrente", "Garantía extendida", "Disputa con comercio"),
    "salud": ("Médico", "Hospital", "Laboratorio", "Farmacia", "Tratamiento", "Salud preventiva", "Salud dental",
              "Salud mental", "Seguro médico", "Seguro de vida", "Seguro de auto", "Seguro de hogar", "Seguro de viaje",
              "Prima de seguro", "Siniestro", "Reclamación de seguro", "Reembolso médico", "Cobertura y exclusiones",
              "Citas médicas", "Documentación clínica"),
    "viajes": ("Vuelos", "Hoteles", "Transporte terrestre", "Alquiler de vehículo", "Itinerarios", "Cambios de viaje",
               "Cancelaciones de viaje", "Viajes pendientes", "Visados y documentos de viaje", "Equipaje", "Entradas",
               "Conciertos y espectáculos", "Eventos profesionales", "Eventos familiares", "Restaurantes",
               "Citas personales", "Actividades y excursiones", "Eventos deportivos", "Eventos educativos",
               "Eventos pendientes"),
    "promociones": ("Redes sociales", "Comentarios y menciones", "Mensajes de comunidad", "Actividad de contactos",
                    "Boletines informativos", "Boletines temáticos", "Promociones", "Cupones", "Ofertas y rebajas",
                    "Marketing comercial", "Invitaciones promocionales", "Encuestas comerciales",
                    "Programas de fidelidad", "Comunicaciones de creadores", "Comunidades de interés",
                    "Alertas de reputación social", "Concursos y sorteos", "Ofertas de seguros", "Spam"),
}
SECURITY_TAGS = ("Inicio de sesión desconocido", "Cuenta posiblemente comprometida", "Cambio de contraseña",
                 "Recuperación de cuenta", "Código de verificación", "Suplantación de identidad", "Phishing sospechoso",
                 "Fraude financiero", "Cargo no reconocido", "Cambio sospechoso de datos bancarios", "Actividad bloqueada",
                 "Riesgo de privacidad", "Malware o archivo sospechoso", "Permisos de aplicación",
                 "Seguridad de dispositivos")


def _rx(*parts: str) -> re.Pattern[str]:
    return re.compile("(" + "|".join(parts) + ")")


# Señales de tema (texto plegado: minúsculas, sin acentos). (área, peso, patrón)
TOPIC_SIGNALS: list[tuple[str, int, re.Pattern[str]]] = [
    # Ocupación
    ("trabajo", 3, _rx(r"recibo de nomina", r"\bpayslip", r"\bpay stub", r"comprobante de nomina")),
    ("trabajo", 3, _rx(r"contrato (de prestacion|de servicios|laboral|con )", r"para (tu )?(revision y )?firma", r"\bnda\b",
                       r"acuerdo de confidencialidad")),
    ("trabajo", 3, _rx(r"entrevista", r"\bvacante", r"\bpuesto de", r"\bjob (offer|interview)", r"reclutamiento", r"seleccion de personal")),
    ("trabajo", 3, _rx(r"\bproyecto\b", r"\bsprint\b", r"\bpmo\b", r"\bdemo\b", r"\bstand-?up\b", r"reunion de (seguimiento|equipo|trabajo|proyecto)",
                       r"\bkick-?off\b", r"entregables?", r"\bcliente(s)? (nos|pide|solicita)")),
    ("trabajo", 3, _rx(r"servicios de (consultoria|asesoria|desarrollo|hosting|nube)", r"\bproveedor(a)?\b", r"cuentas por pagar",
                       r"orden de compra", r"\bcloud\s?host", r"\bhosting\b", r"\bservidores?\b", r"\bsaas\b", r"(?<!your )\binvoice\b.{0,60}\b(usd|eur)\b.{0,40}(services|servicios|consult|hosting|cloud)")),
    ("trabajo", 2, _rx(r"\b(estimados|les compartimos)\b", r"\bequipo\b", r"\bteam\b")),
    # Hogar y familia
    ("hogar", 3, _rx(r"\bcolegio\b", r"\bescuela\b", r"padres de familia", r"\bmaestr[ao]\b", r"boleta de calificaciones", r"\bguarderia",
                     r"\bgrupo \d[a-z]\b", r"\baviso escolar\b", r"\bcircular escolar\b")),
    ("hogar", 3, _rx(r"\bedificio\b", r"\bcondominio\b", r"administracion del (edificio|condominio)", r"\bcisterna\b", r"cuota de mantenimiento",
                     r"\bcasero\b", r"\barrendador")),
    ("hogar", 3, _rx(r"\bmascota", r"\bveterinari", r"\bantirrabica", r"\bdesparasit", r"\bvet\b")),
    ("hogar", 3, _rx(r"\bplomer", r"\bfuga\b", r"visita tecnica", r"\belectricista", r"\bmudanza", r"\bjardiner")),
    ("hogar", 2, _rx(r"\babuela?\b", r"\bfamilia\b", r"\btios?\b", r"\bprimos?\b", r"comida (del|en casa)")),
    # Dinero y facturas
    ("dinero", 3, _rx(r"energia electrica", r"\bluz\b", r"agua potable", r"\bgas natural", r"\binternet\b", r"\btelefonia\b",
                      r"recibo .{0,30}(periodo|total a pagar)")),
    ("dinero", 3, _rx(r"\bdeposito\b", r"\btransferencia\b", r"\bspei\b", r"clave de rastreo", r"estado de cuenta", r"pago minimo",
                      r"tarjeta de credito", r"\bsaldo\b", r"\bprestamo", r"\bhipoteca", r"\bafore\b")),
    ("dinero", 3, _rx(r"movimiento bancario", r"aviso fiscal", r"\bfiscal(es)?\b", r"\bsat\b", r"declaracion (anual|mensual)", r"\bimpuesto", r"\bacuse\b", r"\bcfdi\b", r"\brfc\b", r"\bmulta\b", r"\btenencia\b")),
    ("dinero", 1, _rx(r"\bbanco\b", r"\bfactura\b", r"\bpago\b", r"\bcargo\b")),
    # L7reg1 (4): facturas y movimientos en en/fr/pt (la factura personal es Dinero; la de proveedor se mueve a Trabajo abajo).
    ("dinero", 3, _rx(r"\b(your|tu|sua|votre) (invoice|bill|fatura|facture|factura)\b", r"\bfatura\b", r"\bfacture\b",
                      r"\bpagamento\b", r"\bmontant\b", r"movimiento por", r"\bis due\b", r"\bvence em\b", r"\bstatement\b")),
    # Compras y suscripciones
    ("compras", 3, _rx(r"\bpedido\b", r"\border\b", r"\bpaquete\b", r"\benvio\b", r"\bshipped\b", r"\bguia \d", r"\bentregamos\b",
                       r"\bdevolucion\b", r"\breembolso\b", r"\brefund\b", r"\bgarantia\b")),
    ("compras", 3, _rx(r"\bmembresia\b", r"\bsuscripcion\b", r"\bsubscription\b", r"se renovara", r"\bplan (premium|basico|pro)\b",
                       r"periodo de prueba", r"\bfree trial\b", r"elige un plan")),
    # Salud y seguros
    ("salud", 3, _rx(r"cita (medica|con (el|la) (dr|dra))", r"\bdra?\.\s", r"\bclinica\b", r"\bhospital", r"\bconsultorio",
                     r"\bpaciente", r"\blaboratorio\b", r"resultados (disponibles|de (laboratorio|tu estudio|tus estudios))", r"\bestudio de\b", r"\bdentista|\bdental\b")),
    ("salud", 3, _rx(r"\bpoliza\b", r"\baseguradora", r"\bsiniestro", r"\bajustador", r"gastos medicos", r"\bcobertura\b", r"\bdeducible")),
    ("salud", 3, _rx(r"\bfarmacia", r"\breceta\b", r"\bmedicamento", r"\btratamiento\b", r"\bvacuna\b(?!.{0,40}(toby|mascota|perro|gato|antirrabica))")),
    # Viajes y eventos
    ("viajes", 3, _rx(r"\bvuelo\b", r"\bflight\b", r"\baerolinea", r"\bitinerario", r"\bhotel\b", r"\bcheck-?in\b", r"\bboarding\b",
                      r"\bgate opens\b", r"\bequipaje\b", r"\bpasaporte", r"\bvisa\b", r"renta de auto", r"\bautobus")),
    ("viajes", 3, _rx(r"\breservation\b", r"\breserva(cion)? (esta |fue )?confirmad", r"\bvoyage\b", r"\bviagem\b", r"\bvoo\b")),
    ("viajes", 3, _rx(r"\bboletos?\b", r"\bentradas?\b.{0,30}(concierto|evento|funcion)", r"\bconcierto", r"\bteatro\b",
                      r"\bfestival\b", r"\bpartido\b", r"\bmesa para \d", r"\brestaurante", r"\btickets?\b")),
    # Promociones y social
    ("promociones", 3, _rx(r"\bdescuento", r"\bcupon\b", r"\boferta", r"\brebajas?\b", r"\bpromocion", r"darte de baja", r"dejar de recibir",
                           r"\bunsubscribe\b", r"\b\d{1,2}% (de descuento|off)")),
    ("promociones", 3, _rx(r"comento tu", r"\bpublicacion\b", r"\bseguidor", r"te etiqueto", r"\bmenciono\b", r"red social",
                           r"\blikes?\b", r"le gusta tu")),
    ("promociones", 3, _rx(r"\bboletin\b", r"\bnewsletter\b", r"\bpuntos\b.{0,40}(vencer|canjea|lealtad|programa)", r"\blealtad\b",
                           r"\bsorteo\b", r"\bconcurso\b", r"\bganaste\b", r"\bfelicidades\b", r"producto milagro", r"compra ya")),
]

# Regla del analizador → área sugerida (prior). La regla nunca decide sola cuando hay tema explícito de otra área.
RULE_PRIOR = {
    "invoice_due": "dinero", "charge_due": "dinero", "bill_followup": "dinero", "bill_settled": "dinero", "invoice_info": "dinero",
    "payment_confirmation": "dinero", "partial_payment": "dinero",
    "booking": "viajes", "booking_pending": "viajes", "booking_cancel": "viajes",
    "renewal_upcoming": "compras", "renewal_done": "compras", "renewal_action": "compras",
    "order_notice": "compras", "stock_alert": "compras", "promotional": "promociones", "social": "promociones",
}
# Desempate determinista (orden de sombreros).
_ORDER = ["trabajo", "hogar", "dinero", "compras", "salud", "viajes", "promociones"]

_SECURITY_RULES = {"security", "security_action", "security_unverified", "verification"}
_BANK_RE = _rx(r"\bbanco\b", r"\btarjeta\b", r"\bcargo\b", r"\bnip\b", r"\bbanca\b", r"\bcuenta (bancaria|terminacion)",
               r"\bbank\b", r"\bcard\b", r"bancolince|codigos@|alertas@")

# Etiquetas por área: (etiqueta, patrón). Solo se emiten las que están en CATALOG[área].
TAG_RULES: dict[str, list[tuple[str, re.Pattern[str]]]] = {
    "trabajo": [
        ("Nómina laboral", _rx(r"recibo de nomina", r"payslip", r"comprobante de nomina")),
        ("Recursos humanos", _rx(r"recibo de nomina", r"\brrhh\b", r"recursos humanos", r"\bhr\b")),
        ("Contratos", _rx(r"\bcontrato")), ("Legal y cumplimiento", _rx(r"\blegal\b", r"\bfirma\b", r"cumplimiento")),
        ("Empleo y contratación", _rx(r"entrevista", r"vacante", r"puesto de", r"seleccion")),
        ("Proyectos", _rx(r"\bproyecto", r"\bsprint\b", r"\bdemo\b")),
        ("Reuniones y tareas", _rx(r"reunion", r"\breview\b", r"\bjunta\b", r"asistencia", r"\bmeeting\b")),
        ("Proveedores", _rx(r"proveedor", r"consultoria", r"\binvoice\b", r"\bfactura\b", r"hosting", r"\bcloud")),
        ("Facturación empresarial", _rx(r"\bfactura\b", r"\binvoice\b")),
    ],
    "hogar": [
        # L7reg1 (5): "escuela" suelta en un pie genérico ("consulta con la familia o escuela") no es Escuela.
        ("Escuela", _rx(r"colegio", r"(?<!familia o )(?<!familia y )\bescuela\b(?! por el canal)", r"padres de familia", r"maestr",
                        r"\bescolar(es)?\b", r"boleta", r"colegiatura", r"guarderia", r"\bgrupo \d[a-z]\b")),
        ("Actividades familiares", _rx(r"junta de padres", r"festival escolar", r"actividad familiar")),
        ("Administración del edificio", _rx(r"edificio", r"condominio", r"administracion")),
        ("Mantenimiento", _rx(r"mantenimiento", r"fuga", r"reparacion")),
        ("Servicios domésticos", _rx(r"plomer", r"visita tecnica", r"electricista", r"limpieza")),
        ("Mascotas", _rx(r"mascota", r"veterinari", r"antirrabica", r"\bvet")),
        ("Familia", _rx(r"(?<!padres de )familia", r"abuela", r"\bfotos\b")),  # "padres de familia" es Escuela
    ],
    "dinero": [
        ("Electricidad", _rx(r"energia electrica", r"\bluz\b")), ("Agua", _rx(r"agua potable", r"\bagua\b")),
        ("Gas", _rx(r"\bgas\b")), ("Internet y telefonía", _rx(r"internet", r"telefonia", r"fibra")),
        ("Factura pendiente", _rx(r"total a pagar", r"\b(recibo|factura)\b[^\n]{0,120}fecha limite de pago")),  # "vence en 10 min" (código) no es factura
        ("Factura pagada", _rx(r"recibimos tu pago", r"pago recibido")),
        ("Pagos y comprobantes", _rx(r"recibimos tu pago", r"pago recibido", r"se realizo con exito", r"comprobante")),
        ("Depósitos e ingresos", _rx(r"deposito")), ("Nómina", _rx(r"deposito de nomina", r"nomina")),
        ("Transferencias", _rx(r"transferencia", r"spei")),
        ("Tarjeta de crédito", _rx(r"tarjeta de credito", r"pago minimo", r"estado de cuenta", r"en tu tarjeta", r"\btarjeta\b")),
        ("Banco", _rx(r"\bbanco\b", r"tu codigo es", r"codigo de verificacion")),
        ("Impuestos", _rx(r"\bsat\b", r"declaracion", r"impuesto")), ("Gobierno", _rx(r"\bsat\b", r"gobierno", r"acuse")),
        ("Seguros", _rx(r"\bprima\b", r"poliza")),
    ],
    "compras": [
        ("Pedido confirmado", _rx(r"pedido .{0,20}confirmado", r"fue confirmado")), ("Recibo de compra", _rx(r"gracias por tu compra")),
        ("Envío", _rx(r"va en camino", r"shipped", r"\benvio\b", r"centro de distribucion", r"\bguia\b")),
        ("Entrega", _rx(r"entregado", r"entregamos", r"delivered")),
        ("Devolución", _rx(r"devolucion")), ("Reembolso de compra", _rx(r"reembolso", r"refund")),
        ("Suscripción digital", _rx(r"membresia", r"suscripcion", r"plan premium", r"tu cuenta", r"contrasena")),
        ("Renovación automática", _rx(r"se renovara", r"renovacion automatica", r"automaticamente")),
        ("Periodo de prueba", _rx(r"periodo de prueba", r"free trial")),
    ],
    "salud": [
        ("Citas médicas", _rx(r"cita (medica|con)")), ("Médico", _rx(r"cita (medica|con)", r"\bdra?\.\s", r"consulta medica")),  # "gastos médicos" (póliza) no es Médico
        ("Laboratorio", _rx(r"laboratorio")), ("Documentación clínica", _rx(r"resultados", r"expediente")),
        ("Farmacia", _rx(r"farmacia", r"receta", r"medicamento")), ("Tratamiento", _rx(r"receta", r"medicamento", r"tratamiento")),
        ("Seguro médico", _rx(r"gastos medicos", r"seguro medico")), ("Cobertura y exclusiones", _rx(r"cobertura", r"exclusiones")),
        ("Seguro de auto", _rx(r"siniestro de auto", r"seguro de auto", r"\bauto\b")), ("Siniestro", _rx(r"siniestro")),
        # L7reg1 (5): póliza o aseguradora sin tipo explícito → Prima de seguro (familia Seguro).
        ("Prima de seguro", _rx(r"\bpoliza (vigente|vencida|no\.?|numero|#|\d)", r"\btu poliza\b", r"renovacion de (tu )?poliza",
                                r"\bprima (de seguro|anual|mensual|pendiente)", r"\baseguradora\b")),
    ],
    "viajes": [
        ("Vuelos", _rx(r"\bvuelo\b", r"\bflight\b")), ("Itinerarios", _rx(r"codigo de reserva", r"\bsale el\b")),
        ("Cambios de viaje", _rx(r"cambio de horario", r"cambio .{0,15}(vuelo|itinerario)", r"cambio\b.{0,20}horario")),
        ("Hoteles", _rx(r"hotel", r"check-?in")), ("Entradas", _rx(r"boletos", r"entradas", r"tickets?")),
        ("Conciertos y espectáculos", _rx(r"concierto", r"teatro", r"espectaculo")), ("Restaurantes", _rx(r"restaurante", r"mesa para")),
    ],
    "promociones": [
        ("Promociones", _rx(r"descuento", r"promocion")), ("Cupones", _rx(r"cupon")),
        ("Redes sociales", _rx(r"comento tu", r"publicacion", r"red social")), ("Comentarios y menciones", _rx(r"comento", r"comentario", r"mencion")),
        ("Boletines informativos", _rx(r"boletin", r"newsletter", r"noticias")), ("Programas de fidelidad", _rx(r"puntos", r"lealtad")),
        ("Concursos y sorteos", _rx(r"sorteo", r"concurso", r"ganaste", r"premio")),
        ("Marketing comercial", _rx(r"producto milagro", r"compra ya", r"envio gratis")),
        ("Spam", _rx(r"no solicitad", r"unsolicited", r"\bmilagros[ao]\b", r"producto milagro", r"promesas exageradas",
                     r"gana dinero (facil|rapido)", r"bajar de peso sin")),
    ],
}
SECURITY_TAG_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("Inicio de sesión desconocido", _rx(r"inicio de sesion", r"se inicio sesion", r"sign-?in", r"dispositivo nuevo")),
    ("Cambio de contraseña", _rx(r"contrasena .{0,20}(cambio|modificada)", r"contrasena modificada", r"password changed")),
    ("Código de verificación", _rx(r"tu codigo es", r"codigo de verificacion", r"verification code")),
    ("Cargo no reconocido", _rx(r"cargo no reconocido", r"no lo reconoces", r"no coincide con tus patrones")),
    ("Cuenta posiblemente comprometida", _rx(r"comprometida", r"compromised")),
    ("Actividad bloqueada", _rx(r"bloquead", r"suspendida")),
]


def topic_scores(text: str) -> dict[str, int]:
    scores: dict[str, int] = {}
    for area, weight, pattern in TOPIC_SIGNALS:
        if pattern.search(text):
            scores[area] = scores.get(area, 0) + weight
    return scores


def _pick(scores: dict[str, int], prior: str | None) -> str | None:
    if prior:
        scores = {**scores, prior: scores.get(prior, 0) + 2}
    if not scores:
        return None
    best = max(scores.values())
    if best < 2:
        return None
    return next(a for a in _ORDER if scores.get(a) == best)


def _tags(area: str | None, text: str) -> list[str]:
    if not area:
        return []
    allowed = set(CATALOG[area])
    out = [tag for tag, pattern in TAG_RULES.get(area, []) if pattern.search(text) and tag in allowed]
    return list(dict.fromkeys(out))[:4]


def security_tags(text: str, *, phishing_tags: list[str] | None = None) -> list[str]:
    out = list(phishing_tags or []) + [tag for tag, pattern in SECURITY_TAG_RULES if pattern.search(text)]
    return [t for t in dict.fromkeys(out) if t in SECURITY_TAGS][:3]


_WORK_INVOICE_RE = _rx(r"servicios de (consultoria|asesoria|desarrollo|hosting|nube)", r"\bproveedor", r"cuentas por pagar",
                       r"\bcloud", r"\bhosting\b", r"\bsaas\b", r"\bestimados\b", r"\bles compartimos\b")
_PERSONAL_ROLE_RE = _rx(r"deposito de nomina", r"recibiste un deposito")


# L7reg1 (1): el remitente solo da una pista débil (peso 1, nunca decide sola). Antes el remitente entraba en el
# texto de temas y una palabra del dominio (p. ej. "demo" → Trabajo) decidía el área de cualquier correo.
SENDER_HINTS: list[tuple[str, re.Pattern[str]]] = [
    ("salud", _rx(r"clinica", r"hospital", r"laboratorio", r"aseguradora", r"polizas?", r"farmacia", r"medic")),
    ("hogar", _rx(r"escuela", r"colegio", r"condominio", r"edificio", r"veterinari")),
    ("dinero", _rx(r"\bbanco", r"\bbank", r"facturacion", r"\bbilling", r"\bsat\b")),
    ("viajes", _rx(r"aerolinea", r"airline", r"\bhotel", r"reservas?\b", r"booking")),
    ("compras", _rx(r"tienda", r"\bstore\b", r"pedidos", r"\bshop\b")),
]
_WEAK_TOPIC_RULES = {"legacy_info", "legacy_notice", "legacy_action", "request", "bulk"}
_NO_AREA_RULES = {"ambiguous"}
# Triage "review" que NO es duda de área: factura identificada sin fecha límite (seguimiento) conserva su área.
_REVIEW_KEEPS_AREA = {"bill_followup"}


_CHARGE_RULES = {"invoice_due", "charge_due", "bill_followup", "invoice_info", "bill_settled"}
# El cobro corresponde a una compra: "factura de tu pedido", "cargo por la renovación", "tu suscripción por $".
_PURCHASE_CHARGE_RE = _rx(
    r"(factura|cargo|cobro|recibo|pago|invoice|charge)[^.\n]{0,40}\b(pedido|compra|orden|suscripcion|membresia|renovacion|plan)\b",
    r"\b(pedido|compra|orden|suscripcion|membresia|renovacion|order|subscription)\b[^.\n]{0,40}(factura|cargo|cobro|total|\$|mxn|usd)")


def _reliable_topic(text: str) -> str | None:
    strong: dict[str, int] = {}
    for area, weight, pattern in TOPIC_SIGNALS:
        if weight >= 3 and pattern.search(text):
            strong[area] = strong.get(area, 0) + 1
    hits = [a for a, n in strong.items() if n >= 2]
    return hits[0] if len(hits) == 1 and all(n < 2 for a, n in strong.items() if a != hits[0]) else None


def _sender_tokens(sender_l: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", sender_l.replace(".invalid", " ").replace(".example", " "))


def _review(reason: str, flag: str | None = None, sec_tags: list[str] | None = None) -> dict[str, Any]:
    return {"area": None, "area_label": None, "hat": None, "tags": [], "security_flag": flag,
            "security_tags": sec_tags or [], "review_reason": reason}


def classify_v2(rule: str, text: str, sender: str, confidence: float, *, phishing: bool = False,
                severity: str | None = None, phishing_tags: list[str] | None = None,
                triage: str | None = None, input_limit: str | None = None) -> dict[str, Any]:
    """Devuelve {area, area_label, hat, tags, security_flag, security_tags, review_reason}.

    ``text`` debe venir plegado (fold). Phishing → area None (Por revisar) + security_flag N1.
    """
    sender_l = (sender or "").lower()
    probe = f"{sender_l}\n{text}"
    if phishing:
        # L7reg2 (a, ASTRA): fraude N1 → Por revisar + alerta (nunca se oculta). Solo conserva un área temática con
        # evidencia explícita y fiable: dos señales fuertes distintas del MISMO tema en el texto, y tema único.
        reliable = _reliable_topic(text)
        return {"area": reliable, "area_label": AREAS.get(reliable) if reliable else None,
                "hat": HATS.get(reliable) if reliable else None, "tags": _tags(reliable, text) if reliable else [],
                "security_flag": "N1",
                "security_tags": security_tags(text, phishing_tags=phishing_tags or ["Phishing sospechoso"]),
                "review_reason": "Posible phishing o fraude: no interactúes; revisa."}
    if input_limit:
        return _review(input_limit)
    scores = topic_scores(text)
    best = max(scores.values(), default=0)
    tied = [a for a, v in scores.items() if v == best]
    if best >= 3 and len(tied) > 1:
        # Empate de temas en el cuerpo: decide el ASUNTO si su tema es único entre los empatados.
        subj = topic_scores(text.split("\n", 1)[0])
        lead = [a for a in tied if subj.get(a, 0) >= 3]
        if len(lead) == 1:
            scores = {**scores, lead[0]: best + 1}
            best, tied = best + 1, lead
    explicit = best >= 3 and len(tied) == 1
    if rule in _NO_AREA_RULES or (triage == "review" and rule not in _REVIEW_KEEPS_AREA):
        # Revisión o ambigüedad: solo un tema EXPLÍCITO y único en el propio texto da área (sin remitente ni regla).
        # Si no, Por revisar; nunca un área por defecto.
        if not explicit:
            return _review("Correo ambiguo o en revisión: no se asigna un área por defecto.")
        area = next(a for a in _ORDER if scores.get(a) == best)
        # L7reg2 (b): conserva el área Y la marca de revisión.
        return {"area": area, "area_label": AREAS[area], "hat": HATS[area], "tags": _tags(area, text),
                "security_flag": None, "security_tags": [],
                "review_reason": "En revisión: el tema es explícito, pero el correo necesita tu confirmación."}
    if rule in _WEAK_TOPIC_RULES and not explicit:
        # Regla genérica sin tema explícito fuerte en el texto → Por revisar (nunca un área por defecto).
        return _review("Sin tema reconocible.")
    sender_tokens = _sender_tokens(sender_l)
    for area_key, pattern in SENDER_HINTS:
        if pattern.search(sender_tokens) and area_key not in scores:  # pista, nunca refuerza un tema ya visto
            scores[area_key] = 1
    prior = RULE_PRIOR.get(rule)
    # Factura/cobro de negocio (proveedor, nube, consultoría) → Trabajo; depósito de nómina sigue en Dinero.
    if prior == "dinero" and _WORK_INVOICE_RE.search(text) and not _PERSONAL_ROLE_RE.search(text):
        prior = "trabajo"
    if rule in _CHARGE_RULES and prior in {"dinero", "trabajo"}:
        # L7reg2 (c, ASTRA): un cobro se decide por CONTEXTO del propio cobro, nunca en bloque ni por el asunto suelto:
        # operación de negocio comprobada → Trabajo; el cobro es de un pedido/compra/renovación → Compras;
        # obligación, cargo o factura personal → Dinero.
        work = prior == "trabajo" or scores.get("trabajo", 0) >= 3  # nómina, contrato, proyecto: operación laboral
        area = "trabajo" if work else ("compras" if _PURCHASE_CHARGE_RE.search(text) else "dinero")
        return {"area": area, "area_label": AREAS[area], "hat": HATS[area], "tags": _tags(area, text),
                "security_flag": None, "security_tags": [], "review_reason": None}
    flag = None
    if rule in _SECURITY_RULES:
        strong = rule in {"security_action", "security_unverified"} or severity in {"critical", "risk", "compromise", "check"}
        flag = "N1" if strong else "N2"
        if _BANK_RE.search(probe):
            prior = "dinero"
        elif scores:
            prior = None
        else:
            prior = "compras"  # cuenta de un servicio digital (Suscripción digital)
    area = _pick(scores, prior)
    tags = _tags(area, text)
    if area == "compras" and flag and not tags:
        tags = ["Suscripción digital"]
    if area == "dinero" and flag and not tags:
        tags = ["Banco"]
    reason = None
    if area is None:
        reason = "Baja confianza: el correo no indica un tema claro." if confidence < 0.5 else "Sin tema reconocible."
    return {"area": area, "area_label": AREAS.get(area) if area else None, "hat": HATS.get(area) if area else None,
            "tags": tags, "security_flag": flag, "security_tags": security_tags(text) if flag else [],
            "review_reason": reason}
