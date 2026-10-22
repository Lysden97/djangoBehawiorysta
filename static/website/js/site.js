document.addEventListener('DOMContentLoaded', function () {
    var dateInput = document.getElementById('id_preferred_date');
    if (dateInput && window.flatpickr) {
        window.flatpickr(dateInput, {
            dateFormat: 'Y-m-d',
            altInput: true,
            altFormat: 'd.m.Y',
            minDate: 'today',
            maxDate: new Date().fp_incr(90),
            locale: 'pl',
            disableMobile: true
        });
    }

    document.querySelectorAll('.needs-validation').forEach(function (form) {
        form.addEventListener('submit', function (event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
                form.classList.add('was-validated');

                var firstInvalid = form.querySelector(':invalid');
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
