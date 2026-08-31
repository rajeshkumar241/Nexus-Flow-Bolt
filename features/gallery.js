/**
 * Nexus Flow - Image Gallery Feature Module
 * Opens images in a larger view with next/previous navigation.
 * 
 * Required HTML:
 *   <div class="gallery-grid">
 *     <div class="gallery-item" data-image="path/to/image.jpg" data-caption="Caption">
 *       <img src="path/to/image.jpg" alt="...">
 *     </div>
 *   </div>
 * 
 * The lightbox overlay is auto-created by this module.
 */
(function () {
  'use strict';

  const GALLERY_ITEM_SELECTOR = '.gallery-item, [data-gallery-item]';
  const LIGHTBOX_ID = 'nexusLightbox';

  let currentIndex = 0;
  let galleryItems = [];

  function createLightbox() {
    let lightbox = document.getElementById(LIGHTBOX_ID);
    if (lightbox) return lightbox;

    lightbox = document.createElement('div');
    lightbox.id = LIGHTBOX_ID;
    lightbox.className = 'lightbox';
    lightbox.setAttribute('aria-hidden', 'true');
    lightbox.innerHTML =
      '<div class="lightbox-content">' +
      '<button class="lightbox-close" aria-label="Close"><i class="fa-solid fa-xmark"></i></button>' +
      '<button class="lightbox-prev" aria-label="Previous"><i class="fa-solid fa-chevron-left"></i></button>' +
      '<div class="lightbox-image-container"><img class="lightbox-image" src="" alt=""></div>' +
      '<button class="lightbox-next" aria-label="Next"><i class="fa-solid fa-chevron-right"></i></button>' +
      '<div class="lightbox-caption"></div>' +
      '<div class="lightbox-counter"></div>' +
      '</div>';
    document.body.appendChild(lightbox);
    return lightbox;
  }

  function getGalleryItems() {
    const items = [];
    document.querySelectorAll(GALLERY_ITEM_SELECTOR).forEach(function (item) {
      const img = item.querySelector('img');
      const imageSrc = item.getAttribute('data-image') || (img ? img.getAttribute('src') : '');
      const caption = item.getAttribute('data-caption') || (img ? img.getAttribute('alt') : '');
      if (imageSrc) {
        items.push({ src: imageSrc, caption: caption });
      }
    });
    return items;
  }

  function openLightbox(index) {
    galleryItems = getGalleryItems();
    if (galleryItems.length === 0) return;

    currentIndex = index;
    const lightbox = createLightbox();
    const image = lightbox.querySelector('.lightbox-image');
    const caption = lightbox.querySelector('.lightbox-caption');
    const counter = lightbox.querySelector('.lightbox-counter');

    image.src = galleryItems[currentIndex].src;
    image.alt = galleryItems[currentIndex].caption || '';
    caption.textContent = galleryItems[currentIndex].caption || '';
    counter.textContent = (currentIndex + 1) + ' / ' + galleryItems.length;

    lightbox.classList.add('open');
    lightbox.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
  }

  function closeLightbox() {
    const lightbox = document.getElementById(LIGHTBOX_ID);
    if (lightbox) {
      lightbox.classList.remove('open');
      lightbox.setAttribute('aria-hidden', 'true');
      document.body.style.overflow = '';
    }
  }

  function navigate(direction) {
    if (galleryItems.length === 0) return;
    currentIndex = (currentIndex + direction + galleryItems.length) % galleryItems.length;
    const lightbox = document.getElementById(LIGHTBOX_ID);
    if (!lightbox) return;

    const image = lightbox.querySelector('.lightbox-image');
    const caption = lightbox.querySelector('.lightbox-caption');
    const counter = lightbox.querySelector('.lightbox-counter');

    image.src = galleryItems[currentIndex].src;
    image.alt = galleryItems[currentIndex].caption || '';
    caption.textContent = galleryItems[currentIndex].caption || '';
    counter.textContent = (currentIndex + 1) + ' / ' + galleryItems.length;
  }

  function initGallery() {
    createLightbox();

    // Open lightbox on gallery item click
    document.querySelectorAll(GALLERY_ITEM_SELECTOR).forEach(function (item, index) {
      item.addEventListener('click', function () {
        openLightbox(index);
      });
    });

    const lightbox = document.getElementById(LIGHTBOX_ID);
    if (!lightbox) return;

    // Close button
    const closeBtn = lightbox.querySelector('.lightbox-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', closeLightbox);
    }

    // Prev/Next buttons
    const prevBtn = lightbox.querySelector('.lightbox-prev');
    const nextBtn = lightbox.querySelector('.lightbox-next');
    if (prevBtn) {
      prevBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        navigate(-1);
      });
    }
    if (nextBtn) {
      nextBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        navigate(1);
      });
    }

    // Close when clicking outside the content
    lightbox.addEventListener('click', function (e) {
      if (e.target === lightbox || e.target.classList.contains('lightbox-content')) {
        closeLightbox();
      }
    });

    // Keyboard navigation
    document.addEventListener('keydown', function (e) {
      if (!lightbox.classList.contains('open')) return;
      if (e.key === 'Escape') {
        closeLightbox();
      } else if (e.key === 'ArrowLeft') {
        navigate(-1);
      } else if (e.key === 'ArrowRight') {
        navigate(1);
      }
    });
  }

  // Initialize on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initGallery);
  } else {
    initGallery();
  }
})();