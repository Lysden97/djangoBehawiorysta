"""Single source of truth for visible prices, choices and structured data."""

SERVICES = (
    dict(
        id="first",
        name="Pierwsza konsultacja behawioralna",
        price=300,
        unit="",
        image="kiedybeh.jpg",
        description="Dwugodzinne spotkanie, analiza problemu, wywiad i pierwsze zalecenia do pracy.",
    ),
    dict(
        id="followup",
        name="Kolejna konsultacja behawioralna",
        price=200,
        unit="",
        image="kolejna_konsultacja.jpg",
        description="Godzinne spotkanie kontrolne, korekta planu i dalsze prowadzenie przypadku.",
    ),
    dict(
        id="training",
        name="Trening",
        price=150,
        unit="",
        image="portfolio3.jpg",
        description="Godzina praktycznej pracy nad konkretną umiejętnością lub zachowaniem.",
    ),
    dict(
        id="online",
        name="Konsultacja online",
        price=200,
        unit="",
        image="portfolio6.jpg",
        description="Godzinna konsultacja zdalna i plan działania.",
    ),
    dict(
        id="walk",
        name="Spacer",
        price=80,
        unit="",
        image="portfolio5.jpg",
        description="Trzydziestominutowy spacer lub wsparcie w codziennej opiece.",
    ),
    dict(
        id="care",
        name="Opieka w domu",
        price=250,
        unit="/dzień",
        image="portfolio4.jpg",
        description="Dzień opieki w miejscu zamieszkania dopasowanej do potrzeb zwierzęcia.",
    ),
)


def service_label(service):
    return f"{service['name']} ({service['price']} zł{service['unit']})"
