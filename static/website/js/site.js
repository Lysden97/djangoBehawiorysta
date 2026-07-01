document.addEventListener('DOMContentLoaded', function () {
    var phoneInput = document.getElementById('phone');
    if (phoneInput) {
        phoneInput.addEventListener('input', function () {
            phoneInput.value = phoneInput.value
                .replace(/\D/g, '')
                .replace(/(\d{3})(?=\d)/g, '$1 ')
                .trim();
        });
    }

    var dateInput = document.getElementById('preferred-date');
    if (dateInput && window.flatpickr) {
        window.flatpickr(dateInput, {
            dateFormat: 'd.m.Y',
            minDate: 'today',
            maxDate: new Date().fp_incr(90),
            locale: 'pl',
            disableMobile: true
        });
    }

    document.querySelectorAll('.needs-validation').forEach(function (form) {
        form.addEventListener('submit', function (event) {
            clearValidationMessages();

            var termsValid = validateRequiredCheckbox('terms', 'termsValidationMessage', 'Trzeba zaakceptować zgodę na przetwarzanie danych.');
            var privacyValid = validateRequiredCheckbox('privacy-policy', 'privacyValidationMessage', 'Trzeba zaakceptować politykę prywatności.');

            if (!form.checkValidity() || !termsValid || !privacyValid) {
                event.preventDefault();
                event.stopPropagation();
                form.classList.add('was-validated');

                var firstInvalid = form.querySelector(':invalid, .validation-message');
                if (firstInvalid) {
                    firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }
        }, false);
    });

    var cookieScript = document.querySelector('script[data-privacy-url]');
    var privacyUrl = cookieScript ? cookieScript.dataset.privacyUrl : '/privacy-policy/';

    window.addEventListener('load', function () {
        if (!window.cookieconsent) return;

        window.cookieconsent.initialise({
            palette: {
                popup: { background: '#16231f', text: '#ffffff' },
                button: { background: '#f4c89c', text: '#16231f' }
            },
            theme: 'classic',
            content: {
                message: 'Ta strona używa plików cookies.',
                dismiss: 'Akceptuję',
                link: 'Dowiedz się więcej',
                href: privacyUrl
            }
        });
    });
});

function clearValidationMessages() {
    document.querySelectorAll('.validation-message').forEach(function (message) {
        message.remove();
    });
}

function validateRequiredCheckbox(inputId, messageId, message) {
    var input = document.getElementById(inputId);
    var container = document.getElementById(messageId);

    if (!input || !container || input.checked) {
        return true;
    }

    var messageElement = document.createElement('p');
    messageElement.className = 'validation-message';
    messageElement.textContent = message;
    container.appendChild(messageElement);
    return false;
}
