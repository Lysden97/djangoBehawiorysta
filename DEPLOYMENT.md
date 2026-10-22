# Wdrożenie i utrzymanie VPS

Wymagania: Linux, Docker Engine i **Compose v2**, działający cron, DNS A/AAAA
obu nazw skierowane na VPS, publiczne TCP 80/443. Nie publikuj portu aplikacji
8000. Polecenia wykonuj w katalogu projektu kontem z dostępem do Dockera.

## Konfiguracja

Skopiuj `.env.example` do `.env.prod`, a `.env.ssl.example` do `.env.ssl`.
Uzupełnij własne wartości. Dla istniejącego wdrożenia zachowaj dotychczasowy
SECRET_KEY i klucze reCAPTCHA. Nie nadpisuj plików produkcyjnych przykładami.

W `.env.prod` ustaw:

```dotenv
DEBUG=False
SECRET_KEY=<losowy-sekret-minimum-50-znakow>
SITE_URL=https://example.com
ALLOWED_HOSTS=example.com,www.example.com
CSRF_TRUSTED_ORIGINS=https://example.com,https://www.example.com
CONTACT_EMAIL=contact@example.com
CONTACT_PHONE=+48123456789
BUSINESS_ADDRESS="Twój adres firmy"
CONTACT_RECIPIENTS=owner@example.com
DEFAULT_FROM_EMAIL=noreply@example.com
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=<konto-smtp>
EMAIL_HOST_PASSWORD=<haslo-smtp>
EMAIL_TIMEOUT=10
RECAPTCHA_ENABLED=True
RECAPTCHA_PUBLIC_KEY=<klucz-publiczny-v2-checkbox>
RECAPTCHA_PRIVATE_KEY=<klucz-prywatny>
RECAPTCHA_HOSTNAMES=example.com,www.example.com
```

Pozostałe opcje i limity opisano w `.env.example`. Nadawca musi być dozwolony
przez operatora SMTP; skonfiguruj też SPF/DKIM/DMARC u swojego dostawcy.
Odbiorców rozdzielaj przecinkami. Nie ustawiaj `SECURE_SSL_REDIRECT=False` na VPS.

W `.env.ssl` wpisz email konta Let's Encrypt, główną domenę i opcjonalny alias
www. `SITE_URL` musi wskazywać `https://` + `LETSENCRYPT_DOMAIN`.
Zmienne z `.env.ssl` generują konfigurację Nginx i ścieżki certyfikatów.
Nie umieszczaj protokołu ani ukośników w nazwach domen.

## Istniejący VPS: najpierw zachowaj bazę!

Poprzednia wersja miała SQLite w `/app/db.sqlite3` wewnątrz kontenera. Nowy
wolumen sam nie przejmie tych danych. **Przed `up --build`** wykonaj:

```bash
mkdir -p backups
chmod 700 backups
docker compose stop django-web
docker compose cp django-web:/app/db.sqlite3 backups/legacy.sqlite3
chmod 600 backups/legacy.sqlite3
```

Sprawdź, że kopia istnieje. Jeżeli bazy nie ma, ustal, czy wdrożenie faktycznie
nie zawiera danych; nie zakładaj tego automatycznie. Starego kontenera nie usuwaj
przed poprawnym zakończeniem kopii. Teraz zbuduj nowy obraz i importuj bazę do
**pustego** wolumenu. Jednorazowy import działa jako root, aby odczytać chronioną
kopię niezależnie od UID konta VPS; ustawia właściciela bazy na `appuser`.
Import odmówi nadpisania istniejącego pliku:

```bash
docker compose build django-web
docker compose run --rm --no-deps --user root -v "$PWD/backups:/restore:ro" django-web sh -c 'test ! -e /app/data/db.sqlite3 && cp /restore/legacy.sqlite3 /app/data/db.sqlite3 && chown appuser:appuser /app/data/db.sqlite3 && chmod 600 /app/data/db.sqlite3'
```

Przy przywracaniu kopii ze starszego
wdrożenia zachowaj też jego SECRET_KEY. Migracje uruchamiają się na starcie.

## Start i SSL

```bash
sudo bash deploy/init-letsencrypt.sh
sudo bash deploy/install-certbot-cron.sh
docker compose exec -T django-web python manage.py check --deploy
docker compose run --rm certbot renew --dry-run
```

Bootstrap udostępnia HTTP dla ACME, pobiera certyfikat i przełącza Nginx na HTTPS.
Przy już istniejącym certyfikacie nie żąda nowego. Zmiana zestawu domen wymaga
osobnego rozszerzenia certyfikatu w Certbocie. Cron działa codziennie o 03:17
(czas VPS); przeładowuje Nginx po udanej próbie odnowienia. O 03:37 usuwa wygasłe
liczniki limitów. Zapewnij działającą usługę `cron` i instalację Compose dostępną
także dla root. Ścieżka projektu nie może zawierać spacji ani znaków specjalnych.
Log: `/var/log/django-behawiorysta-certbot.log`; skonfiguruj jego rotację na VPS.

