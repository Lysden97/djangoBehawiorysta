import json
import re

from django.test import TestCase
from django.urls import reverse


class SeoTests(TestCase):
    def test_homepage_contains_current_structured_prices(self):
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)

        html = response.content.decode()
        match = re.search(
            r'<script type="application/ld\+json">(.*?)</script>',
            html,
            re.DOTALL,
        )
        self.assertIsNotNone(match)

        structured_data = json.loads(match.group(1))
        self.assertEqual(structured_data['priceRange'], '80-300 PLN')
        offers = structured_data['hasOfferCatalog']['itemListElement']
        prices = {
            offer['itemOffered']['name']: offer['price'] for offer in offers
        }
        self.assertEqual(prices, {
            'Pierwsza konsultacja behawioralna': '300',
            'Kolejna konsultacja behawioralna': '200',
            'Trening': '150',
            'Konsultacja online': '200',
            'Spacer': '80',
            'Opieka w domu': '250',
        })

    def test_seo_endpoints(self):
        robots = self.client.get(reverse('robots-txt'))
        self.assertEqual(robots.status_code, 200)
        self.assertContains(
            robots,
            'Sitemap: https://behawiorysta.warszawa.pl/sitemap.xml',
        )

        sitemap = self.client.get(reverse('sitemap-xml'))
        self.assertEqual(sitemap.status_code, 200)
        self.assertContains(
            sitemap,
            '<loc>https://behawiorysta.warszawa.pl/</loc>',
        )

    def test_contact_get_redirects_to_canonical_homepage_section(self):
        response = self.client.get(reverse('contact'))
        self.assertRedirects(
            response,
            '/#contact',
            status_code=301,
            fetch_redirect_response=False,
        )
