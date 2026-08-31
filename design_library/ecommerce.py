"""Nexus Flow AI - Design Pattern Library: E-commerce Patterns

Contains design architecture patterns for:
1. Product Listing
2. Product Detail
3. Checkout
"""

from typing import Dict, Any

ECOMMERCE_PATTERNS: Dict[str, Dict[str, Any]] = {
    "product_listing": {
        "id": "ecom_product_listing",
        "name": "E-commerce Product Catalog & Listing",
        "category": "ecommerce",
        "description": "Multi-column product catalog with faceted category filters, sort controls, dynamic badge pills, and quick add-to-cart drawers.",
        "layout": {
            "type": "catalog_with_sidebar",
            "sidebar_width": "280px",
            "product_grid": "repeat(auto-fill, minmax(260px, 1fr))",
        },
        "sections": [
            {"name": "E-commerce Header", "type": "navbar", "components": ["Store Logo", "Search Bar with autocomplete", "Category Dropdown", "Wishlist counter", "Cart Icon with live badge indicator"]},
            {"name": "Promo / Category Hero Banner", "type": "banner", "components": ["Seasonal collection headline", "Discount badge (e.g. Up to 40% Off)", "Shop Now anchor CTA"]},
            {"name": "Filter & Sort Controls Bar", "type": "controls", "components": ["Category tags / chips", "Price range slider", "Sort dropdown (Popular, Price Low-High, Rating)", "Grid vs List view toggle"]},
            {"name": "Product Grid Showcase", "type": "product_grid", "components": ["Product Cards with image hover zoom, price tag, discount strikethrough, star rating, color swatches, Quick View button, and Add-to-Cart button"]},
            {"name": "Customer Reviews Carousel", "type": "reviews", "components": ["Verified buyer review cards with photo uploads and star scores"]},
            {"name": "E-commerce Footer", "type": "footer", "components": ["Customer Care links", "Track Order form", "Accepted payment method icons (Visa, Mastercard, Apple Pay, Stripe)", "Shipping guarantee badge"]},
        ],
        "design_hints": {
            "card_hover": "Subtle image scale (transform: scale(1.05)) and immediate Quick Add CTA reveal",
            "badge_colors": "Sale badge in Rose/Amber, Best Seller in Emerald",
        }
    },
    "product_detail": {
        "id": "ecom_product_detail",
        "name": "E-commerce Product Detail Experience",
        "category": "ecommerce",
        "description": "Comprehensive product page with multi-angle gallery thumbnails, dynamic variant selector, sticky buy box, and detailed specs tabs.",
        "layout": {
            "type": "2_column_detail",
            "gallery_col": "55%",
            "info_col": "45%",
        },
        "sections": [
            {"name": "Navigation Bar", "type": "navbar", "components": ["Breadcrumb navigation (Home > Apparel > Premium Jacket)", "Cart drawer trigger"]},
            {"name": "Main Product Viewport", "type": "product_hero", "components": ["Multi-angle thumbnail strip", "Main high-res image zoom view", "Product Title with rating stars & review count", "Pricing display with tax note", "Color swatch picker", "Size selector with Size Guide modal link", "Quantity stepper", "Primary Add to Cart & Buy Now CTA buttons", "Stock availability badge (e.g. In Stock, Ships in 24h)"]},
            {"name": "Value Prop Icons Bar", "type": "perks_bar", "components": ["Free Worldwide Shipping icon", "30-Day Money Back Guarantee", "Eco-friendly Materials", "Secure SSL Checkout"]},
            {"name": "Product Specifications Tabs", "type": "specs_tabs", "components": ["Overview tab", "Technical specs table", "Care instructions", "Shipping & returns policy"]},
            {"name": "Frequently Bought Together", "type": "cross_sell", "components": ["Bundle card with checkboxes and 1-click Add Bundle to Cart"]},
            {"name": "Customer Reviews & Q&A", "type": "reviews_breakdown", "components": ["Rating breakdown bar chart", "Filterable review list with search"]},
        ],
        "design_hints": {
            "sticky_buy_box": "Sticky mobile bottom bar with price and Instant Checkout button",
            "accent": "High-contrast CTA button with active ripple micro-interaction",
        }
    },
    "checkout": {
        "id": "ecom_checkout",
        "name": "Frictionless Checkout Flow",
        "category": "ecommerce",
        "description": "Streamlined, high-trust multi-step checkout flow optimized for zero cart abandonment.",
        "layout": {
            "type": "checkout_split",
            "forms_col": "60%",
            "summary_col": "40%",
        },
        "sections": [
            {"name": "Minimal Trust Header", "type": "checkout_header", "components": ["Secure Checkout Lock Icon", "Brand Logo", "Back to Cart link", "Help / Support chat link"]},
            {"name": "Checkout Stepper", "type": "stepper", "components": ["Step 1: Shipping Address (Active)", "Step 2: Shipping Method", "Step 3: Payment"]},
            {"name": "Express Checkout Row", "type": "express_pay", "components": ["Apple Pay button", "Google Pay button", "Shop Pay button", "Or continue below divider"]},
            {"name": "Customer & Shipping Form", "type": "shipping_form", "components": ["Email contact", "Full name", "Address autocomplete", "Apartment / Suite", "City, State, Zip", "Phone for delivery updates"]},
            {"name": "Payment Method Selector", "type": "payment_form", "components": ["Credit Card (Card number, Expiry, CVC with brand icons)", "PayPal toggle", "Cash on delivery option"]},
            {"name": "Order Summary Card", "type": "order_summary", "components": ["Product items with quantities & thumbnail preview", "Promo code input with Apply button", "Subtotal, Estimated Shipping, Tax, and Final Total calculation", "Complete Order CTA Button", "Encrypted 256-bit SSL trust seal"]},
        ],
        "design_hints": {
            "trust": "Clear security badges, encrypted data guarantee, transparent refund policy",
            "clarity": "Disabled state until required fields are valid, inline green checkmarks for completed fields",
        }
    }
}
