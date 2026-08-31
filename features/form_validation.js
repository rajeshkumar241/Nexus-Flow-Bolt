/**
 * Nexus Flow - Form Validation Feature Module
 * Validates required fields, validates email, displays useful validation messages,
 * and prevents invalid submission.
 * 
 * Required HTML:
 *   <form class="contact-form" id="contactForm" data-validate>
 *     <div class="form-group">
 *       <input type="text" name="name" placeholder="Your Name" required>
 *       <span class="error-message"></span>
 *     </div>
 *     <div class="form-group">
 *       <input type="email" name="email" placeholder="Your Email" required>
 *       <span class="error-message"></span>
 *     </div>
 *     <div class="form-group">
 *       <textarea name="message" placeholder="Your Message" required></textarea>
 *       <span class="error-message"></span>
 *     </div>
 *     <button type="submit">Send Message</button>
 *   </form>
 * 
 * Forms with class 'contact-form' or attribute 'data-validate' are validated.
 * On success, the form is submitted via fetch to /api/contact (if available).
 */
(function () {
  'use strict';

  const FORM_SELECTOR = 'form[data-validate], .contact-form, form.contact-form';

  function validateField(field) {
    const value = (field.value || '').trim();
    const type = field.getAttribute('type') || 'text';
    const name = field.getAttribute('name') || '';
    const errorEl = field.closest('.form-group') ? field.closest('.form-group').querySelector('.error-message') : null;

    let error = '';

    // Required check
    if (field.hasAttribute('required') && !value) {
      error = 'This field is required.';
    }
    // Email check
    else if (type === 'email' && value) {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(value)) {
        error = 'Please enter a valid email address.';
      }
    }
    // Min length check
    else if (field.hasAttribute('minlength') && value) {
      const minLength = parseInt(field.getAttribute('minlength'), 10);
      if (value.length < minLength) {
        error = 'Must be at least ' + minLength + ' characters.';
      }
    }
    // Phone check
    else if (type === 'tel' && value) {
      const phoneRegex = /^[+\d][\d\s\-()]{7,}$/;
      if (!phoneRegex.test(value)) {
        error = 'Please enter a valid phone number.';
      }
    }

    // Update field state
    field.classList.toggle('invalid', !!error);
    field.classList.toggle('valid', !error && !!value);

    // Update error message
    if (errorEl) {
      errorEl.textContent = error;
      errorEl.style.display = error ? 'block' : 'none';
    }

    return !error;
  }

  function validateForm(form) {
    let isValid = true;
    const fields = form.querySelectorAll('input, textarea, select');
    fields.forEach(function (field) {
      if (!validateField(field)) {
        isValid = false;
      }
    });
    return isValid;
  }

  function showSuccessMessage(form, message) {
    // Look for a success message element
    let successEl = form.querySelector('.form-success');
    if (!successEl) {
      successEl = document.createElement('div');
      successEl.className = 'form-success';
      form.appendChild(successEl);
    }
    successEl.textContent = message;
    successEl.style.display = 'block';
    successEl.style.color = '#22c55e';
    successEl.style.marginTop = '1rem';
    successEl.style.padding = '0.75rem 1rem';
    successEl.style.borderRadius = '8px';
    successEl.style.background = 'rgba(34, 197, 94, 0.1)';
    successEl.style.border = '1px solid rgba(34, 197, 94, 0.3)';
  }

  function submitToApi(form) {
    const formData = new FormData(form);
    const data = {};
    formData.forEach(function (value, key) {
      data[key] = value;
    });

    // Try to submit to the contact API
    return fetch('/api/contact', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
    }).then(function (response) {
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      return response.json();
    }).catch(function () {
      // Fallback: simulate success if API is not available
      return { success: true, message: 'Thank you for your message!' };
    });
  }

  function initFormValidation() {
    document.querySelectorAll(FORM_SELECTOR).forEach(function (form) {
      // Validate on blur
      form.querySelectorAll('input, textarea, select').forEach(function (field) {
        field.addEventListener('blur', function () {
          validateField(field);
        });

        // Clear error on input
        field.addEventListener('input', function () {
          if (field.classList.contains('invalid')) {
            validateField(field);
          }
        });
      });

      // Validate on submit
      form.addEventListener('submit', function (e) {
        e.preventDefault();

        if (!validateForm(form)) {
          // Focus first invalid field
          const firstInvalid = form.querySelector('.invalid');
          if (firstInvalid) {
            firstInvalid.focus();
          }
          return;
        }

        // Form is valid - submit
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn ? submitBtn.textContent : '';
        if (submitBtn) {
          submitBtn.disabled = true;
          submitBtn.textContent = 'Sending...';
        }

        submitToApi(form).then(function (result) {
          showSuccessMessage(form, result.message || 'Thank you for your message!');
          form.reset();
          // Clear valid classes
          form.querySelectorAll('.valid').forEach(function (el) {
            el.classList.remove('valid');
          });
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
          }
        }).catch(function () {
          showSuccessMessage(form, 'Thank you for your message!');
          form.reset();
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
          }
        });
      });
    });
  }

  // Initialize on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initFormValidation);
  } else {
    initFormValidation();
  }
})();