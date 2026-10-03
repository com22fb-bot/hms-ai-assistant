"""Anonymised synthetic copies of real mail patterns (no real personal data).

Shapes follow what Yahoo/Gmail imports really store: HTML-only bodies whose
``body_text`` is just the subject, tables, HTML entities, invisible preheader
padding, footers, legal text, quoted replies. Names, card endings, account
and reference numbers are invented.
"""

PAD = "&#847;&zwnj;&shy;&#8199;" * 40
FOOT_AZTECA = (
    "<p>Contáctanos ayuda@banco.example Línea 55 0000 0000</p>"
    "<p>Este correo se constituye como una referencia de los términos en que la operación se realizó.</p>"
    "<p>Protege tus datos y tu dinero, conócelas aquí.</p>"
)


def html_doc(body: str, preheader: str = "") -> str:
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'><title>Aviso</title>"
        "<style>.x{color:#333;font-family:Arial} @media only screen and (max-width:600px){.y{width:100%}}</style>"
        f"</head><body><div style='display:none'>{preheader}</div>{body}"
        "<img src='https://trk.example.com/open.gif?u=1' width='1' height='1'></body></html>"
    )


FIXTURES = [
    {
        "name": "azteca_declined",
        "subject": "Rechazo por saldo insuficiente",
        "sender": "Banco Azteca <notificaciones@bazdigital.com>",
        "body_text": "Rechazo por saldo insuficiente",
        "body_html": html_doc(
            "<table><tr><td>Rechazo por saldo insuficiente</td></tr><tr><td>02/Oct/2026, 09:10:11</td></tr>"
            "<tr><td>Tarjeta: Debito Digital ***1111</td></tr><tr><td>Monto de rechazo:</td><td>$159</td></tr>"
            "<tr><td>Establecimiento: Google Youtubepremium 650-2530</td></tr></table>"
            "<p>Evita el rechazo de tu tarjeta, consulta tu saldo en la App de Banco Azteca.</p>" + FOOT_AZTECA
        ),
        "kind": "payment_declined", "area": "money",
        "idea": ["Banco Azteca", "Google Youtubepremium", "$159", "saldo insuficiente"],
        "quotes": ["Monto de rechazo: $159", "Establecimiento: Google Youtubepremium 650-2530"],
        "facts": {"amount": "$159", "merchant": "Google Youtubepremium", "card_last4": "1111"},
    },
    {
        "name": "azteca_spei",
        "subject": "Notificación Banco Azteca",
        "sender": "Banco Azteca <notificaciones@bazdigital.com>",
        "body_text": "Notificación Banco Azteca",
        "body_html": html_doc(
            "<table><tr><td>DATOS DE LA OPERACIÓN</td></tr><tr><td>Operación</td><td>SPEI</td></tr>"
            "<tr><td>Beneficiario</td><td>Persona Ejemplo</td></tr><tr><td>Importe</td><td>$100</td></tr>"
            "<tr><td>Fecha y hora</td><td>01/Oct/2026, 07:15:33</td></tr><tr><td>Clave de rastreo</td><td>ABC1234567890</td></tr></table>"
            + FOOT_AZTECA
        ),
        "kind": "transfer_sent", "area": "money",
        "idea": ["Enviaste $100", "01/Oct/2026"],
        "quotes": ["Importe $100"],
        "facts": {"amount": "$100", "reference": "ABC1234567890"},
    },
    {
        "name": "cfe_aviso_cobro",
        "subject": "CFE:  Aviso de cobro del servicio suministro de energía eléctrica",
        "sender": "CFE <avisos@cfe.mx>",
        "body_text": (
            "Asunto: Aviso de cobro del servicio suministro de energía eléctrica\r\nFecha: 2 de octubre de 2026\r\n"
            "NOMBRE: PERSONA EJEMPLO\r\nSERVICIO: 000000000000\r\n\r\nEstimado Cliente:\r\n"
            "Te informamos que tu servicio presenta 1 adeudo(s) acumulado(s) por vencer, por el servicio de suministro "
            "de energía eléctrica, con un importe total de $1498.00 M.N.\r\n"
            "SI AL RECIBIR ESTA INFORMACIÓN YA FUE LIQUIDADO EL ADEUDO, AGRADECEREMOS HAGAS CASO OMISO.\r\n"
            "Por lo anterior, te solicitamos liquides el adeudo antes de tu fecha límite de pago, PARA EVITAR LA "
            "SUSPENSION DEL SERVICIO O LA BAJA DEFINITIVA.\r\n\r\nAviso de privacidad: consulta cfe.mx\r\n"
        ),
        "body_html": "",
        "kind": "bill_due", "area": "bills",
        "idea": ["CFE", "$1498.00 M.N."],
        "quotes": ["con un importe total de $1498.00 M.N."],
        "facts": {"amount": "$1498.00 M.N."},
    },
    {
        "name": "bbva_auto_vencido",
        "subject": "Conserva tu Crédito de Auto al corriente",
        "sender": "BBVA <notificaciones@bbva.mx>",
        "body_text": "Conserva tu Crédito de Auto al corriente",
        "body_html": html_doc(
            "<p>Notificaci&oacute;n BBVA</p><p>Hola, Persona:</p><p>Debido al adeudo que presenta tu Cr&eacute;dito de Auto "
            "con terminaci&oacute;n 2222 , te solicitamos el pago de tu saldo vencido. Tu fecha l&iacute;mite de pago fue el "
            "03 de agosto de 2026 .</p><p>Deuda total: $ 150,000.00</p><p>Pago requerido inmediato: $ 9,194.67</p>"
            "<p>Para evitar m&aacute;s cargos e intereses, realiza tu pago en nuestras sucursales o en la app.</p>"
            "<p>Aviso de privacidad en bbva.mx</p>"
        ),
        "kind": "debt_overdue", "area": "money",
        "idea": ["BBVA", "pago vencido", "$9,194.67", "03 de agosto de 2026"],
        "quotes": ["Pago requerido inmediato: $ 9,194.67"],
        "facts": {"amount": "$ 9,194.67", "due_date": "03 de agosto de 2026"},
    },
    {
        "name": "santander_card_not_delivered",
        "subject": "No fue posible entregar tu Tarjeta",
        "sender": "Santander <avisos@envio.santander.com.mx>",
        "body_text": "No fue posible entregar tu Tarjeta",
        "body_html": html_doc(
            "<p>Si no puedes ver este mensaje correctamente haz clic aquí</p><p>Hola, Persona Ejemplo</p>"
            "<p>¡Aviso Santander! No fue posible entregar tu Tarjeta de Debito terminación 3333.</p>"
            "<p>No nos fue posible entregar tu Tarjeta en la dirección que seleccionaste para su recepción y fue devuelta a mensajería.</p>"
            "<p>Comunícate a SuperLínea para conocer más detalles.</p><p>Te recordamos que nuestros operadores telefónicos nunca solicitarán ninguna contraseña, código de seguridad o claves.</p>"
            "<p>Aviso de privacidad Santander</p>"
        ),
        "kind": "card_status", "area": "money",
        "idea": ["Santander no pudo entregar tu tarjeta", "3333"],
        "quotes": ["No nos fue posible entregar tu Tarjeta en la dirección que seleccionaste para su recepción y fue devuelta a mensajería."],
        "facts": {"card_last4": "3333"},
    },
    {
        "name": "cleverbridge_unauthorized",
        "subject": "N.º de referencia 500000001: pago no autorizado para CCleaner Professional",
        "sender": "Cleverbridge <noreply@cleverbridge.com>",
        "body_text": "",
        "body_html": html_doc(
            "<p>Estimado(a) Persona Ejemplo,</p><h2>Pago no autorizado</h2><p>Su pago a Piriform es procesado por Cleverbridge.</p>"
            "<p>Su número de referencia de Cleverbridge : 500000001</p><p>Es posible que haya introducido incorrectamente el número de "
            "tarjeta de crédito, la fecha de caducidad o el código de seguridad. También es posible que haya alcanzado el límite de su tarjeta.</p>"
        ),
        "kind": "payment_declined", "area": "money",
        "idea": ["Cleverbridge", "CCleaner Professional"],
        "quotes": [],
        "facts": {"merchant": "CCleaner Professional", "reference": "500000001"},
    },
    {
        "name": "issste_fopi",
        "subject": "ISSSTE: FOPI de tu préstamo personal número 20000000001",
        "sender": "ISSSTE <notificaciones@issste.gob.mx>",
        "body_text": "ISSSTE: FOPI de tu préstamo personal número 20000000001",
        "body_html": html_doc(
            "<p>Adjunto encontrará el Formato de Pago de Individuales (FOPI) generado desde el Subsistema Integral de Crédito para su "
            "préstamo personal número: 20000000001, los cuales vencen el día: 30/06/2026</p><p>Recuerde considerar lo siguiente: "
            "Imprime dos copias del FOPI. No pagues dos veces con el mismo formato.</p>"
        ),
        "kind": "bill_due", "area": "bills",
        "idea": ["ISSSTE", "30/06/2026"],
        "quotes": [],
        "facts": {"due_date": "30/06/2026", "reference": "20000000001"},
    },
    {
        "name": "ml_shipped",
        "subject": "Tu compra está en camino",
        "sender": "Mercado Libre <info@mercadolibre.com.mx>",
        "body_text": "Tu compra está en camino",
        "body_html": html_doc(
            "<p>Llega entre el 1 y 2 de septiembre</p><p>¡En camino!</p><p>Trampas para hormigas</p>"
            "<p>El día de la entrega te avisaremos en qué horario vamos a pasar por tu domicilio.</p>"
            "<p>¿Necesitas ayuda? Contáctanos</p><p>Administrar preferencias de e-mails</p>"
        ),
        "kind": "order_shipped", "area": "orders",
        "idea": ["Mercado Libre", "va en camino"],
        "quotes": [],
        "facts": {},
    },
    {
        "name": "ml_delivered",
        "subject": "Llegó tu compra, ¡que la disfrutes!",
        "sender": "Mercado Libre <info@info.mercadolibre.com.mx>",
        "body_text": "Llegó tu compra, ¡que la disfrutes!",
        "body_html": html_doc("<p>Entregamos tu paquete.</p><p>Podrás devolver el producto hasta 30 días después de recibirlo.</p>"),
        "kind": "order_delivered", "area": "orders",
        "idea": ["Mercado Libre", "entregado"],
        "quotes": [],
        "facts": {},
    },
    {
        "name": "google_security",
        "subject": "Alerta de seguridad para persona@example.com",
        "sender": "Google <no-reply@accounts.google.com>",
        "body_text": "Se ha accedido a tu cuenta desde un nuevo dispositivo. Si no fuiste tú, revisa la actividad de tu cuenta.",
        "body_html": "",
        "kind": "security_alert", "area": "security",
        "idea": ["Google", "seguridad"],
        "quotes": ["Si no fuiste tú, revisa la actividad de tu cuenta."],
        "facts": {},
    },
    {
        "name": "yahoo_app_password",
        "subject": "Se creó una contraseña de aplicación para tu cuenta de Yahoo",
        "sender": "Yahoo <no-reply@cc.yahoo.com>",
        "body_text": "",
        "body_html": html_doc("<p>Se generó una contraseña de aplicación para tu cuenta.</p><p>Si no fuiste tú, cambia tu contraseña de inmediato.</p>"),
        "kind": "security_alert", "area": "security",
        "idea": ["Yahoo"],
        "quotes": [],
        "facts": {},
    },
    {
        "name": "microsoft_code",
        "subject": "Tu código de un solo uso",
        "sender": "Microsoft <account-security-noreply@accountprotection.microsoft.com>",
        "body_text": "Usa el siguiente código de un solo uso para la cuenta: 482913\nSi no reconoces esta cuenta, puedes ignorar este mensaje.",
        "body_html": "",
        "kind": "verification_code", "area": "security",
        "idea": ["Microsoft", "código"],
        "quotes": [],
        "facts": {},
        "no_digits_in_quotes": True,
    },
    {
        "name": "donexto_magic_link",
        "subject": "Your Donexto sign-in link",
        "sender": "Donexto <noreply@donexto.com>",
        "body_text": "Hi, use this link to sign in to Donexto: https://app.donexto.com/auth/callback?token=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa&type=magiclink\nThis link expires in 1 hour.",
        "body_html": "",
        "kind": "magic_link", "area": "security",
        "idea": ["Donexto"],
        "quotes": [],
        "facts": {},
    },
    {
        "name": "indeed_interviews",
        "subject": "Algunas de tus invitaciones a entrevistas vencerán pronto",
        "sender": "Indeed <invitationstoapply@indeed.com>",
        "body_text": "",
        "body_html": html_doc(
            "<p>Algunas de tus invitaciones a entrevistas vencerán pronto</p><p>Para mejorar la programación, responde a las invitaciones pendientes.</p>"
            "<p>Unsubscribe</p>",
            preheader="Algunas de tus invitaciones " + PAD,
        ),
        "kind": "job", "area": "work",
        "idea": ["Indeed", "entrevista", "vencen pronto"],
        "quotes": [],
        "facts": {},
    },
    {
        "name": "recruiter_reply_quoted",
        "subject": "Re: CV Persona Ejemplo",
        "sender": "Reclutamiento <rh@empresa.example>",
        "body_text": (
            "Buen día Persona, gracias por tu interés. Nos gustaría agendar una llamada el martes 6 de octubre.\n\n"
            "Saludos\n\nEl jueves, 1 de octubre de 2026, 10:00:00 a.m. CST, Persona <persona@yahoo.com> escribió:\n\n"
            "> Adjunto mi CV para la vacante.\n> Quedo atento."
        ),
        "body_html": "",
        "kind": "job", "area": "work",
        "idea": ["Reclutamiento", "respondió sobre tu postulación"],
        "quotes": ["Nos gustaría agendar una llamada el martes 6 de octubre."],
        "facts": {},
        "absent": ["Adjunto mi CV"],
    },
    {
        "name": "gov_thread_outlook_quote",
        "subject": "RE: FONAC, AGUINALDO Y DIFERENCIA AUMENTO",
        "sender": "Recursos Humanos <rh@dif.gob.mx>",
        "body_text": (
            "Buenas tardes, el pago de la diferencia se verá reflejado en la quincena del 15 de octubre.\n"
            "Atentamente\nRecursos Humanos\n\nDe: Persona Ejemplo <persona@yahoo.com>\nEnviado: miércoles, 30 de septiembre de 2026 12:00\n"
            "Para: rh@dif.gob.mx\nAsunto: FONAC, AGUINALDO Y DIFERENCIA AUMENTO\n\nBuen día, quisiera saber cuándo se paga la diferencia.\n\n"
            "AVISO DE CONFIDENCIALIDAD: Este mensaje es confidencial."
        ),
        "body_html": "",
        "kind": "gov_procedure", "area": "government",
        "idea": ["Recursos Humanos", "trámite", "FONAC"],
        "quotes": ["Buenas tardes, el pago de la diferencia se verá reflejado en la quincena del 15 de octubre."],
        "facts": {},
        "absent": ["quisiera saber", "CONFIDENCIALIDAD"],
    },
    {
        "name": "samsung_promo",
        "subject": "Hasta 47% dto. en Pantallas + Hasta 24 MSI",
        "sender": "Samsung <samsung@mx.email.samsung.com>",
        "body_text": "",
        "body_html": html_doc(
            "<p>Hasta 47% dto. en Pantallas</p><p>Compra hoy y paga en hasta 24 MSI con tarjetas participantes.</p>"
            "<p>Si ya no deseas recibir estos correos, darte de baja aquí.</p>",
            preheader=PAD,
        ),
        "kind": "promo", "area": "promos",
        "idea": ["Publicidad de Samsung"],
        "quotes": [],
        "facts": {},
    },
    {
        "name": "newsletter_marketing_subdomain",
        "subject": "¿Quieres VIVIR DE INTERNET?",
        "sender": "Club Ejemplo <hola@mail.beehiiv.com>",
        "body_text": "Hoy te cuento cómo empecé con una idea sencilla.\n\nUnsubscribe | Manage your preferences",
        "body_html": "",
        "kind": "promo", "area": "promos",
        "idea": ["Publicidad de Club Ejemplo"],
        "quotes": [],
        "facts": {},
    },
    {
        "name": "cafe_promo_percent",
        "subject": "Un 50% de Reembolso en tu bebida te espera 🤩",
        "sender": "Cafetería <hola@hola.cafe.example>",
        "body_text": "",
        "body_html": html_doc("<p>Pide desde la app y recibe 50% de reembolso en monedero.</p><p>Términos y condiciones de uso aplican.</p>"),
        "kind": "promo", "area": "promos",
        "idea": ["Publicidad"],
        "quotes": [],
        "facts": {},
    },
    {
        "name": "banamex_statement",
        "subject": "Envio de estado de cuenta",
        "sender": "Banamex <estadosdecuenta@banamex.com>",
        "body_text": "",
        "body_html": html_doc("<p>Estimado cliente:</p><p>Tu estado de cuenta del periodo ya está disponible en Banca en Línea.</p>"),
        "kind": "statement", "area": "money",
        "idea": ["Banamex", "estado de cuenta"],
        "quotes": ["Tu estado de cuenta del periodo ya está disponible en Banca en Línea."],
        "facts": {},
    },
    {
        "name": "costco_cfdi",
        "subject": "Envio de Comprobante Fiscal Digital",
        "sender": "Costco <facturacion@costco.com.mx>",
        "body_text": "Adjuntamos su Comprobante Fiscal Digital (CFDI) por un total de $1,234.50 correspondiente a su compra.",
        "body_html": "",
        "kind": "receipt", "area": "money",
        "idea": ["Costco", "$1,234.50"],
        "quotes": ["Adjuntamos su Comprobante Fiscal Digital (CFDI) por un total de $1,234.50 correspondiente a su compra."],
        "facts": {"amount": "$1,234.50"},
    },
    {
        "name": "clip_received",
        "subject": "Recibiste un pago de $4,160.00",
        "sender": "Clip <no-reply@payclip.com>",
        "body_text": "Recibiste un pago de $4,160.00 con tarjeta el 28/09/2026. El depósito se verá reflejado en tu cuenta.",
        "body_html": "",
        "kind": "transfer_received", "area": "money",
        "idea": ["Recibiste $4,160.00"],
        "quotes": ["Recibiste un pago de $4,160.00 con tarjeta el 28/09/2026."],
        "facts": {"amount": "$4,160.00"},
    },
    {
        "name": "collection_offer",
        "subject": "Liquide su cuenta solo con  $4,500.00, Comuníquese al 5500000000",
        "sender": "Despacho Ejemplo <cobranza@despacho.example>",
        "body_text": "",
        "body_html": html_doc("<p>Estimado cliente, le ofrecemos liquidar su cuenta solo con $4,500.00 este mes.</p><p>Comuníquese hoy mismo.</p>"),
        "kind": "debt_offer", "area": "money",
        "idea": ["liquidar", "$4,500.00", "verifica con tu banco"],
        "quotes": ["Estimado cliente, le ofrecemos liquidar su cuenta solo con $4,500.00 este mes."],
        "facts": {"amount": "$4,500.00"},
    },
    {
        "name": "amazon_terms",
        "subject": "Actualizaciones Importantes de Nuestros Términos y Condiciones",
        "sender": "Amazon <no-reply@amazon.com>",
        "body_text": "Estamos actualizando nuestras Condiciones de Uso a partir del 1 de noviembre de 2026.",
        "body_html": "",
        "kind": "terms_update", "area": "other",
        "idea": ["Amazon", "condiciones"],
        "quotes": [],
        "facts": {},
    },
    {
        "name": "mojibake_bill",
        "subject": "AtenciÃ³n: tu recibo estÃ¡ disponible",
        "sender": "Servicio Ejemplo <avisos@servicio.example>",
        "body_text": "Tu recibo estÃ¡ disponible. El pago de $250.00 vence el 15/10/2026. Gracias por tu preferencia â€” Equipo.",
        "body_html": "",
        "kind": "bill_due", "area": "bills",
        "idea": ["$250.00", "15/10/2026"],
        "quotes": ["El pago de $250.00 vence el 15/10/2026."],
        "facts": {"amount": "$250.00", "due_date": "15/10/2026"},
        "absent": ["Ã", "â€"],
    },
    {
        "name": "css_leftovers_text",
        "subject": "Tu factura de servicios en la nube",
        "sender": "Nube Ejemplo <billing@nube.example>",
        "body_text": (
            "table {width:640px} body[data-outlook-cycle] .container-wide .main-container > table {width:888px} "
            "@media only screen and (max-width: 640px) { .outer-wrapper {width:100% !important} }\n"
            "Tu factura de $12.40 está lista y vence el 20/10/2026."
        ),
        "body_html": "",
        "kind": "bill_due", "area": "bills",
        "idea": ["$12.40", "20/10/2026"],
        "quotes": ["Tu factura de $12.40 está lista y vence el 20/10/2026."],
        "facts": {"amount": "$12.40"},
        "absent": ["{", "@media"],
    },
    {
        "name": "image_placeholder",
        "subject": "Tu pedido #A12345 fue enviado",
        "sender": "Tienda Ejemplo <pedidos@tienda.example>",
        "body_text": "[image: Logo Tienda]\nHola Persona,\nTu pedido #A12345 fue enviado y llegará el 8 de octubre.\n[image: Banner]",
        "body_html": "",
        "kind": "order_shipped", "area": "orders",
        "idea": ["Tienda Ejemplo", "en camino"],
        "quotes": ["Tu pedido #A12345 fue enviado y llegará el 8 de octubre."],
        "facts": {},
        "absent": ["[image"],
    },
    {
        "name": "personal_friend",
        "subject": "Saludo",
        "sender": "Ana Ejemplo <ana.ejemplo@gmail.com>",
        "body_text": "Hola Persona,\n¿Nos vemos el sábado en la tarde para revisar lo del viaje?\n\nEnviado desde Yahoo Mail para Android",
        "body_html": "",
        "kind": "personal", "area": None,
        "idea": ["Ana Ejemplo te escribió", "¿Nos vemos el sábado"],
        "quotes": ["¿Nos vemos el sábado en la tarde para revisar lo del viaje?"],
        "facts": {},
        "absent": ["Enviado desde"],
    },
    {
        "name": "tracking_links",
        "subject": "Tu suscripción fue renovada",
        "sender": "Streaming Ejemplo <billing@streaming.example>",
        "body_text": (
            "Cobramos $99.00 a tu tarjeta el 05/09/2026 por tu plan mensual.\n"
            "Ver detalle: https://click.streaming.example/ls/click?upn=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa&utm_source=mail"
        ),
        "body_html": "",
        "kind": "unknown", "area": None,
        "idea": ["Streaming Ejemplo"],
        "quotes": ["Cobramos $99.00 a tu tarjeta el 05/09/2026 por tu plan mensual."],
        "facts": {"amount": "$99.00"},
        "absent": ["upn=", "utm_source"],
    },
    {
        "name": "rfc2047_subject",
        "subject": "=?UTF-8?Q?Notificaci=C3=B3n_de_pago_rechazado?=",
        "sender": "Banco Ejemplo <alertas@banco.example>",
        "body_text": "Tu pago de $75.00 en Tienda Ejemplo fue rechazado por saldo insuficiente.",
        "body_html": "",
        "kind": "payment_declined", "area": "money",
        "idea": ["$75.00", "saldo insuficiente"],
        "quotes": ["Tu pago de $75.00 en Tienda Ejemplo fue rechazado por saldo insuficiente."],
        "facts": {"amount": "$75.00"},
    },
]