## Kolejne aktualizacje

Nginx automatycznie odświeża adres `django-web` przez DNS Dockera co 5 sekund.
Odtworzenie aplikacji ze zmianą IP nie wymaga przeładowania proxy. Przy aktualizacji
pojedynczego backendu możliwa jest krótka przerwa w obsłudze żądań.

Konfiguracja wymaga Nginx co najmniej 1.27.3. Przy pierwszym wdrożeniu tej poprawki
odśwież obraz i odtwórz Nginx, aby załadować nową konfigurację:

```bash
docker compose pull nginx
docker compose up -d --force-recreate --no-deps nginx
```

Przy kolejnych aktualizacjach:

```bash
docker compose up -d --build django-web nginx
docker compose logs --tail=100 django-web nginx
```

Nie używaj `docker compose down -v`: usuwa trwałe wolumeny.
Katalog `data/certbot` przechowuje certyfikaty; nie zmieniaj uprawnień kluczy
na publicznie czytelne. Baza i certyfikaty są wykluczone z kontekstu budowania.

Pliki statyczne w produkcji są wersjonowane hashem treści przez manifest Django.
Zmiana CSS, JavaScript, obrazu lub fontu zmienia jego adres. Nginx ustawia długi
cache (`public, max-age=2592000, immutable`) dla nazw z hashem; adresy bez wersji
wymagają rewalidacji (`no-cache`). Development i zwykłe testy nie wymagają manifestu.

Przy pierwszym wdrożeniu wersjonowania przebuduj aplikację i odtwórz Nginx,
aby załadować nową politykę nagłówków:

```bash
docker compose up -d --build django-web
docker compose up -d --force-recreate --no-deps nginx
```

Start aplikacji wykonuje `collectstatic` przed uruchomieniem Gunicorna. Zachowaj
dotychczasowy wolumen `staticfiles` i starsze pliki z hashem, aby wcześniej otwarte
strony nadal mogły pobierać zasoby. Nie używaj `collectstatic --clear` podczas
aktualizacji. Wersjonowanie dotyczy lokalnych zasobów; biblioteki CDN pozostają
niezmienione. Przy zmianie konfiguracji Nginx trzeba odtworzyć kontener: plik jest
renderowany na starcie, więc samo `nginx -s reload` nie wczyta zmian szablonu.
Compose montuje również `deploy/nginx-security-headers.conf`. Wspólny plik
zapewnia nagłówki bezpieczeństwa dla odpowiedzi aplikacji, plików statycznych
i błędów 404; aktualizując konfigurację, zachowaj ten mount.

Test odzyskiwania połączenia i polityki cache można uruchomić lokalnie:

```bash
docker build -t behawiorysta:test .
python scripts/test_nginx_integration.py
```

Test używa obrazu Nginx wskazanego w Compose, tymczasowego certyfikatu i osobnej
sieci. Nie wymaga `.env.prod` ani certyfikatów produkcyjnych; sprząta własne
kontenery i sieć także po niepowodzeniu.

## Backup i odtworzenie

Wykonuj kopię przed aktualizacją i cyklicznie. Polecenie korzysta z SQLite Backup
API, więc działa również na aktywnej bazie. Używaj nowej nazwy dla każdej kopii:

```bash
docker compose exec -T django-web python manage.py backup_database /app/data/backup-2026-09-16.sqlite3
docker compose cp django-web:/app/data/backup-2026-09-16.sqlite3 backups/backup-2026-09-16.sqlite3
chmod 600 backups/backup-2026-09-16.sqlite3
```

Przechowuj zaszyfrowaną kopię poza VPS, stosuj retencję i okresowo testuj
odtwarzanie. Kopia w tym samym wolumenie nie chroni przed awarią serwera.

Odtworzenie: zatrzymaj `django-web`, zachowaj aktualną bazę pod nową nazwą,
następnie skopiuj wybraną kopię do `/app/data/db.sqlite3` kontenerem jednorazowym
jak przy imporcie powyżej. Właścicielem ma być `appuser`, prawa `600`.
Uruchom `docker compose up -d django-web` i sprawdź logi oraz formularz.
Kopiuj bazę przy zatrzymanej aplikacji; nie zastępuj aktywnego pliku SQLite.

## Sprawdzenie po wdrożeniu

- HTTP i alias www prowadzą do głównej domeny HTTPS; wyzwania ACME są dostępne.
- `/robots.txt` i `/sitemap.xml` wskazują właściwą domenę.
- Błędny formularz zachowuje dane; poprawny dociera do odbiorcy z Reply-To klienta.
- Limit zwraca HTTP 429. Przy SMTP timeout zwracane jest 503, bez szczegółów serwera.
- Google reCAPTCHA akceptuje hostnames wpisane w panelu i `.env.prod`.
- Baza pozostaje dostępna po odtworzeniu kontenera.

Przed publikacją zaktualizuj treść polityki prywatności do faktycznych dostawców,
przetwarzania przez reCAPTCHA i retencji poczty. Ten dokument nie jest opinią prawną.
