/**
 * Nexus Flow - Filter Feature Module
 * Filters cards/items by category.
 * 
 * Required HTML:
 *   <div class="filter-buttons">
 *     <button class="filter-btn active" data-filter="all">All</button>
 *     <button class="filter-btn" data-filter="starters">Starters</button>
 *     <button class="filter-btn" data-filter="mains">Mains</button>
 *   </div>
 * 
 * Items to filter must have a data-category attribute:
 *   <div class="menu-item" data-category="starters">...</div>
 * 
 * Also supports <select> elements with class 'filter-select'.
 */
(function () {
  'use strict';

  const FILTER_BTN_SELECTOR = '.filter-btn';
  const FILTER_SELECT_SELECTOR = '.filter-select';
  const ITEM_SELECTOR = '.searchable-item, .menu-item, .card, .product-card, .gallery-item, .food-card, .item-card';

  function getFilterableItems() {
    const containers = document.querySelectorAll('.filter-container, .search-container');
    if (containers.length > 0) {
      const items = [];
      containers.forEach(function (container) {
        container.querySelectorAll(ITEM_SELECTOR).forEach(function (item) {
          items.push(item);
        });
      });
      return items;
    }
    return Array.from(document.querySelectorAll(ITEM_SELECTOR));
  }

  function applyFilter(filterValue) {
    const items = getFilterableItems();
    const normalizedFilter = filterValue.toLowerCase().trim();

    items.forEach(function (item) {
      const category = (item.getAttribute('data-category') || '').toLowerCase();
      const matches = normalizedFilter === 'all' || !normalizedFilter || category === normalizedFilter;
      item.style.display = matches ? '' : 'none';
    });

    // Update active button state
    document.querySelectorAll(FILTER_BTN_SELECTOR).forEach(function (btn) {
      const btnFilter = (btn.getAttribute('data-filter') || '').toLowerCase();
      btn.classList.toggle('active', btnFilter === normalizedFilter);
    });
  }

  function initFilter() {
    // Filter buttons
    document.querySelectorAll(FILTER_BTN_SELECTOR).forEach(function (btn) {
      btn.addEventListener('click', function () {
        const filterValue = btn.getAttribute('data-filter') || 'all';
        applyFilter(filterValue);
      });
    });

    // Filter selects
    document.querySelectorAll(FILTER_SELECT_SELECTOR).forEach(function (select) {
      select.addEventListener('change', function () {
        applyFilter(select.value);
      });
    });
  }

  // Initialize on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initFilter);
  } else {
    initFilter();
  }
})();