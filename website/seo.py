import json

from django.conf import settings

from .catalog import SERVICES


def homepage_structured_data():
    prices = [s["price"] for s in SERVICES]
    schema = {
        "@context": "https://schema.org",
        "@type": "ProfessionalService",
        "@id": f"{settings.SITE_URL}/#business",
        "url": f"{settings.SITE_URL}/",
        "name": "Eli Zalewski - Behawiorysta psów i kotów",
        "telephone": settings.CONTACT_PHONE,
        "email": settings.CONTACT_EMAIL,
        "address": settings.BUSINESS_ADDRESS,
        "image": f"{settings.SITE_URL}/static/website/images/portfolio3.jpg",
        "areaServed": "Warszawa",
        "priceRange": f"{min(prices)}-{max(prices)} PLN",
        "hasOfferCatalog": {
            "@type": "OfferCatalog",
            "itemListElement": [
                {
                    "@type": "Offer",
                    "price": str(s["price"]),
                    "priceCurrency": "PLN",
                    "itemOffered": {
                        "@type": "Service",
                        "name": s["name"],
                        "description": s["description"],
                    },
                }
                for s in SERVICES
            ],
        },
    }
    # Escape HTML-significant characters before embedding JSON in a script.
    return (
        json.dumps(schema, ensure_ascii=False)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )
