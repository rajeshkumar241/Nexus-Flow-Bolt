/**
 * Nexus Flow - Search Feature Module
 * Searches generated cards/items dynamically.
 * Hides non-matching items and shows a "No results found" message.
 * 
 * Required HTML:
 *   <input type="search" id="searchInput" placeholder="Search...">
 *   <div id="searchNoResults" class="no-results" style="display:none;">No results found</div>
 * 
 * Items to search must have class 'searchable-item' or be inside a container
 * with class 'search-container'. The search matches text content.
 */
(function () {
  'use strict';

  const SEARCH_INPUT_ID = 'searchInput';
  const NO_RESULTS_ID = 'searchNoResults';
  const ITEM_SELECTOR = '.searchable-item, .menu-item, .card, .product-card, .gallery-item, .food-card, .item-card';

  function getSearchableItems() {
    // Prefer items inside a search container, otherwise use global selector
    const containers = document.querySelectorAll('.search-container');
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

  function getNoResultsElement() {
    return document.getElementById(NO_RESULTS_ID);
  }

  function performSearch(query) {
    const items = getSearchableItems();
    const noResults = getNoResultsElement();
    const normalizedQuery = query.toLowerCase().trim();
    let visibleCount = 0;

    items.forEach(function (item) {
      const text = (item.textContent || '').toLowerCase();
      const dataSearch = (item.getAttribute('data-search') || '').toLowerCase();
      const matches = !normalizedQuery || text.includes(normalizedQuery) || dataSearch.includes(normalizedQuery);
      item.style.display = matches ? '' : 'none';
      if (matches) visibleCount++;
    });

    // Show/hide no results message
    if (noResults) {
      noResults.style.display = visibleCount === 0 ? 'block' : 'none';
    }
  }

  function initSearch() {
    const input = document.getElementById(SEARCH_INPUT_ID);
    if (!input) return;

    input.addEventListener('input', function () {
      performSearch(input.value);
    });

    // Also support a search form submit
    const form = input.closest('form');
    if (form) {
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        performSearch(input.value);
      });
    }
  }

  // Initialize on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSearch);
  } else {
    initSearch();
  }
})();