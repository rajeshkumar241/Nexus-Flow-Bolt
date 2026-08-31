/**
 * Nexus Flow - Image Slider/Carousel Feature Module
 * Next/previous controls and automatic sliding.
 * 
 * Required HTML:
 *   <div class="slider" data-autoplay="true" data-interval="5000">
 *     <div class="slider-track">
 *       <div class="slide active"><img src="slide1.jpg" alt=""></div>
 *       <div class="slide"><img src="slide2.jpg" alt=""></div>
 *       <div class="slide"><img src="slide3.jpg" alt=""></div>
 *     </div>
 *     <button class="slider-prev" aria-label="Previous"><i class="fa-solid fa-chevron-left"></i></button>
 *     <button class="slider-next" aria-label="Next"><i class="fa-solid fa-chevron-right"></i></button>
 *     <div class="slider-dots"></div>
 *   </div>
 */
(function () {
  'use strict';

  const SLIDER_SELECTOR = '.slider, [data-slider]';

  function initSlider(slider) {
    const track = slider.querySelector('.slider-track');
    const slides = slider.querySelectorAll('.slide');
    const prevBtn = slider.querySelector('.slider-prev');
    const nextBtn = slider.querySelector('.slider-next');
    const dotsContainer = slider.querySelector('.slider-dots');
    const autoplay = slider.getAttribute('data-autoplay') === 'true';
    const interval = parseInt(slider.getAttribute('data-interval') || '5000', 10);

    if (slides.length === 0) return;

    let currentIndex = 0;
    let autoplayTimer = null;

    function showSlide(index) {
      currentIndex = (index + slides.length) % slides.length;
      slides.forEach(function (slide, i) {
        slide.classList.toggle('active', i === currentIndex);
      });

      // Update dots
      if (dotsContainer) {
        const dots = dotsContainer.querySelectorAll('.slider-dot');
        dots.forEach(function (dot, i) {
          dot.classList.toggle('active', i === currentIndex);
        });
      }
    }

    function nextSlide() {
      showSlide(currentIndex + 1);
    }

    function prevSlide() {
      showSlide(currentIndex - 1);
    }

    function startAutoplay() {
      if (autoplay && !autoplayTimer) {
        autoplayTimer = setInterval(nextSlide, interval);
      }
    }

    function stopAutoplay() {
      if (autoplayTimer) {
        clearInterval(autoplayTimer);
        autoplayTimer = null;
      }
    }

    // Create dots
    if (dotsContainer) {
      dotsContainer.innerHTML = '';
      slides.forEach(function (_, i) {
        const dot = document.createElement('button');
        dot.className = 'slider-dot' + (i === 0 ? ' active' : '');
        dot.setAttribute('aria-label', 'Go to slide ' + (i + 1));
        dot.addEventListener('click', function () {
          showSlide(i);
        });
        dotsContainer.appendChild(dot);
      });
    }

    // Event listeners
    if (prevBtn) {
      prevBtn.addEventListener('click', function () {
        stopAutoplay();
        prevSlide();
        startAutoplay();
      });
    }
    if (nextBtn) {
      nextBtn.addEventListener('click', function () {
        stopAutoplay();
        nextSlide();
        startAutoplay();
      });
    }

    // Pause on hover
    slider.addEventListener('mouseenter', stopAutoplay);
    slider.addEventListener('mouseleave', startAutoplay);

    // Touch swipe support
    let touchStartX = 0;
    slider.addEventListener('touchstart', function (e) {
      touchStartX = e.touches[0].clientX;
    });
    slider.addEventListener('touchend', function (e) {
      const touchEndX = e.changedTouches[0].clientX;
      const diff = touchStartX - touchEndX;
      if (Math.abs(diff) > 50) {
        if (diff > 0) {
          nextSlide();
        } else {
          prevSlide();
        }
      }
    });

    // Start
    showSlide(0);
    startAutoplay();
  }

  function initSliders() {
    document.querySelectorAll(SLIDER_SELECTOR).forEach(function (slider) {
      initSlider(slider);
    });
  }

  // Initialize on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSliders);
  } else {
    initSliders();
  }
})();