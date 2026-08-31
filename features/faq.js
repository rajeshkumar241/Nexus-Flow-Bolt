/**
 * Nexus Flow - FAQ Accordion Feature Module
 * Expands and collapses FAQ answers.
 * 
 * Required HTML:
 *   <div class="faq">
 *     <div class="faq-item">
 *       <button class="faq-question">What is your question?</button>
 *       <div class="faq-answer">
 *         <p>The answer goes here.</p>
 *       </div>
 *     </div>
 *   </div>
 * 
 * The .faq-answer should be hidden by default (max-height: 0 / display: none).
 * Adding class 'active' to .faq-item expands it.
 */
(function () {
  'use strict';

  const FAQ_SELECTOR = '.faq';
  const FAQ_ITEM_SELECTOR = '.faq-item';
  const FAQ_QUESTION_SELECTOR = '.faq-question';
  const FAQ_ANSWER_SELECTOR = '.faq-answer';

  function initFaq() {
    document.querySelectorAll(FAQ_SELECTOR).forEach(function (faq) {
      // If the FAQ is an accordion (only one open at a time)
      const isAccordion = faq.getAttribute('data-accordion') === 'true';

      faq.querySelectorAll(FAQ_ITEM_SELECTOR).forEach(function (item) {
        const question = item.querySelector(FAQ_QUESTION_SELECTOR);
        const answer = item.querySelector(FAQ_ANSWER_SELECTOR);

        if (!question || !answer) return;

        // Set initial aria attributes
        const answerId = answer.id || ('faq-answer-' + Math.random().toString(36).substr(2, 9));
        answer.id = answerId;
        question.setAttribute('aria-expanded', item.classList.contains('active') ? 'true' : 'false');
        question.setAttribute('aria-controls', answerId);

        question.addEventListener('click', function () {
          const isActive = item.classList.contains('active');

          if (isAccordion) {
            // Close all other items
            faq.querySelectorAll(FAQ_ITEM_SELECTOR).forEach(function (otherItem) {
              otherItem.classList.remove('active');
              const otherQuestion = otherItem.querySelector(FAQ_QUESTION_SELECTOR);
              if (otherQuestion) {
                otherQuestion.setAttribute('aria-expanded', 'false');
              }
            });
          }

          // Toggle this item
          item.classList.toggle('active', !isActive);
          question.setAttribute('aria-expanded', String(!isActive));
        });
      });
    });
  }

  // Initialize on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initFaq);
  } else {
    initFaq();
  }
})();