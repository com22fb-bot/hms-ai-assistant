# Taxonomía v2 del cerebro (detrás de `BRAIN_V1_ENABLED`)

Aprobada por Héctor (13-oct-2026) y definida por ASTRA. ASTRA aprobó este cambio para desarrollo y pruebas. **La activación en producción no está aprobada**: `BRAIN_V1_ENABLED` sigue apagada o ausente.

## Áreas (`brain_signals.area`)
| id | Área | Sombrero |
|---|---|---|
| trabajo | Trabajo y negocios | Ocupación |
| hogar | Hogar y familia | Hogar |
| dinero | Dinero y facturas | Hogar |
| compras | Compras y suscripciones | Hogar |
| salud | Salud y seguros | Personal |
| viajes | Viajes y eventos | Personal |
| promociones | Promociones y social | Personal |

- `area = null` significa **Por revisar**. Es un estado, no un área, y lleva `area_review_reason`. Ya no existe "Otros".
- **Seguridad no es área.** Es la señal transversal `security_flag` (N1/N2) más `security_tags`. Una alerta legítima conserva su área temática: banco o tarjeta va a Dinero; la cuenta de un servicio digital va a Compras (Suscripción digital).
- **Phishing o fraude:** `rule = phishing_suspect`, `security_flag = N1`, `area = null`. No lleva fecha, cobro ni caso.

## Reglas de conflicto implementadas
- Factura de negocio (proveedor, consultoría, nube/hosting, importes en USD/EUR) va a Trabajo. Una factura personal va a Dinero.
- Recibo de nómina va a Trabajo (Nómina laboral). Depósito de nómina va a Dinero (Nómina).
- La antigua `agenda` se reparte por tema: cita médica a Salud; escuela, mascota o servicio doméstico a Hogar; reunión de trabajo a Trabajo; boletos, conciertos y restaurantes a Viajes y eventos.
- Prima de seguro cobrada va a Dinero con la etiqueta `Seguros`. ASTRA la nombra en sus reglas aunque no aparece en la lista de etiquetas de Dinero. Póliza, cobertura y siniestro van a Salud y seguros.

## Etiquetas
Son de vocabulario cerrado (`taxonomy_v2.CATALOG`). Solo se emiten etiquetas del área elegida, con un máximo de 4.

## Detector de phishing para marcas desconocidas (`phishing_v2.py`)
Busca estas señales:
- dominio parecido (marca + `-verifica`, `-soporte`, `-mail`…, o TLD doble);
- petición de contraseña, NIP o CVV;
- cobro pequeño por enlace para "liberar" algo;
- fraude de CEO (transferencia urgente o confidencial a una cuenta nueva);
- rendimientos irreales;
- cripto con depósito;
- premio no solicitado que pide datos.

Decide con una señal fuerte o con dos señales cualesquiera. Frases como "no lo compartas" o "desde la app oficial" anulan la señal de credenciales. `security_unverified` conserva su caso visible en revisión.

## Casos, duplicados y vínculos
- Un asunto idéntico ya no une correos distintos. Solo une respuestas o reenvíos (`Re:`/`Fwd:`) del mismo remitente.
- `content_key` (remitente + asunto normalizado + cuerpo sin firma de móvil) marca `duplicate_of`. Si el original tiene caso, el duplicado se une a ese caso.
- `ref_key` (marca + folio o pedido) marca `related_to`, por ejemplo pedido → envío → reembolso. Registra el vínculo sin fusionar casos.

## Bandera apagada
Nada de esto se ejecuta con la bandera apagada. Todo vive en `app/services/brain_v1/`, y se comprobó la identidad de la salida con la bandera apagada en L5 y L6.
