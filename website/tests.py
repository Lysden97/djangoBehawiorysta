import json
import re

from django.test import TestCase, override_settings
from django.urls import reverse

from .forms import ContactForm
from .views import homepage_context


class SeoTests(TestCase):
    @override_settings(SITE_URL="https://new.example", CONTACT_EMAIL="hello@new.example")
    def test_site_configuration_and_single_contact_anchor(self):
        response = self.client.get("/")
        self.assertContains(response, "https://new.example/")
        self.assertContains(response, "hello@new.example")
        self.assertContains(response, 'id="contact"', count=1)
        self.assertNotContains(response, "newsletter")
        self.assertContains(self.client.get("/privacy-policy/"), "noindex,follow")

    def test_homepage_contains_current_structured_prices(self):
        response = self.client.get(reverse("index"))
        self.assertEqual(response.status_code, 200)

        html = response.content.decode()
        match = re.search(
            r'<script type="application/ld\+json">(.*?)</script>',
            html,
            re.DOTALL,
        )
        self.assertIsNotNone(match)

        structured_data = json.loads(match.group(1))
        self.assertEqual(structured_data["priceRange"], "80-300 PLN")
        offers = structured_data["hasOfferCatalog"]["itemListElement"]
        prices = {offer["itemOffered"]["name"]: offer["price"] for offer in offers}
        self.assertEqual(
            prices,
            {
                "Pierwsza konsultacja behawioralna": "300",
                "Kolejna konsultacja behawioralna": "200",
                "Trening": "150",
                "Konsultacja online": "200",
                "Spacer": "80",
                "Opieka w domu": "250",
            },
        )

    def test_structured_data_escapes_html_and_preserves_values(self):
        address = '</script><script>alert("test")</script> & Warszawa > centrum'
        with override_settings(BUSINESS_ADDRESS=address):
            response = self.client.get(reverse("index"))
        match = re.search(
            r'<script type="application/ld\+json">(.*?)</script>',
            response.content.decode(),
            re.DOTALL,
        )
        self.assertIsNotNone(match)
        serialized = match.group(1)
        self.assertEqual(json.loads(serialized)["address"], address)
        for character in "<>&":
            self.assertNotIn(character, serialized)

    def test_homepage_context_preserves_invalid_bound_form(self):
        form = ContactForm({"name": "Jan"})
        self.assertFalse(form.is_valid())
        context = homepage_context(form)
        self.assertIs(context["form"], form)
        self.assertEqual(context["form"]["name"].value(), "Jan")
        self.assertIn("email", context["form"].errors)

    def test_seo_endpoints(self):
        robots = self.client.get(reverse("robots-txt"))
        self.assertEqual(robots.status_code, 200)
        self.assertContains(
            robots,
            "Sitemap: https://behawiorysta.warszawa.pl/sitemap.xml",
        )

        sitemap = self.client.get(reverse("sitemap-xml"))
        self.assertEqual(sitemap.status_code, 200)
        self.assertContains(
            sitemap,
            "<loc>https://behawiorysta.warszawa.pl/</loc>",
        )

    def test_contact_get_redirects_to_canonical_homepage_section(self):
        response = self.client.get(reverse("contact"))
        self.assertRedirects(
            response,
            "/#contact",
            status_code=301,
            fetch_redirect_response=False,
        )
