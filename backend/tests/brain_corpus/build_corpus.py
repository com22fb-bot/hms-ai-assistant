"""Genera corpus.jsonl: correos sintéticos etiquetados (dominios .example).

Etiquetas por correo:
  triage     accion | aviso | revision | info | social | promo
  crea_caso  el correo debe quedar dentro de un caso
  case_key   identificador del caso esperado (mismo valor = mismo caso)
  status     estado final esperado del caso (pendiente, programado, resuelto, sin acción, requiere revisión)
  due_at     AAAA-MM-DD esperado del vencimiento del caso, o null
  event_at   AAAA-MM-DDTHH:MM (o AAAA-MM-DD) esperado del evento, o null
  priority   N1 | N2 | N3 del caso, o null
  protected  security | code | bank | government | invoice | health | null
  partd      id del caso de la Parte D (opcional)
Cada correo trae además 'solo_cabeceras' (from, subject, list-id, list-unsubscribe).
Fechas de recepción en UTC; 16:00Z = 10:00 America/Mexico_City.
Ejecutar: python tests/brain_corpus/build_corpus.py
"""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).with_name("corpus.jsonl")
rows: list[dict] = []


def add(mid, sender, subject, body, received, *, triage, key=None, status=None, due=None, event=None,
        priority=None, protected=None, labels=None, list_unsub=None, partd=None, thread=None):
    rows.append({
        "id": mid, "thread_id": thread or f"t-{mid}", "sender": sender, "subject": subject, "body_text": body,
        "received_at": received, "labels": ["INBOX"] + (labels or []),
        "headers": {"list-unsubscribe": list_unsub} if list_unsub else {},
        "solo_cabeceras": {"from": sender, "subject": subject, "list-unsubscribe": list_unsub},
        "label": {"triage": triage, "crea_caso": key is not None, "case_key": key, "status": status, "due_at": due,
                  "event_at": event, "priority": priority, "protected": protected, "partd": partd},
    })


# ---------------- Parte D (mismos 27 correos de /workspace/cerebro/partd.py) ----------------
A = "facturacion@acme-servicios.example"
add("f1", A, "Factura F-1001 de Servicios Acme", "Adjuntamos la factura F-1001 por $1,250.00 MXN. Fecha de vencimiento: 2026-10-30. Favor de realizar el pago.", "2026-10-01T15:00:00Z", triage="accion", key="F1001", status="resuelto", due="2026-10-30", priority="N2", protected="invoice", partd="D1")
add("f2", A, "Recordatorio: Factura F-1001 de Servicios Acme", "Recordatorio: su factura F-1001 por $1,250.00 vence el 2026-10-30. Por favor pague.", "2026-10-08T15:00:00Z", triage="accion", key="F1001", status="resuelto", due="2026-10-30", priority="N2", protected="invoice", partd="D2")
add("f3", A, "Confirmación de pago - Factura F-1001", "Recibimos su pago de $1,250.00 de la factura F-1001. Gracias.", "2026-10-10T15:00:00Z", triage="aviso", key="F1001", status="resuelto", due="2026-10-30", priority="N2", protected="invoice", partd="D3")
T = "pedidos@tienda-x.example"
add("c1", T, "Tu pedido ha sido confirmado", "Pedido #A-555 por $499.00. Pago pendiente: favor de pagar en OXXO.", "2026-10-02T15:00:00Z", triage="accion", key="A555", status="pendiente", priority="N2", protected="invoice", partd="D4")
add("c2", T, "Tu pedido ha sido confirmado", "Pedido #B-777 por $499.00. Pago pendiente: favor de pagar en OXXO.", "2026-10-03T15:00:00Z", triage="accion", key="B777", status="pendiente", priority="N2", protected="invoice", partd="D4")
add("p1", "promociones@tienda-x.example", "¡50% de descuento solo hoy!", "Ofertas exclusivas. Cancelar suscripción.", "2026-10-04T15:00:00Z", triage="promo", labels=["CATEGORY_PROMOTIONS"], list_unsub="<mailto:baja@tienda-x.example>", partd="D5")
add("s1", "notification@facebookmail.com", "Ana comentó tu foto", "Ana comentó tu foto. Ver en Facebook.", "2026-10-04T16:00:00Z", triage="social", labels=["CATEGORY_SOCIAL"], partd="D6")
add("s2", "security@mail.instagram.com", "Nuevo inicio de sesión en tu cuenta de Instagram", "Detectamos un nuevo inicio de sesión desde Chrome en Windows. Si no fuiste tú, protege tu cuenta. Tu código de seguridad es 482913.", "2026-10-05T16:00:00Z", triage="aviso", protected="code", partd="D7")
for i in range(15):
    add(f"v{i}", "support@donexto.com", "Verifica tu cuenta de Donexto", "Confirma tu correo haciendo clic en el enlace para verificar tu cuenta.", f"2026-10-06T{10 + i % 10:02d}:{i:02d}:00Z", triage="info", partd="D8")
