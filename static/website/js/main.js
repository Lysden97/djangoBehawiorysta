/*
	Prologue by HTML5 UP
	html5up.net | @ajlkn
	Free for personal and commercial use under the CCA 3.0 license (html5up.net/license)
*/

(function($) {

	var	$window = $(window),
		$body = $('body'),
		$nav = $('#nav');

	// Breakpoints.
		breakpoints({
			wide:      [ '961px',  '1880px' ],
			normal:    [ '961px',  '1620px' ],
			narrow:    [ '961px',  '1320px' ],
			narrower:  [ '737px',  '960px'  ],
			mobile:    [ null,     '736px'  ]
		});

	// Play initial animations on page load.
		$window.on('load', function() {
			window.setTimeout(function() {
				$body.removeClass('is-preload');
			}, 100);
		});

	// Nav.
		var $nav_a = $nav.find('a');

		$nav_a
			.addClass('scrolly')
			.on('click', function(e) {

				var $this = $(this);

				// External link? Bail.
					if ($this.attr('href').charAt(0) != '#')
						return;

				// Prevent default.
					e.preventDefault();

				// Deactivate all links.
					$nav_a.removeClass('active');

				// Activate link *and* lock it (so Scrollex doesn't try to activate other links as we're scrolling to this one's section).
					$this
						.addClass('active')
						.addClass('active-locked');

			})
			.each(function() {

				var	$this = $(this),
					href = $this.attr('href'),
					id = href.substring(href.indexOf('#'));

				if (id === href) return

				var $section = $(id);
				// No section for this link? Bail.
					if ($section.length < 1)
						return;

				// Scrollex.
					$section.scrollex({
						mode: 'middle',
						top: '-10vh',
						bottom: '-10vh',
						initialize: function() {

							// Deactivate section.
								$section.addClass('inactive');

						},
						enter: function() {

							// Activate section.
								$section.removeClass('inactive');

							// No locked links? Deactivate all links and activate this section's one.
								if ($nav_a.filter('.active-locked').length == 0) {

									$nav_a.removeClass('active');
									$this.addClass('active');

								}

							// Otherwise, if this section's link is the one that's locked, unlock it.
								else if ($this.hasClass('active-locked'))
									$this.removeClass('active-locked');

						}
					});

			});

	// Scrolly.
		$('.scrolly').scrolly();

	// Header (narrower + mobile).

		// Toggle.
			$(
				'<div id="headerToggle">' +
					'<a href="#header" class="toggle"></a>' +
				'</div>'
			)
				.appendTo($body);

		// Header.
			$('#header')
				.panel({
					delay: 500,
					hideOnClick: true,
					hideOnSwipe: true,
					resetScroll: true,
					resetForms: true,
					side: 'left',
					target: $body,
					visibleClass: 'header-visible'
				});

})(jQuery);

(function($) {
    $(document).ready(function() {
        const dateInput = $('input[name="appointment-date"]');
        if (dateInput.length === 0) return;

        flatpickr(dateInput[0], {
            dateFormat: 'd.m.Y',
            minDate: 'today',
            maxDate: new Date().fp_incr(90),
            locale: 'pl',
            allowInput: false,
            theme: 'light',
            showMonths: 1,
            animate: true,
            altInput: true,
            altFormat: 'j F Y (l)',
            enableTime: false,
            position: 'auto'
        });
    });
})(jQuery);

$(document).ready(function() {
    const $form = $('form');
    const $terms = $('#terms');
    const $messageContainer = $('#termsValidationMessage');

    function validateTerms() {
        $messageContainer.empty();

        if (!$terms.prop('checked')) {
            $messageContainer.html('<div style="color: red; margin-bottom: 15px; font-weight: bold;">Trzeba zaakceptować regulamin aby kontynuować</div>');
            return false;
        }
        return true;
    }

    $terms.on('change', function() {
        if ($(this).prop('checked')) {
            $messageContainer.empty();
        }
    });

    $form.on('submit', function(e) {
        if (!validateTerms()) {
            e.preventDefault();
            $('html, body').animate({
                scrollTop: $messageContainer.offset().top - 100
            }, 500);
        }
    });
});

$(document).ready(function() {
    const $form = $('form');
    const $privacy = $('#privacy-policy');
    const $messageContainer = $('#privacyValidationMessage');

    function validatePrivacy() {
        $messageContainer.empty();

        if (!$privacy.prop('checked')) {
            $messageContainer.html('<div style="color: red; margin-bottom: 15px; font-weight: bold;">Trzeba zaakceptować politykę prywatności aby kontynuować</div>');
            return false;
        }
        return true;
    }

    $privacy.on('change', function() {
        if ($(this).prop('checked')) {
            $messageContainer.empty();
        }
    });

    $form.on('submit', function(e) {
        if (!validatePrivacy()) {
            e.preventDefault();
            $('html, body').animate({
                scrollTop: $messageContainer.offset().top - 100
            }, 500);
        }
    });
});






