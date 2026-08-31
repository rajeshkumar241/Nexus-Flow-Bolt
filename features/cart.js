/**
 * Nexus Flow - Shopping Cart Feature Module
 * Add products, remove products, increase/decrease quantity, calculate total,
 * display cart item count, and persist cart using localStorage.
 * 
 * Required HTML:
 *   <button class="add-to-cart" data-id="1" data-name="Pizza" data-price="12.99">Add to Cart</button>
 *   <span id="cartCount">0</span>
 *   <div id="cartItems"></div>
 *   <div id="cartTotal">$0.00</div>
 * 
 * The cart drawer/panel should have id="cartDrawer" or class="cart-panel".
 * Close button should have class="cart-close" or data-close-cart.
 */
(function () {
  'use strict';

  const STORAGE_KEY = 'nexus-cart';
  const CART_COUNT_ID = 'cartCount';
  const CART_ITEMS_ID = 'cartItems';
  const CART_TOTAL_ID = 'cartTotal';
  const CART_DRAWER_SELECTOR = '#cartDrawer, .cart-panel, .cart-drawer';
  const CART_TOGGLE_SELECTOR = '#cartToggle, .cart-toggle, .cart-btn';
  const CART_CLOSE_SELECTOR = '.cart-close, [data-close-cart]';

  let cart = [];

  function loadCart() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      cart = stored ? JSON.parse(stored) : [];
      if (!Array.isArray(cart)) cart = [];
    } catch (e) {
      cart = [];
    }
  }

  function saveCart() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(cart));
    } catch (e) {
      // localStorage unavailable
    }
  }

  function getCartCount() {
    return cart.reduce(function (sum, item) {
      return sum + (item.quantity || 1);
    }, 0);
  }

  function getCartTotal() {
    return cart.reduce(function (sum, item) {
      return sum + (parseFloat(item.price) || 0) * (item.quantity || 1);
    }, 0);
  }

  function formatPrice(amount) {
    return '$' + amount.toFixed(2);
  }

  function updateCartUI() {
    // Update cart count
    const countEl = document.getElementById(CART_COUNT_ID);
    if (countEl) {
      countEl.textContent = getCartCount();
    }

    // Update cart items list
    const itemsEl = document.getElementById(CART_ITEMS_ID);
    if (itemsEl) {
      if (cart.length === 0) {
        itemsEl.innerHTML = '<p class="cart-empty">Your cart is empty</p>';
      } else {
        itemsEl.innerHTML = cart.map(function (item, index) {
          const price = parseFloat(item.price) || 0;
          const qty = item.quantity || 1;
          return '<div class="cart-item" data-index="' + index + '">' +
            '<div class="cart-item-info">' +
            '<span class="cart-item-name">' + (item.name || 'Item') + '</span>' +
            '<span class="cart-item-price">' + formatPrice(price * qty) + '</span>' +
            '</div>' +
            '<div class="cart-item-controls">' +
            '<button class="cart-qty-btn" data-action="decrease" data-index="' + index + '">-</button>' +
            '<span class="cart-qty">' + qty + '</span>' +
            '<button class="cart-qty-btn" data-action="increase" data-index="' + index + '">+</button>' +
            '<button class="cart-remove-btn" data-action="remove" data-index="' + index + '" aria-label="Remove">' +
            '<i class="fa-solid fa-trash"></i></button>' +
            '</div>' +
            '</div>';
        }).join('');
      }
    }

    // Update cart total
    const totalEl = document.getElementById(CART_TOTAL_ID);
    if (totalEl) {
      totalEl.textContent = formatPrice(getCartTotal());
    }

    saveCart();
  }

  function addToCart(id, name, price) {
    const existing = cart.find(function (item) {
      return String(item.id) === String(id);
    });

    if (existing) {
      existing.quantity = (existing.quantity || 1) + 1;
    } else {
      cart.push({
        id: id,
        name: name,
        price: parseFloat(price) || 0,
        quantity: 1
      });
    }

    updateCartUI();
  }

  function removeFromCart(index) {
    if (index >= 0 && index < cart.length) {
      cart.splice(index, 1);
      updateCartUI();
    }
  }

  function changeQuantity(index, delta) {
    if (index >= 0 && index < cart.length) {
      const item = cart[index];
      item.quantity = (item.quantity || 1) + delta;
      if (item.quantity <= 0) {
        cart.splice(index, 1);
      }
      updateCartUI();
    }
  }

  function openCart() {
    const drawer = document.querySelector(CART_DRAWER_SELECTOR);
    if (drawer) {
      drawer.classList.add('open');
      drawer.setAttribute('aria-hidden', 'false');
    }
  }

  function closeCart() {
    const drawer = document.querySelector(CART_DRAWER_SELECTOR);
    if (drawer) {
      drawer.classList.remove('open');
      drawer.setAttribute('aria-hidden', 'true');
    }
  }

  function initCart() {
    loadCart();
    updateCartUI();

    // Add to cart buttons
    document.querySelectorAll('.add-to-cart').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        const id = btn.getAttribute('data-id') || btn.getAttribute('data-product-id');
        const name = btn.getAttribute('data-name') || btn.getAttribute('data-product-name');
        const price = btn.getAttribute('data-price') || btn.getAttribute('data-product-price');
        if (id && name && price) {
          addToCart(id, name, price);
          // Show feedback
          const originalText = btn.textContent;
          btn.textContent = 'Added!';
          setTimeout(function () {
            btn.textContent = originalText;
          }, 1200);
        }
      });
    });

    // Cart toggle button
    document.querySelectorAll(CART_TOGGLE_SELECTOR).forEach(function (toggle) {
      toggle.addEventListener('click', function (e) {
        e.preventDefault();
        const drawer = document.querySelector(CART_DRAWER_SELECTOR);
        if (drawer && drawer.classList.contains('open')) {
          closeCart();
        } else {
          openCart();
        }
      });
    });

    // Cart close buttons
    document.querySelectorAll(CART_CLOSE_SELECTOR).forEach(function (closeBtn) {
      closeBtn.addEventListener('click', function () {
        closeCart();
      });
    });

    // Cart item controls (event delegation)
    const itemsEl = document.getElementById(CART_ITEMS_ID);
    if (itemsEl) {
      itemsEl.addEventListener('click', function (e) {
        const btn = e.target.closest('.cart-qty-btn, .cart-remove-btn');
        if (!btn) return;
        const index = parseInt(btn.getAttribute('data-index'), 10);
        const action = btn.getAttribute('data-action');
        if (action === 'increase') {
          changeQuantity(index, 1);
        } else if (action === 'decrease') {
          changeQuantity(index, -1);
        } else if (action === 'remove') {
          removeFromCart(index);
        }
      });
    }

    // Close cart when clicking outside
    document.addEventListener('click', function (e) {
      const drawer = document.querySelector(CART_DRAWER_SELECTOR);
      if (!drawer || !drawer.classList.contains('open')) return;
      if (!drawer.contains(e.target) && !e.target.closest(CART_TOGGLE_SELECTOR)) {
        closeCart();
      }
    });
  }

  // Initialize on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initCart);
  } else {
    initCart();
  }
})();