add("m1", "citas@clinica-salud.example", "Cita confirmada: Dra. López", "Su cita médica quedó confirmada para el 2026-10-20 a las 10:00. Por favor llegue 15 minutos antes.", "2026-10-07T15:00:00Z", triage="accion", key="M1", status="programado", event="2026-10-20T10:00", priority="N2", protected="health", partd="D9")
add("x1", "cobranza@servicio-y.example", "Aviso de adeudo", "Tiene un saldo pendiente. Paga cuanto antes para evitar suspensión.", "2026-10-07T16:00:00Z", triage="accion", key="X1", status="pendiente", priority="N1", protected="invoice", partd="D10")
add("a1", "amigo.persona@correo.example", "lo de ayer", "Oye, sobre lo de ayer, ¿cómo ves?", "2026-10-08T16:00:00Z", triage="revision", partd="D11")
add("d1", "rh@empresa-z.example", "Documentos para expediente laboral", "Hola, por favor envía tu INE, comprobante de domicilio y CURP a más tardar el próximo viernes.", "2026-10-12T16:00:00Z", triage="accion", key="D1", status="pendiente", due="2026-10-16", priority="N2", protected=None, partd="D12")

# ---------------- Facturas MX: CFE, Telmex, agua, gas, tarjetas, colegiaturas ----------------
# (id, remitente, asunto factura, folio, importe, frase de vencimiento, recibido, due esperado, escenario)
bills = [
    ("cfe", "avisos@cfe-recibos.example", "Tu recibo CFE de luz", "CFE-88120", "845.00", "Fecha límite de pago: 5 de noviembre.", "2026-10-20T16:00:00Z", "2026-11-05", "full"),
    ("tmx", "facturacion@telmex-pagos.example", "Factura Telmex octubre", "TMX-4431", "589.00", "Tu factura vence el 28/10/2026.", "2026-10-14T16:00:00Z", "2026-10-28", "partial"),
    ("agua", "cobranza@agua-municipal.example", "Recibo de agua bimestral", "AG-20991", "312.50", "Paga antes del 31 de octubre de 2026.", "2026-10-09T16:00:00Z", "2026-10-31", "other_folio"),
    ("gas", "clientes@gas-natural.example", "Factura de gas natural", "GN-7781", "460.00", "Fecha de vencimiento: 2026-11-02.", "2026-10-15T16:00:00Z", "2026-11-02", "last_notice"),
    ("tdc", "estados@banco-azul.example", "Estado de cuenta de tu tarjeta", "EC-5521", "3,420.00", "Fecha límite de pago: 25 de octubre de 2026. Paga al menos el mínimo.", "2026-10-05T16:00:00Z", "2026-10-25", "wrong_amount"),
    ("col", "administracion@colegio-sol.example", "Colegiatura noviembre", "COL-1102", "4,800.00", "La mensualidad vence a fin de mes, favor de pagar.", "2026-10-12T16:00:00Z", "2026-10-31", "full"),
    ("int", "facturas@redfibra.example", "Factura internet hogar", "RF-90012", "699.00", "Tu factura vence en 3 días.", "2026-10-13T16:00:00Z", "2026-10-16", "partial"),
    ("seg", "cobros@seguros-vida.example", "Aviso de pago de póliza", "POL-33310", "1,980.00", "Realice su pago a más tardar el 6 de noviembre.", "2026-10-16T16:00:00Z", "2026-11-06", "other_folio"),
    ("ren", "admin@inmobiliaria-norte.example", "Recibo de renta noviembre", "RN-1124", "9,500.00", "La renta vence mañana, favor de realizar el pago.", "2026-10-30T16:00:00Z", "2026-10-31", "last_notice"),
    ("pre", "tesoreria@municipio-x.example", "Factura predial 2026", "PRD-2026-55", "2,150.00", "Fecha límite de pago: 30 de noviembre de 2026.", "2026-10-19T16:00:00Z", "2026-11-30", "full"),
    ("tdc2", "avisos@banco-verde.example", "Tu estado de cuenta está listo", "TV-6610", "12,300.00", "Fecha límite de pago: 2 de noviembre de 2026. Realiza tu pago.", "2026-10-11T16:00:00Z", "2026-11-02", "wrong_amount"),
    ("gym", "pagos@gimnasio-fit.example", "Factura de membresía", "GYM-0451", "750.00", "Favor de pagar antes del 20 de octubre.", "2026-10-10T16:00:00Z", "2026-10-20", "full"),
]


