# 1. Bazowy obraz z Pythonem
FROM python:3.10-slim

# 2. Ustawiamy katalog roboczy w kontenerze
WORKDIR /app

# 3. Kopiujemy pliki wymagane do instalacji pakietów
COPY requirements.txt /app/

# 4. Instalujemy zależności
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# 5. Kopiujemy cały kod aplikacji
COPY . /app/

# 6. Tworzymy katalog na statyczne pliki
RUN mkdir -p /app/staticfiles

# 7. Zbieramy statyczne pliki Django (musisz mieć poprawnie ustawione STATIC_ROOT w settings.py)
RUN python manage.py collectstatic --noinput

# 8. Otwieramy port 9000
EXPOSE 9000

# 9. Komenda startowa uruchamia Gunicorna na porcie 8000
CMD ["gunicorn", "djangoBehawiorysta.wsgi:application", "--bind", "0.0.0.0:9000", "--workers", "3"]