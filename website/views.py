from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.views import View
from django.views.generic import TemplateView
import requests

SITE_URL = 'https://behawiorysta.warszawa.pl'


class IndexView(TemplateView):
    template_name = 'index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['recaptcha_public_key'] = settings.RECAPTCHA_PUBLIC_KEY
        return context


class PrivacyPolicyView(TemplateView):
    template_name = 'privacy-policy.html'


class ContactView(View):
    def get(self, request):
        # Formularz znajduje się na stronie głównej. Przekierowanie zapobiega
        # udostępnianiu tej samej treści także pod adresem /contact/.
        return redirect('/#contact', permanent=True)

    def post(self, request):
        try:
            recaptcha_response = request.POST.get('g-recaptcha-response')

            if not recaptcha_response:
                messages.error(request, 'Proszę zaznaczyć pole reCAPTCHA.')
                return redirect('/#contact')

            verify_data = {
                'secret': settings.RECAPTCHA_PRIVATE_KEY,
                'response': recaptcha_response,
            }

            response = requests.post('https://www.google.com/recaptcha/api/siteverify', verify_data)
            result = response.json()

            if not result['success']:
                messages.error(request, 'Weryfikacja reCAPTCHA nie powiodła się. Spróbuj ponownie.')
                return redirect('/#contact')

            name = request.POST.get('name')
            last_name = request.POST.get('last-name')
            email = request.POST.get('email')
            phone = request.POST.get('phone')
            address = request.POST.get('address')
            preferred_date = request.POST.get('preferred-date')
            animal_info = request.POST.get('animal-info')
            gender = request.POST.get('gender')
            animal_breed = request.POST.get('animal-breed')
            appointment_type = request.POST.get('appointment-type')
            message = request.POST.get('message')
            newsletter = request.POST.get('newsletter') == 'on'

            if not all([
                name,
                last_name,
                email,
                phone,
                address,
                preferred_date,
                animal_info,
                gender,
                animal_breed,
                appointment_type,
                message,
            ]):
                messages.error(request, 'Wszystkie pola są wymagane.')
                return redirect('/#contact')

            context = {
                'name': name,
                'last_name': last_name,
                'email': email,
                'phone': phone,
                'address': address,
                'preferred_date': preferred_date,
                'animal_info': animal_info,
                'gender': gender,
                'animal_breed': animal_breed,
                'appointment_type': appointment_type,
                'message': message,
                'newsletter_status': 'Tak' if newsletter else 'Nie',
            }

            html_message = render_to_string('emails/appointment_notification.html', context)
            plain_message = strip_tags(html_message)

            send_mail(
                subject=f'Nowa wiadomość od {name} {last_name}',
                message=plain_message,
                from_email=email,
                recipient_list=['eli.behawiorysta@gmail.com'],
                html_message=html_message,
            )

            messages.success(request, 'Twoja wiadomość została wysłana. Dziękujemy!')
            return redirect('/#contact')

        except Exception:
            messages.error(request, 'Wystąpił błąd podczas wysyłania wiadomości. Spróbuj ponownie.')
            return redirect('/#contact')


def robots_txt(request):
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /contact/\n"
        f"Sitemap: {SITE_URL}/sitemap.xml\n"
    )
    return HttpResponse(content, content_type='text/plain; charset=utf-8')


def sitemap_xml(request):
    content = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>{SITE_URL}/</loc>
    <changefreq>monthly</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>
"""
    return HttpResponse(content, content_type='application/xml; charset=utf-8')
