/**
 * Nexus Flow - Modal Feature Module
 * Opens and closes modals. Closes when clicking outside.
 * 
 * Required HTML:
 *   <button data-open-modal="myModal">Open Modal</button>
 *   <div class="modal" id="myModal" aria-hidden="true">
 *     <div class="modal-content">
 *       <button class="modal-close" data-close-modal aria-label="Close"><i class="fa-solid fa-xmark"></i></button>
 *       <h2>Modal Title</h2>
 *       <p>Modal content</p>
 *     </div>
 *   </div>
 * 
 * Modals need class 'modal', open buttons use data-open-modal="id",
 * close buttons use data-close-modal.
 */
(function () {
  'use strict';

  const MODAL_SELECTOR = '.modal';
  const OPEN_TRIGGER_SELECTOR = '[data-open-modal]';
  const CLOSE_TRIGGER_SELECTOR = '[data-close-modal], .modal-close';

  function openModal(modalId) {
    const modal = modalId ? document.getElementById(modalId) : null;
    if (!modal) {
      // If no specific id, open the first modal
      document.querySelectorAll(MODAL_SELECTOR).forEach(function (m) {
        if (m.classList.contains('active')) closeModal(m);
      });
      return;
    }
    modal.classList.add('active');
    modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
  }

  function closeModal(modal) {
    if (typeof modal === 'string') {
      modal = document.getElementById(modal);
    }
    if (!modal) {
      document.querySelectorAll(MODAL_SELECTOR).forEach(function (m) {
        m.classList.remove('active');
        m.setAttribute('aria-hidden', 'true');
      });
      document.body.style.overflow = '';
      return;
    }
    modal.classList.remove('active');
    modal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  }

  function initModal() {
    // Open triggers
    document.querySelectorAll(OPEN_TRIGGER_SELECTOR).forEach(function (trigger) {
      trigger.addEventListener('click', function (e) {
        e.preventDefault();
        const modalId = trigger.getAttribute('data-open-modal');
        openModal(modalId);
      });
    });

    // Close triggers
    document.querySelectorAll(CLOSE_TRIGGER_SELECTOR).forEach(function (closeBtn) {
      closeBtn.addEventListener('click', function (e) {
        e.preventDefault();
        const modal = closeBtn.closest(MODAL_SELECTOR);
        if (modal) {
          closeModal(modal);
        }
      });
    });

    // Close when clicking outside the modal content
    document.querySelectorAll(MODAL_SELECTOR).forEach(function (modal) {
      modal.addEventListener('click', function (e) {
        if (e.target === modal) {
          closeModal(modal);
        }
      });
    });

    // Close on Escape key
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        closeModal(null);
      }
    });
  }

  // Initialize on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initModal);
  } else {
    initModal();
  }
})();