def days_prio(received: str, due: str) -> str:
    from datetime import date
    r = date.fromisoformat(received[:10]); d = date.fromisoformat(due)
    return "N1" if (d - r).days <= 3 else "N2"


def later(received: str, days: int) -> str:
    from datetime import datetime, timedelta
    return (datetime.fromisoformat(received.replace("Z", "+00:00")) + timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


for code, snd, subj, folio, amount, due_phrase, rec, due, scen in bills:
    key = f"BILL-{code}"
    final = "resuelto" if scen == "full" else "pendiente"
    prio = days_prio(rec, due)
    prot = "invoice"
    add(f"{code}-inv", snd, f"{subj} · folio {folio}", f"Estimado cliente: su factura folio {folio} por ${amount} MXN ya está disponible (CFDI adjunto). {due_phrase}", rec,
        triage="accion", key=key, status=final, due=due, priority=prio, protected=prot)
    if scen in {"full", "last_notice"}:
        prefix = "Recordatorio:" if scen == "full" else "Último aviso:"
        add(f"{code}-rem", snd, f"{prefix} {subj} · folio {folio}", f"{prefix} su factura folio {folio} por ${amount} sigue pendiente. Por favor pague para evitar la suspensión.", later(rec, 2),
            triage="accion", key=key, status=final, due=due, priority=prio, protected=prot)
    if scen == "full":
        add(f"{code}-pay", snd, f"Pago recibido · folio {folio}", f"Gracias por su pago de ${amount} MXN aplicado a la factura folio {folio}.", later(rec, 3),
            triage="aviso", key=key, status=final, due=due, priority=prio, protected=prot)
    if scen == "partial":
        half = f"{float(amount.replace(',', '')) / 2:.2f}"
        add(f"{code}-pay", snd, f"Pago parcial recibido · folio {folio}", f"Recibimos su pago parcial de ${half} a la factura folio {folio}. Saldo restante pendiente.", later(rec, 3),
            triage="aviso", key=key, status=final, due=due, priority=prio, protected=prot)
    if scen == "other_folio":
        add(f"{code}-pay", snd, "Confirmación de pago", f"Gracias por su pago de ${amount}. Folio de la factura pagada: {folio}9.", later(rec, 3),
            triage="aviso", protected=prot)
    if scen == "wrong_amount":
        add(f"{code}-pay", snd, f"Pago recibido · folio {folio}", f"Recibimos su pago de $500.00 a la factura folio {folio}. Gracias.", later(rec, 4),
            triage="aviso", key=key, status=final, due=due, priority=prio, protected=prot)

# SAT / gobierno
add("sat1", "notificaciones@buzon-sat.example", "Buzón tributario: requerimiento de información", "Se solicita que presente la documentación de su declaración a más tardar el 15 de noviembre de 2026.", "2026-10-15T16:00:00Z", triage="accion", key="SAT1", status="pendiente", due="2026-11-15", priority="N2", protected="government")
add("sat2", "avisos@buzon-sat.example", "SAT: tu constancia de situación fiscal", "Tu constancia de situación fiscal fue generada. No requiere acción.", "2026-10-16T16:00:00Z", triage="aviso", protected="government")
add("imss1", "citas@imss-digital.example", "IMSS: cita confirmada", "Su cita en la Unidad de Medicina Familiar quedó confirmada para el 4 de noviembre de 2026 a las 8:30.", "2026-10-21T16:00:00Z", triage="accion", key="IMSS1", status="programado", event="2026-11-04T08:30", priority="N2", protected="government")
# CFDI informativos (ya pagados)
for i, (shop, folio) in enumerate([("ferreteria-luz", "FL-901"), ("farmacia-sana", "FS-2231"), ("papeleria-uno", "PU-77")]):
    add(f"cfdi{i}", f"facturacion@{shop}.example", f"Tu CFDI de la compra {folio}", f"Te enviamos el CFDI de tu compra {folio} ya pagada. Consérvalo para tu contabilidad.", f"2026-10-{10 + i:02d}T16:00:00Z", triage="aviso", protected="invoice")

# ---------------- Compras repetidas del mismo comercio e importe ----------------
for i, order in enumerate(["MX-1001", "MX-1002", "MX-1003"]):
    add(f"rp{i}", "ventas@mercado-z.example", "Confirma tu pago pendiente", f"Tu pedido #{order} por $1,099.00 tiene pago pendiente. Favor de pagar en tienda.", f"2026-10-{5 + i:02d}T16:00:00Z", triage="accion", key=f"RP-{order}", status="pendiente", priority="N2", protected="invoice")
for i, order in enumerate(["ZZ-501", "ZZ-502"]):
    add(f"rpd{i}", "ventas@mercado-z.example", "Gracias por tu compra", f"Tu pedido #{order} por $350.00 fue pagado y se enviará pronto.", f"2026-10-{15 + i:02d}T16:00:00Z", triage="aviso")
add("ship1", "envios@paqueteria-r.example", "Tu pedido fue enviado", "Tu pedido #MX-1001 fue enviado. Número de guía 77881.", "2026-10-09T16:00:00Z", triage="aviso")

# ---------------- Citas y cancelaciones ----------------
appts = [
    ("ap1", "agenda@dental-sonrisa.example", "Cita confirmada con el dentista", "Su cita quedó confirmada para el 22 de octubre de 2026 a las 17:00.", "2026-10-13T16:00:00Z", "2026-10-22T17:00", None),
    ("ap2", "resultados@laboratorio-vida.example", "Confirmación de cita de laboratorio", "Su cita de laboratorio está confirmada para mañana a las 7:30. Acuda en ayunas.", "2026-10-14T16:00:00Z", "2026-10-15T07:30", None),
    ("ap3", "citas@optica-clara.example", "Cita agendada: examen de la vista", "Tu cita fue agendada para el 3 de noviembre a las 12:00.", "2026-10-15T16:00:00Z", "2026-11-03T12:00", "cancel"),
    ("ap4", "appointments@city-clinic.example", "Appointment confirmed", "Your appointment is confirmed for October 29, 2026 at 3:00 pm. Please arrive 10 minutes early.", "2026-10-16T16:00:00Z", "2026-10-29T15:00", None),
    ("ap5", "citas@fisio-centro.example", "Cita confirmada: fisioterapia", "Su cita de fisioterapia quedó confirmada para el próximo martes a las 9:00.", "2026-10-15T16:00:00Z", "2026-10-20T09:00", "reminder"),
    ("ap6", "agenda@vet-amigos.example", "Cita confirmada para tu mascota", "La cita de Firulais quedó confirmada para el 2026-10-27 a las 18:30.", "2026-10-17T16:00:00Z", "2026-10-27T18:30", "cancel"),
]
for mid, snd, subj, body, rec, ev, extra in appts:
    final = "sin acción" if extra == "cancel" else "programado"
    prio = days_prio(rec, ev[:10])
    add(mid, snd, subj, body, rec, triage="accion", key=f"AP-{mid}", status=final, event=ev, priority=prio, protected="health")
    if extra == "cancel":
        add(f"{mid}-x", snd, "Cita cancelada", f"Le informamos que su cita del {ev[:10]} fue cancelada. Puede reagendar cuando guste.", later(rec, 2), triage="aviso", key=f"AP-{mid}", status=final, event=ev, priority=prio, protected="health")
    if extra == "reminder":
        add(f"{mid}-r", snd, "Recordatorio de su cita", f"Recordatorio de su cita: lo esperamos el {ev[:10]} a las {ev[11:]}.", later(rec, 3), triage="accion", key=f"AP-{mid}", status=final, event=ev, priority=prio, protected="health")
add("ap7", "recepcion@clinica-norte.example", "Cita confirmada", "Su cita quedó confirmada. Le avisaremos la fecha.", "2026-10-18T16:00:00Z", triage="revision", protected="health")

# ---------------- Plazos relativos (personas y empresas) ----------------
rel = [
    ("r1", "jefa.area@empresa-z.example", "Reporte trimestral", "Por favor envía el reporte trimestral mañana.", "2026-10-13T16:00:00Z", "2026-10-14", "N1"),
    ("r2", "contabilidad@despacho-k.example", "Papeles para la declaración", "Necesitamos que nos envíes tus recibos de nómina en 3 días.", "2026-10-14T16:00:00Z", "2026-10-17", "N1"),
    ("r3", "proveedor@imprenta-q.example", "Aprobación de diseño", "¿Puedes confirmar el diseño final antes del 30 de octubre?", "2026-10-15T16:00:00Z", "2026-10-30", "N2"),
    ("r4", "maestra@colegio-sol.example", "Firma de boleta", "Favor de enviar la boleta firmada el próximo viernes.", "2026-10-16T16:00:00Z", "2026-10-23", "N2"),
    ("r5", "rh@empresa-z.example", "Evaluación de desempeño", "Por favor envía tu autoevaluación a fin de mes.", "2026-10-19T16:00:00Z", "2026-10-31", "N2"),
    ("r6", "socio@negocio-b.example", "Contrato de arrendamiento", "Te pido que me envíes el contrato firmado el lunes.", "2026-10-15T16:00:00Z", "2026-10-19", "N2"),
    ("r7", "manager@globex.example", "Quarterly numbers", "Could you send the quarterly numbers by next Friday?", "2026-10-13T16:00:00Z", "2026-10-16", "N1"),
    ("r8", "client@acme-corp.example", "Signed proposal", "Please send the signed proposal in 5 days.", "2026-10-14T16:00:00Z", "2026-10-19", "N2"),
    ("r9", "abogado@bufete-m.example", "Documentos del juicio", "Le pido que envíe los documentos a más tardar el 5 de noviembre de 2026.", "2026-10-20T16:00:00Z", "2026-11-05", "N2"),
    ("r10", "tesorero@asociacion-v.example", "Cuota anual", "Favor de enviar el comprobante de tu cuota antes del 25 de octubre.", "2026-10-12T16:00:00Z", "2026-10-25", "N2"),
    ("r11", "coordinador@proyecto-h.example", "Minuta", "Por favor revisa la minuta y confírmame.", "2026-10-12T16:00:00Z", None, "N2"),
    ("r12", "vecino@condominio-p.example", "Junta de condóminos", "Favor de confirmar tu asistencia.", "2026-10-12T16:00:00Z", None, "N2"),
]
for mid, snd, subj, body, rec, due, prio in rel:
    add(mid, snd, subj, body, rec, triage="accion", key=f"REL-{mid}", status="pendiente", due=due, priority=prio)
# fecha ambigua → sin fecha
add("amb1", "cobranza@servicio-y.example", "Factura FA-77 pendiente", "Favor de pagar la factura FA-77 el viernes o el lunes, como le quede mejor.", "2026-10-13T16:00:00Z", triage="accion", key="AMB1", status="pendiente", priority="N2", protected="invoice")
add("amb2", "billing@hosting-co.example", "Invoice INV-3301", "Your invoice INV-3301 for $45.00 is due on 03/04/2027. Please pay.", "2026-10-13T16:00:00Z", triage="accion", key="AMB2", status="pendiente", priority="N2", protected="invoice")

# ---------------- Correos en inglés ----------------
add("en1", "billing@cloudhost.example", "Invoice INV-4410 is ready", "Your invoice INV-4410 for $120.00 is due on October 28, 2026. Please pay to avoid interruption.", "2026-10-14T16:00:00Z", triage="accion", key="EN-4410", status="resuelto", due="2026-10-28", priority="N2", protected="invoice")
add("en2", "billing@cloudhost.example", "Payment received for INV-4410", "Thank you for your payment of $120.00 for invoice INV-4410.", "2026-10-16T16:00:00Z", triage="aviso", key="EN-4410", status="resuelto", due="2026-10-28", priority="N2", protected="invoice")
add("en3", "news@saas-weekly.example", "This week in SaaS", "Our weekly newsletter with the best articles. Unsubscribe anytime.", "2026-10-14T16:00:00Z", triage="promo", list_unsub="<https://saas-weekly.example/u>")
add("en4", "no-reply@accounts.cloudhost.example", "Your verification code", "Your verification code is 552901. It expires in 10 minutes.", "2026-10-14T17:00:00Z", triage="aviso", protected="code")
add("en5", "team@startup-io.example", "Final notice: last chance for 40% off", "Urgent! Our biggest sale ends tonight. Unsubscribe here.", "2026-10-15T16:00:00Z", triage="promo", list_unsub="<https://startup-io.example/u>")
add("en6", "billing@streamflix.example", "Your receipt", "Thanks for your purchase. Receipt #SF-8812 for $9.99. No action needed.", "2026-10-15T16:00:00Z", triage="aviso", protected="invoice")

# ---------------- Alertas de seguridad de redes sociales ----------------
sec = [
    ("sx1", "security@facebookmail.com", "Inicio de sesión desde un nuevo dispositivo", "Alguien inició sesión en tu cuenta desde un nuevo dispositivo en Monterrey. Si no fuiste tú, protege tu cuenta.", "security"),
    ("sx2", "no-reply@tiktok.com", "Código de verificación de TikTok", "Tu código de verificación es 381245.", "code"),
    ("sx3", "security-noreply@linkedin.com", "Tu contraseña se ha cambiado", "Tu contraseña de LinkedIn se ha cambiado. Si no fuiste tú, restablece tu contraseña.", "security"),
    ("sx4", "info@x.com", "New sign-in to your X account", "We noticed a new sign-in to your account from Chrome on Mac.", "security"),
    ("sx5", "no-reply@accounts.google.com", "Alerta de seguridad", "Alerta de seguridad: se detectó actividad sospechosa en tu cuenta de Google.", "security"),
    ("sx6", "security@mail.instagram.com", "Restablece tu contraseña de Instagram", "Recibimos una solicitud para restablecer tu contraseña.", "security"),
    ("sx7", "noreply@discord.com", "Tu código de acceso", "Tu código de acceso de Discord es 990011.", "code"),
    ("sx8", "notification@facebookmail.com", "Actividad inusual en tu cuenta", "Detectamos actividad inusual en tu cuenta. Revisa tus inicios de sesión.", "security"),
]
for i, (mid, snd, subj, body, kind) in enumerate(sec):
    add(mid, snd, subj, body, f"2026-10-{11 + i:02d}T18:00:00Z", triage="aviso", protected=kind, labels=["CATEGORY_SOCIAL"] if "facebook" in snd else None)
soc = [
    ("so1", "noreply@youtube.com", "Nuevo video de Cocina Fácil", "Cocina Fácil subió un nuevo video."),
    ("so2", "notification@facebookmail.com", "Luis te etiquetó en una foto", "Luis te etiquetó en una foto."),
    ("so3", "no-reply@tiktok.com", "Tienes 12 nuevos seguidores", "Mira quién empezó a seguirte."),
    ("so4", "messages-noreply@linkedin.com", "Tienes 3 invitaciones", "Personas que quizá conozcas."),
    ("so5", "no-reply@mail.instagram.com", "A ana_r le gustó tu publicación", "A ana_r le gustó tu publicación."),
    ("so6", "noreply@pinterest.com", "Ideas para ti", "Pines que te pueden gustar."),
    ("so7", "notify@x.com", "Tendencias para ti", "Lo más popular hoy en X."),
    ("so8", "noreply@youtube.com", "Recomendaciones de la semana", "Videos que te pueden interesar."),
]
for i, (mid, snd, subj, body) in enumerate(soc):
    add(mid, snd, subj, body, f"2026-10-{10 + i:02d}T20:00:00Z", triage="social", labels=["CATEGORY_SOCIAL"])

# ---------------- Verificaciones repetidas de un tercero (cuenta no verificada) ----------------
for i in range(3):
    add(f"vt{i}", "cuentas@tienda-y.example", "Confirma tu correo en Tienda Y", "Confirma tu correo para activar tu cuenta.", f"2026-10-1{i}T15:00:00Z", triage="aviso", key="VT", status="pendiente", priority="N3")

# ---------------- Boletines y promociones que dicen "urgente" ----------------
promos = [
    ("pr1", "ofertas@tienda-x.example", "URGENTE: últimas horas del Buen Fin", "Aprovecha descuentos de hasta 60%. Darte de baja."),
    ("pr2", "boletin@revista-casa.example", "Último aviso: tu cupón vence hoy", "Usa tu cupón de 15% antes de que expire."),
    ("pr3", "marketing@viajes-sol.example", "¡Urgente! Precios increíbles a Cancún", "Promo exclusiva solo hoy."),
    ("pr4", "newsletter@noticias-mx.example", "Boletín diario", "Las noticias más importantes de hoy."),
    ("pr5", "promos@banco-azul.example", "Acción requerida: aprovecha tu crédito preaprobado", "Oferta exclusiva con meses sin intereses."),
    ("pr6", "deals@electro-shop.example", "Hot Sale: no te pierdas", "Envío gratis en toda la tienda."),
    ("pr7", "hola@cafe-aroma.example", "Novedades de octubre", "Conoce nuestros nuevos productos."),
    ("pr8", "info@cursos-online.example", "Urgente: tu lugar en el webinar gratuito", "Regístrate al webinar gratuito antes de que se llene."),
    ("pr9", "ofertas@super-ahorro.example", "Paga menos esta semana", "Descuento en frutas y verduras."),
    ("pr10", "marketing@autos-k.example", "Último aviso: prueba de manejo", "Promoción exclusiva para ti."),
]
for i, (mid, snd, subj, body) in enumerate(promos):
    add(mid, snd, subj, body, f"2026-10-{8 + i:02d}T14:00:00Z", triage="promo", labels=["CATEGORY_PROMOTIONS"] if i % 2 == 0 else None, list_unsub=f"<mailto:baja@{snd.split('@')[1]}>")

# ---------------- Ambiguos y personales ----------------
amb = [
    ("am1", "tia.rosa@correo.example", "Hola", "¿Cómo están todos por allá? Un abrazo."),
    ("am2", "compadre@correo.example", "Fotos", "Ahí van las fotos del sábado."),
    ("am3", "colega@empresa-z.example", "Re: lo que platicamos", "Sí, luego lo vemos con calma."),
    ("am4", "amiga.laura@correo.example", "Una pregunta", "¿Te acuerdas del nombre del restaurante?"),
    ("am5", "primo@correo.example", "Jaja", "Mira este meme."),
]
for i, (mid, snd, subj, body) in enumerate(amb):
    add(mid, snd, subj, body, f"2026-10-{12 + i:02d}T22:00:00Z", triage="revision")

# ---------------- Avisos informativos varios ----------------
info = [
    ("in1", "notificaciones@banco-azul.example", "Compra aprobada con tu tarjeta", "Se realizó una compra aprobada por $250.00 en Café Aroma.", "bank"),
    ("in2", "alertas@banco-verde.example", "Depósito recibido", "Recibiste un depósito SPEI por $5,000.00.", "bank"),
    ("in3", "reservas@hotel-playa.example", "Reservación confirmada", "Tu reservación confirmada del 12 al 15 de diciembre.", None),
    ("in4", "no-reply@aerolinea-x.example", "Tu pase de abordar", "Aquí está tu pase de abordar para el vuelo AX123.", None),
    ("in5", "sistema@portal-escolar.example", "Calificaciones publicadas", "Ya puedes consultar las calificaciones del parcial.", None),
]
for i, (mid, snd, subj, body, prot) in enumerate(info):
    add(mid, snd, subj, body, f"2026-10-{9 + i:02d}T13:00:00Z", triage="aviso", protected=prot)

# ---------------- Lote adicional (variantes) ----------------
more_bills = [
    ("tmx2", "facturacion@telmex-pagos.example", "Factura Telmex noviembre", "TMX-4502", "589.00", "Tu factura vence el 28/11/2026.", "2026-10-29T16:00:00Z", "2026-11-28", "full"),
    ("cfe2", "avisos@cfe-recibos.example", "Tu recibo CFE de luz", "CFE-88377", "910.00", "Fecha límite de pago: 6 de diciembre.", "2026-10-22T16:00:00Z", "2026-12-06", "last_notice"),
    ("ins2", "billing@insure-us.example", "Policy invoice", "PI-70021", "220.00", "Payment due by November 10, 2026.", "2026-10-21T16:00:00Z", "2026-11-10", "full"),
    ("cel", "cobranza@movil-plus.example", "Factura de tu línea móvil", "MP-33120", "399.00", "Tu factura vence el 3 de noviembre.", "2026-10-18T16:00:00Z", "2026-11-03", "partial"),
    ("dep", "cuotas@club-deportivo.example", "Cuota mensual del club", "CD-0919", "650.00", "Favor de pagar en 5 días.", "2026-10-19T16:00:00Z", "2026-10-24", "other_folio"),
]
bills_extra = more_bills
for code, snd, subj, folio, amount, due_phrase, rec, due, scen in bills_extra:
    key = f"BILL-{code}"
    final = "resuelto" if scen == "full" else "pendiente"
    prio = days_prio(rec, due)
    add(f"{code}-inv", snd, f"{subj} · folio {folio}", f"Su factura folio {folio} por ${amount} MXN está disponible. {due_phrase} Favor de realizar el pago.", rec,
        triage="accion", key=key, status=final, due=due, priority=prio, protected="invoice")
    if scen in {"full", "last_notice"}:
        prefix = "Reminder:" if scen == "full" and "insure" in snd else ("Recordatorio:" if scen == "full" else "Aviso:")
        add(f"{code}-rem", snd, f"{prefix} {subj} · folio {folio}", f"{prefix} la factura folio {folio} por ${amount} sigue pendiente. Por favor pague.", later(rec, 2),
            triage="accion", key=key, status=final, due=due, priority=prio, protected="invoice")
    if scen == "full":
        add(f"{code}-pay", snd, f"Pago recibido · folio {folio}", f"Pago recibido por ${amount} para la factura folio {folio}. Gracias.", later(rec, 4),
            triage="aviso", key=key, status=final, due=due, priority=prio, protected="invoice")
    if scen == "partial":
        add(f"{code}-pay", snd, f"Abono parcial · folio {folio}", f"Abono aplicado de $100.00 a la factura folio {folio}. Pago parcial; resta saldo.", later(rec, 3),
            triage="aviso", key=key, status=final, due=due, priority=prio, protected="invoice")
    if scen == "other_folio":
        add(f"{code}-pay", snd, "Gracias por tu pago", f"Recibimos tu pago de ${amount} de la factura folio XX-{folio[-4:]}1.", later(rec, 3), triage="aviso", protected="invoice")
for i, (mid, snd, subj, body) in enumerate([
    ("so9", "noreply@youtube.com", "Nuevo video de Viajes MX", "Viajes MX subió un nuevo video."),
    ("so10", "no-reply@mail.instagram.com", "Nuevos reels para ti", "Mira los reels de hoy."),
    ("so11", "notification@facebookmail.com", "Cumpleaños de Pedro hoy", "Felicita a Pedro."),
]):
    add(mid, snd, subj, body, f"2026-10-{20 + i:02d}T20:00:00Z", triage="social", labels=["CATEGORY_SOCIAL"])
for i, (mid, snd, subj, body) in enumerate([
    ("pr11", "ofertas@moda-z.example", "Urgente: 2x1 solo hoy", "Promo exclusiva en toda la tienda. Darte de baja."),
    ("pr12", "news@tech-digest.example", "Weekly digest", "Top stories of the week. Unsubscribe."),
]):
    add(mid, snd, subj, body, f"2026-10-{20 + i:02d}T14:00:00Z", triage="promo", list_unsub=f"<mailto:baja@{snd.split('@')[1]}>")
add("sx9", "no-reply@accounts.google.com", "Código de verificación de Google", "G-448812 es tu código de verificación.", "2026-10-21T18:00:00Z", triage="aviso", protected="code")
add("r13", "maestro@academia-k.example", "Tarea pendiente", "Por favor envía la tarea dentro de dos días.", "2026-10-20T16:00:00Z", triage="accion", key="REL-r13", status="pendiente", due="2026-10-22", priority="N1")
add("r14", "jefe@empresa-z.example", "Presentación del cliente", "Necesitamos que envíes la presentación hoy mismo.", "2026-10-21T16:00:00Z", triage="accion", key="REL-r14", status="pendiente", due="2026-10-21", priority="N1")

OUT.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
print(f"{len(rows)} correos → {OUT}")
