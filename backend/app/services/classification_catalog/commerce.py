from __future__ import annotations


def _entry(name: str, region: str, country: str) -> dict[str, str]:
    return {
        "name": name,
        "region": region,
        "country": country,
        "vertical": "commerce",
    }


def _add(
    directory: dict[str, dict[str, str]],
    name: str,
    region: str,
    country: str,
    *domains: str,
) -> None:
    meta = _entry(name, region, country)
    for domain in domains:
        directory[domain.lower().strip()] = meta


COMMERCE: dict[str, dict[str, str]] = {}

# Pedidos, compras, envíos, marketplaces — MX y US primero.
_add(
    COMMERCE,
    "Amazon",
    "GLOBAL",
    "US",
    "amazon.com",
    "amazon.com.mx",
    "amazon.ca",
    "amazon.es",
    "amazon.co.uk",
    "amazon.de",
    "amazon.fr",
    "amazon.it",
    "amazon.com.br",
    "marketplace.amazon.com",
    "amazon.com.au",
)
_add(
    COMMERCE,
    "Mercado Libre",
    "LATAM",
    "MX",
    "mercadolibre.com",
    "mercadolibre.com.mx",
    "mercadolibre.com.ar",
    "mercadolibre.com.co",
    "mercadolibre.cl",
    "mercadolibre.com.pe",
    "mercadolivre.com.br",
)
_add(COMMERCE, "Walmart", "US", "US", "walmart.com", "walmart.com.mx")
_add(COMMERCE, "Liverpool", "MX", "MX", "liverpool.com.mx")
_add(COMMERCE, "Coppel", "MX", "MX", "coppel.com")
_add(COMMERCE, "Elektra", "MX", "MX", "elektra.com.mx")
_add(COMMERCE, "Soriana", "MX", "MX", "soriana.com")
_add(COMMERCE, "Chedraui", "MX", "MX", "chedraui.com.mx")
_add(COMMERCE, "OXXO", "MX", "MX", "oxxo.com")
_add(COMMERCE, "Rappi", "LATAM", "MX", "rappi.com", "rappi.com.mx")
_add(COMMERCE, "Uber Eats / Uber", "GLOBAL", "US", "uber.com", "ubercab.com")
_add(COMMERCE, "DiDi", "MX", "MX", "didiglobal.com", "didi-food.com")
_add(COMMERCE, "CornerShop", "MX", "MX", "cornershopapp.com")
_add(COMMERCE, "Shein", "GLOBAL", "CN", "shein.com", "shein.com.mx")
_add(COMMERCE, "Temu", "GLOBAL", "CN", "temu.com")
_add(COMMERCE, "AliExpress", "GLOBAL", "CN", "aliexpress.com")
_add(COMMERCE, "eBay", "GLOBAL", "US", "ebay.com", "ebay.com.mx")
_add(COMMERCE, "Etsy", "US", "US", "etsy.com")
_add(COMMERCE, "Target", "US", "US", "target.com")
_add(COMMERCE, "Costco", "US", "US", "costco.com", "costco.com.mx")
_add(COMMERCE, "Best Buy", "US", "US", "bestbuy.com", "bestbuy.com.mx")
_add(COMMERCE, "Home Depot", "US", "US", "homedepot.com", "homedepot.com.mx")
_add(COMMERCE, "Lowe's", "US", "US", "lowes.com")
_add(COMMERCE, "IKEA", "GLOBAL", "SE", "ikea.com")
_add(COMMERCE, "Apple Store", "GLOBAL", "US", "email.apple.com")
_add(COMMERCE, "Google Store / Play", "GLOBAL", "US", "googleplay-mail.com", "store.google.com")
_add(COMMERCE, "Shopify", "GLOBAL", "CA", "shopify.com", "shopifyemail.com")
_add(COMMERCE, "eBay Magento / Adobe", "US", "US", "magento.com")
_add(COMMERCE, "Estafeta", "MX", "MX", "estafeta.com")
_add(COMMERCE, "DHL", "GLOBAL", "DE", "dhl.com", "dhl.com.mx")
_add(COMMERCE, "FedEx", "GLOBAL", "US", "fedex.com")
_add(COMMERCE, "UPS", "GLOBAL", "US", "ups.com")
_add(COMMERCE, "USPS", "US", "US", "usps.com")
_add(COMMERCE, "Correos de México", "MX", "MX", "correosdemexico.gob.mx")
_add(COMMERCE, "Paquetexpress", "MX", "MX", "paquetexpress.com.mx")
_add(COMMERCE, "99minutos", "MX", "MX", "99minutos.com")
_add(COMMERCE, "Mercado Envíos", "LATAM", "AR", "mercadoenvios.com")
_add(COMMERCE, "Sealed Air / ShipStation", "US", "US", "shipstation.com")
_add(COMMERCE, "DoorDash", "US", "US", "doordash.com")
_add(COMMERCE, "Instacart", "US", "US", "instacart.com")
_add(COMMERCE, "Grubhub", "US", "US", "grubhub.com")
_add(COMMERCE, "Starbucks", "GLOBAL", "US", "starbucks.com")
_add(COMMERCE, "Nike", "GLOBAL", "US", "nike.com")
_add(COMMERCE, "Adidas", "GLOBAL", "DE", "adidas.com")
_add(COMMERCE, "Sephora", "GLOBAL", "FR", "sephora.com", "sephora.com.mx")
_add(COMMERCE, "Falabella", "LATAM", "CL", "falabella.com")
_add(COMMERCE, "Ripley", "LATAM", "CL", "ripley.cl", "ripley.com.pe")
_add(COMMERCE, "Magazine Luiza", "LATAM", "BR", "magazineluiza.com.br")
_add(COMMERCE, "Americanas", "LATAM", "BR", "americanas.com.br")
_add(COMMERCE, "Shopee", "GLOBAL", "SG", "shopee.com", "shopee.com.mx", "shopee.com.br")
