from __future__ import annotations


def _entry(name: str, region: str, country: str) -> dict[str, str]:
    return {
        "name": name,
        "region": region,
        "country": country,
        "vertical": "travel",
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


TRAVEL: dict[str, dict[str, str]] = {}

_add(TRAVEL, "Booking.com", "GLOBAL", "NL", "booking.com")
_add(TRAVEL, "Airbnb", "GLOBAL", "US", "airbnb.com", "airbnb.mx")
_add(TRAVEL, "Expedia", "GLOBAL", "US", "expedia.com", "expedia.com.mx")
_add(TRAVEL, "Hotels.com", "GLOBAL", "US", "hotels.com")
_add(TRAVEL, "Kayak", "GLOBAL", "US", "kayak.com", "kayak.com.mx")
_add(TRAVEL, "Priceline", "US", "US", "priceline.com")
_add(TRAVEL, "Tripadvisor", "GLOBAL", "US", "tripadvisor.com")
_add(TRAVEL, "Despegar", "LATAM", "AR", "despegar.com", "despegar.com.mx")
_add(TRAVEL, "Best Day", "MX", "MX", "bestday.com.mx")
_add(TRAVEL, "PriceTravel", "MX", "MX", "pricetravel.com")
_add(TRAVEL, "Aeroméxico", "MX", "MX", "aeromexico.com")
_add(TRAVEL, "Volaris", "MX", "MX", "volaris.com")
_add(TRAVEL, "VivaAerobus", "MX", "MX", "vivaaerobus.com")
_add(TRAVEL, "Delta", "US", "US", "delta.com")
_add(TRAVEL, "United", "US", "US", "united.com")
_add(TRAVEL, "American Airlines", "US", "US", "aa.com")
_add(TRAVEL, "Southwest", "US", "US", "southwest.com")
_add(TRAVEL, "JetBlue", "US", "US", "jetblue.com")
_add(TRAVEL, "Alaska Airlines", "US", "US", "alaskaair.com")
_add(TRAVEL, "Air Canada", "CA", "CA", "aircanada.com")
_add(TRAVEL, "WestJet", "CA", "CA", "westjet.com")
_add(TRAVEL, "LATAM", "LATAM", "CL", "latam.com")
_add(TRAVEL, "Avianca", "LATAM", "CO", "avianca.com")
_add(TRAVEL, "Copa", "LATAM", "PA", "copa.com", "copaair.com")
_add(TRAVEL, "GOL", "LATAM", "BR", "voegol.com.br")
_add(TRAVEL, "Azul", "LATAM", "BR", "voeazul.com.br")
_add(TRAVEL, "Iberia", "EU", "ES", "iberia.com")
_add(TRAVEL, "Vueling", "EU", "ES", "vueling.com")
_add(TRAVEL, "Air Europa", "EU", "ES", "aireuropa.com")
_add(TRAVEL, "Lufthansa", "EU", "DE", "lufthansa.com")
_add(TRAVEL, "Air France", "EU", "FR", "airfrance.com")
_add(TRAVEL, "KLM", "EU", "NL", "klm.com")
_add(TRAVEL, "British Airways", "EU", "GB", "britishairways.com")
_add(TRAVEL, "Ryanair", "EU", "IE", "ryanair.com")
_add(TRAVEL, "easyJet", "EU", "GB", "easyjet.com")
_add(TRAVEL, "Marriott", "GLOBAL", "US", "marriott.com")
_add(TRAVEL, "Hilton", "GLOBAL", "US", "hilton.com")
_add(TRAVEL, "Hyatt", "GLOBAL", "US", "hyatt.com")
_add(TRAVEL, "IHG", "GLOBAL", "GB", "ihg.com")
_add(TRAVEL, "Accor", "GLOBAL", "FR", "accor.com")
_add(TRAVEL, "Fiesta Americana", "MX", "MX", "fiestamericana.com")
_add(TRAVEL, "City Express", "MX", "MX", "cityexpress.com")
_add(TRAVEL, "Hoteles Misión", "MX", "MX", "hotelesmision.com.mx")
_add(TRAVEL, "Vrbo", "US", "US", "vrbo.com")
_add(TRAVEL, "Hertz", "GLOBAL", "US", "hertz.com")
_add(TRAVEL, "Avis", "GLOBAL", "US", "avis.com")
_add(TRAVEL, "Budget", "GLOBAL", "US", "budget.com")
_add(TRAVEL, "Enterprise", "US", "US", "enterprise.com")
_add(TRAVEL, "Sixt", "EU", "DE", "sixt.com")
_add(TRAVEL, "Amtrak", "US", "US", "amtrak.com")
_add(TRAVEL, "VIA Rail", "CA", "CA", "viarail.ca")
_add(TRAVEL, "Tren Maya / ADO", "MX", "MX", "ado.com.mx")
_add(TRAVEL, "OpenTable", "US", "US", "opentable.com")
_add(TRAVEL, "Resy", "US", "US", "resy.com")
_add(TRAVEL, "Ticketmaster", "GLOBAL", "US", "ticketmaster.com", "ticketmaster.com.mx")
_add(TRAVEL, "Eventbrite", "GLOBAL", "US", "eventbrite.com")
