/**
 * Nexus Flow AI - Professional Website Generation Engine
 * Analyzes requirements, selects technology, generates complete projects
 */

// @ts-nocheck

class WebsiteGenerationEngine {
    constructor() {
        this.techStacks = {
            'html': { name: 'HTML/CSS/JavaScript', complexity: 'simple', backend: false },
            'react': { name: 'React', complexity: 'medium', backend: false },
            'flask': { name: 'Flask + HTML', complexity: 'medium', backend: true },
            'django': { name: 'Django + Templates', complexity: 'high', backend: true },
            'node': { name: 'Node.js + EJS', complexity: 'high', backend: true },
            'nextjs': { name: 'Next.js', complexity: 'high', backend: false }
        };
    }

    analyzeRequirements(prompt) {
        const requirements = {
            type: 'website',
            pages: ['home'],
            features: [],
            techStack: 'html',
            backend: false,
            database: false,
            apis: [],
            responsive: true,
            complexity: 'simple'
        };

        const lowerPrompt = prompt.toLowerCase();

        if (lowerPrompt.includes('e-commerce') || lowerPrompt.includes('ecommerce') || 
            lowerPrompt.includes('store') || lowerPrompt.includes('shop') || lowerPrompt.includes('cart')) {
            requirements.type = 'ecommerce';
            requirements.pages = ['home', 'products', 'cart', 'checkout'];
            requirements.features.push('shopping-cart', 'product-catalog', 'checkout');
            requirements.database = true;
        } else if (lowerPrompt.includes('blog') || lowerPrompt.includes('news') || 
                   lowerPrompt.includes('magazine') || lowerPrompt.includes('article')) {
            requirements.type = 'blog';
            requirements.pages = ['home', 'article', 'categories', 'about'];
            requirements.features.push('article-list', 'categories', 'search');
            requirements.database = true;
        } else if (lowerPrompt.includes('dashboard') || lowerPrompt.includes('admin') || 
                   lowerPrompt.includes('analytics') || lowerPrompt.includes('metrics')) {
            requirements.type = 'dashboard';
            requirements.pages = ['dashboard', 'analytics', 'settings', 'reports'];
            requirements.features.push('data-visualization', 'charts', 'filters');
            requirements.backend = true;
            requirements.database = true;
            requirements.techStack = 'react';
        } else if (lowerPrompt.includes('portfolio') || lowerPrompt.includes('resume') || 
                   lowerPrompt.includes('personal') || lowerPrompt.includes('bio')) {
            requirements.type = 'portfolio';
            requirements.pages = ['home', 'projects', 'about', 'contact'];
            requirements.features.push('project-gallery', 'contact-form');
        } else if (lowerPrompt.includes('restaurant') || lowerPrompt.includes('cafe') || 
                   lowerPrompt.includes('food') || lowerPrompt.includes('menu')) {
            requirements.type = 'restaurant';
            requirements.pages = ['home', 'menu', 'reservations', 'about', 'contact'];
            requirements.features.push('reservation-system', 'menu-display', 'contact-form');
        } else if (lowerPrompt.includes('saas') || lowerPrompt.includes('software') || 
                   lowerPrompt.includes('application') || lowerPrompt.includes('platform')) {
            requirements.type = 'saas';
            requirements.pages = ['home', 'features', 'pricing', 'docs', 'contact'];
            requirements.features.push('pricing-tables', 'feature-grid', 'testimonials');
        } else if (lowerPrompt.includes('social') || lowerPrompt.includes('community') || 
                   lowerPrompt.includes('network')) {
            requirements.type = 'social';
            requirements.pages = ['home', 'feed', 'profile', 'messages'];
            requirements.features.push('user-auth', 'posts', 'messaging');
            requirements.backend = true;
            requirements.database = true;
            requirements.techStack = 'node';
        } else if (lowerPrompt.includes('api') || lowerPrompt.includes('backend') || 
                   lowerPrompt.includes('server')) {
            requirements.type = 'api';
            requirements.backend = true;
            requirements.techStack = 'node';
        }

        if (requirements.features.length > 3 || requirements.pages.length > 4) {
            requirements.complexity = 'high';
            if (!requirements.backend) {
                requirements.techStack = 'react';
            }
        } else if (requirements.features.length > 1) {
            requirements.complexity = 'medium';
        }

        if (lowerPrompt.includes('payment') || lowerPrompt.includes('stripe') || 
            lowerPrompt.includes('paypal')) {
            requirements.apis.push('payment');
        }
        if (lowerPrompt.includes('authentication') || lowerPrompt.includes('login') || 
            lowerPrompt.includes('auth')) {
            requirements.apis.push('auth');
        }
        if (lowerPrompt.includes('email') || lowerPrompt.includes('newsletter')) {
            requirements.apis.push('email');
        }
        if (lowerPrompt.includes('map') || lowerPrompt.includes('location')) {
            requirements.apis.push('maps');
        }
        if (lowerPrompt.includes('ai') || lowerPrompt.includes('chatbot') || 
            lowerPrompt.includes('generator')) {
            requirements.apis.push('ai');
        }

        return requirements;
    }

    selectTechStack(requirements) {
        if (requirements.techStack && requirements.techStack !== 'auto') {
            return requirements.techStack;
        }

        if (requirements.backend && requirements.database) {
            if (requirements.type === 'social' || requirements.type === 'api') {
                return 'node';
            }
            return 'flask';
        } else if (requirements.backend) {
            return 'flask';
        } else if (requirements.complexity === 'high') {
            return 'react';
        } else if (requirements.complexity === 'medium') {
            return 'react';
        }

        return 'html';
    }

    generateProjectStructure(requirements, techStack) {
        let structure = {
            files: {},
            folders: [],
            techStack: techStack,
            requirements: requirements
        };

        switch(techStack) {
            case 'html':
                structure = this.generateHTMLStructure(requirements);
                break;
            case 'react':
                structure = this.generateReactStructure(requirements);
                break;
            case 'flask':
                structure = this.generateFlaskStructure(requirements);
                break;
            case 'node':
                structure = this.generateNodeStructure(requirements);
                break;
        }

        return structure;
    }

    generateHTMLStructure(requirements) {
        const files = {};
        
        requirements.pages.forEach(page => {
            files[page + '.html'] = this.generateHTMLPage(page, requirements);
        });

        files['style.css'] = this.generateSharedCSS(requirements);
        files['script.js'] = this.generateSharedJS(requirements);

        return {
            files: files,
            folders: ['assets/images', 'assets/fonts'],
            techStack: 'html',
            requirements: requirements,
            entryPoint: requirements.pages[0] + '.html'
        };
    }

    generateReactStructure(requirements) {
        const files = {};
        
        files['package.json'] = this.generatePackageJSON(requirements);
        files['src/App.jsx'] = this.generateReactApp(requirements);
        
        requirements.pages.forEach(page => {
            const pageName = page.charAt(0).toUpperCase() + page.slice(1);
            files['src/pages/' + pageName + '.jsx'] = this.generateReactPage(page, requirements);
        });

        files['src/index.css'] = this.generateSharedCSS(requirements);
        files['src/App.css'] = this.generateReactAppCSS(requirements);
        files['src/main.jsx'] = this.generateReactEntry();
        files['index.html'] = this.generateReactHTMLTemplate(requirements);

        return {
            files: files,
            folders: ['public', 'src/components', 'src/assets'],
            techStack: 'react',
            requirements: requirements,
            entryPoint: 'src/main.jsx'
        };
    }

    generateFlaskStructure(requirements) {
        const files = {};
        
        files['app.py'] = this.generateFlaskApp(requirements);
        
        requirements.pages.forEach(page => {
            files['templates/' + page + '.html'] = this.generateHTMLPage(page, requirements);
        });
        
        files['templates/base.html'] = this.generateFlaskBaseTemplate(requirements);
        files['static/css/style.css'] = this.generateSharedCSS(requirements);
        files['static/js/main.js'] = this.generateSharedJS(requirements);
        files['requirements.txt'] = 'flask==2.3.0\npymongo==4.5.0\npython-dotenv==1.0.0';

        return {
            files: files,
            folders: ['templates', 'static/css', 'static/js', 'static/images'],
            techStack: 'flask',
            requirements: requirements,
            entryPoint: 'app.py'
        };
    }

    generateNodeStructure(requirements) {
        const files = {};
        
        files['package.json'] = this.generateNodePackageJSON(requirements);
        files['server.js'] = this.generateNodeServer(requirements);
        
        requirements.pages.forEach(page => {
            files['views/' + page + '.ejs'] = this.generateHTMLPage(page, requirements);
        });
        
        files['views/partials/header.ejs'] = this.generateHeaderPartial(requirements);
        files['views/partials/footer.ejs'] = this.generateFooterPartial(requirements);
        files['public/css/style.css'] = this.generateSharedCSS(requirements);
        files['public/js/main.js'] = this.generateSharedJS(requirements);

        return {
            files: files,
            folders: ['views', 'views/partials', 'public/css', 'public/js', 'public/images'],
            techStack: 'node',
            requirements: requirements,
            entryPoint: 'server.js'
        };
    }

    generateHTMLPage(pageName, requirements) {
        const pageContent = {
            home: this.generateHomePage(requirements),
            products: this.generateProductsPage(requirements),
            cart: this.generateCartPage(requirements),
            checkout: this.generateCheckoutPage(requirements),
            about: this.generateAboutPage(requirements),
            contact: this.generateContactPage(requirements)
        };

        return pageContent[pageName] || this.generateDefaultPage(pageName, requirements);
    }

    generateHomePage(req) {
        const pages = req.pages || ['home'];
        const features = req.features || [];
        
        let html = '<!DOCTYPE html>\n<html lang="en">\n<head>\n';
        html += '    <meta charset="UTF-8">\n';
        html += '    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n';
        html += '    <title>Home - ' + req.type + '</title>\n';
        html += '    <link rel="stylesheet" href="style.css">\n';
        html += '</head>\n<body>\n';
        html += '    <header class="navbar">\n';
        html += '        <div class="container">\n';
        html += '            <a href="home.html" class="logo">Brand</a>\n';
        html += '            <nav class="nav-links">\n';
        html += '                <a href="home.html">Home</a>\n';
        
        if (pages.includes('about')) {
            html += '                <a href="about.html">About</a>\n';
        }
        if (pages.includes('products')) {
            html += '                <a href="products.html">Products</a>\n';
        }
        if (pages.includes('contact')) {
            html += '                <a href="contact.html">Contact</a>\n';
        }
        
        html += '            </nav>\n';
        html += '            <button class="mobile-menu-btn" aria-label="Toggle menu">☰</button>\n';
        html += '        </div>\n';
        html += '    </header>\n\n';
        html += '    <main>\n';
        html += '        <section class="hero">\n';
        html += '            <div class="container">\n';
        html += '                <h1>Welcome to Our ' + req.type + ' Platform</h1>\n';
        html += '                <p class="hero-subtitle">Building the future with innovative solutions</p>\n';
        html += '                <div class="hero-buttons">\n';
        
        if (pages.includes('contact')) {
            html += '                    <a href="contact.html" class="btn btn-primary">Get Started</a>\n';
        }
        if (pages.includes('about')) {
            html += '                    <a href="about.html" class="btn btn-secondary">Learn More</a>\n';
        }
        
        html += '                </div>\n';
        html += '            </div>\n';
        html += '        </section>\n';
        
        if (features.includes('feature-grid')) {
            html += '        <section class="features">\n';
            html += '            <div class="container">\n';
            html += '                <h2>Our Features</h2>\n';
            html += '                <div class="feature-grid">\n';
            html += '                    <div class="feature-card">\n';
            html += '                        <div class="feature-icon">🚀</div>\n';
            html += '                        <h3>Fast Performance</h3>\n';
            html += '                        <p>Optimized for speed and efficiency</p>\n';
            html += '                    </div>\n';
            html += '                    <div class="feature-card">\n';
            html += '                        <div class="feature-icon">🔒</div>\n';
            html += '                        <h3>Secure</h3>\n';
            html += '                        <p>Enterprise-grade security</p>\n';
            html += '                    </div>\n';
            html += '                    <div class="feature-card">\n';
            html += '                        <div class="feature-icon">📱</div>\n';
            html += '                        <h3>Responsive</h3>\n';
            html += '                        <p>Works on all devices</p>\n';
            html += '                    </div>\n';
            html += '                </div>\n';
            html += '            </div>\n';
            html += '        </section>\n';
        }
        
        html += '    </main>\n\n';
        html += '    <footer class="footer">\n';
        html += '        <div class="container">\n';
        html += '            <p>&copy; 2026 Brand. All rights reserved.</p>\n';
        html += '        </div>\n';
        html += '    </footer>\n\n';
        html += '    <script src="script.js"></script>\n';
        html += '</body>\n</html>';
        
        return html;
    }

    generateProductsPage(req) {
        return '<!DOCTYPE html>\n<html lang="en">\n<head>\n    <meta charset="UTF-8">\n    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n    <title>Products</title>\n    <link rel="stylesheet" href="style.css">\n</head>\n<body>\n    <header class="navbar">\n        <div class="container">\n            <a href="home.html" class="logo">Brand</a>\n            <nav class="nav-links">\n                <a href="home.html">Home</a>\n                <a href="products.html">Products</a>\n            </nav>\n        </div>\n    </header>\n    <main>\n        <section class="products">\n            <div class="container">\n                <h1>Our Products</h1>\n                <div class="product-grid" id="product-grid"></div>\n            </div>\n        </section>\n    </main>\n    <footer class="footer">\n        <div class="container">\n            <p>&copy; 2026 Brand. All rights reserved.</p>\n        </div>\n    </footer>\n    <script src="script.js"></script>\n</body>\n</html>';
    }

    generateCartPage(req) {
        return '<!DOCTYPE html>\n<html lang="en">\n<head>\n    <meta charset="UTF-8">\n    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n    <title>Shopping Cart</title>\n    <link rel="stylesheet" href="style.css">\n</head>\n<body>\n    <header class="navbar">\n        <div class="container">\n            <a href="home.html" class="logo">Brand</a>\n            <nav class="nav-links">\n                <a href="home.html">Home</a>\n                <a href="cart.html">Cart</a>\n            </nav>\n        </div>\n    </header>\n    <main>\n        <section class="cart">\n            <div class="container">\n                <h1>Shopping Cart</h1>\n                <div id="cart-items">\n                    <p class="empty-cart">Your cart is empty</p>\n                </div>\n            </div>\n        </section>\n    </main>\n    <footer class="footer">\n        <div class="container">\n            <p>&copy; 2026 Brand. All rights reserved.</p>\n        </div>\n    </footer>\n    <script src="script.js"></script>\n</body>\n</html>';
    }

    generateCheckoutPage(req) {
        return '<!DOCTYPE html>\n<html lang="en">\n<head>\n    <meta charset="UTF-8">\n    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n    <title>Checkout</title>\n    <link rel="stylesheet" href="style.css">\n</head>\n<body>\n    <header class="navbar">\n        <div class="container">\n            <a href="home.html" class="logo">Brand</a>\n            <nav class="nav-links">\n                <a href="home.html">Home</a>\n                <a href="cart.html">Cart</a>\n            </nav>\n        </div>\n    </header>\n    <main>\n        <section class="checkout">\n            <div class="container">\n                <h1>Checkout</h1>\n                <form id="checkout-form">\n                    <input type="text" name="name" placeholder="Full Name" required>\n                    <input type="email" name="email" placeholder="Email" required>\n                    <button type="submit" class="btn btn-primary">Place Order</button>\n                </form>\n            </div>\n        </section>\n    </main>\n    <footer class="footer">\n        <div class="container">\n            <p>&copy; 2026 Brand. All rights reserved.</p>\n        </div>\n    </footer>\n    <script src="script.js"></script>\n    <script>\n        document.getElementById("checkout-form").addEventListener("submit", function(e) {\n            e.preventDefault();\n            alert("Order placed successfully!");\n            localStorage.removeItem("cart");\n            window.location.href = "home.html";\n        });\n    </script>\n</body>\n</html>';
    }

    generateContactPage(req) {
        return '<!DOCTYPE html>\n<html lang="en">\n<head>\n    <meta charset="UTF-8">\n    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n    <title>Contact Us</title>\n    <link rel="stylesheet" href="style.css">\n</head>\n<body>\n    <header class="navbar">\n        <div class="container">\n            <a href="home.html" class="logo">Brand</a>\n            <nav class="nav-links">\n                <a href="home.html">Home</a>\n                <a href="contact.html">Contact</a>\n            </nav>\n        </div>\n    </header>\n    <main>\n        <section class="contact">\n            <div class="container">\n                <h1>Contact Us</h1>\n                <form id="contact-form">\n                    <input type="text" name="name" placeholder="Your Name" required>\n                    <input type="email" name="email" placeholder="Your Email" required>\n                    <textarea name="message" placeholder="Your Message" rows="5" required></textarea>\n                    <button type="submit" class="btn btn-primary">Send Message</button>\n                </form>\n            </div>\n        </section>\n    </main>\n    <footer class="footer">\n        <div class="container">\n            <p>&copy; 2026 Brand. All rights reserved.</p>\n        </div>\n    </footer>\n    <script src="script.js"></script>\n    <script>\n        document.getElementById("contact-form").addEventListener("submit", function(e) {\n            e.preventDefault();\n            alert("Thank you for your message!");\n            this.reset();\n        });\n    </script>\n</body>\n</html>';
    }

    generateAboutPage(req) {
        return '<!DOCTYPE html>\n<html lang="en">\n<head>\n    <meta charset="UTF-8">\n    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n    <title>About Us</title>\n    <link rel="stylesheet" href="style.css">\n</head>\n<body>\n    <header class="navbar">\n        <div class="container">\n            <a href="home.html" class="logo">Brand</a>\n            <nav class="nav-links">\n                <a href="home.html">Home</a>\n                <a href="about.html">About</a>\n            </nav>\n        </div>\n    </header>\n    <main>\n        <section class="about">\n            <div class="container">\n                <h1>About Us</h1>\n                <p>We are dedicated to providing exceptional solutions.</p>\n            </div>\n        </section>\n    </main>\n    <footer class="footer">\n        <div class="container">\n            <p>&copy; 2026 Brand. All rights reserved.</p>\n        </div>\n    </footer>\n    <script src="script.js"></script>\n</body>\n</html>';
    }

    generateDefaultPage(pageName, requirements) {
        return '<!DOCTYPE html>\n<html lang="en">\n<head>\n    <meta charset="UTF-8">\n    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n    <title>' + pageName + '</title>\n    <link rel="stylesheet" href="style.css">\n</head>\n<body>\n    <header class="navbar">\n        <div class="container">\n            <a href="home.html" class="logo">Brand</a>\n        </div>\n    </header>\n    <main>\n        <section class="page-header">\n            <div class="container">\n                <h1>' + pageName + '</h1>\n            </div>\n        </section>\n    </main>\n    <footer class="footer">\n        <div class="container">\n            <p>&copy; 2026 Brand. All rights reserved.</p>\n        </div>\n    </footer>\n    <script src="script.js"></script>\n</body>\n</html>';
    }

    generateSharedCSS(requirements) {
        return '/* Professional Website Styles */\n' +
            '* { margin: 0; padding: 0; box-sizing: border-box; }\n' +
            ':root {\n' +
            '    --primary-color: #ff6b00;\n' +
            '    --secondary-color: #ff2d2d;\n' +
            '    --bg-color: #090d16;\n' +
            '    --text-color: #f8fafc;\n' +
            '    --muted-color: #94a3b8;\n' +
            '    --card-bg: rgba(255, 255, 255, 0.03);\n' +
            '    --border-color: rgba(255, 255, 255, 0.08);\n' +
            '}\n' +
            'html { scroll-behavior: smooth; }\n' +
            'body {\n' +
            '    font-family: "Plus Jakarta Sans", "Inter", sans-serif;\n' +
            '    background: var(--bg-color);\n' +
            '    color: var(--text-color);\n' +
            '    line-height: 1.6;\n' +
            '    overflow-x: hidden;\n' +
            '}\n' +
            '.container { max-width: 1240px; margin: 0 auto; padding: 0 1.5rem; }\n' +
            '.navbar {\n' +
            '    position: sticky;\n' +
            '    top: 0;\n' +
            '    z-index: 100;\n' +
            '    background: rgba(9, 13, 22, 0.8);\n' +
            '    backdrop-filter: blur(12px);\n' +
            '    border-bottom: 1px solid var(--border-color);\n' +
            '    padding: 1.25rem 0;\n' +
            '}\n' +
            '.navbar .container { display: flex; justify-content: space-between; align-items: center; }\n' +
            '.logo { font-size: 1.25rem; font-weight: 800; color: var(--text-color); }\n' +
            '.nav-links { display: flex; gap: 2rem; align-items: center; }\n' +
            '.nav-links a { color: var(--muted-color); font-weight: 500; font-size: 0.95rem; }\n' +
            '.nav-links a:hover { color: var(--text-color); }\n' +
            '.mobile-menu-btn { display: none; background: none; border: none; color: var(--text-color); font-size: 1.5rem; cursor: pointer; }\n' +
            '.btn {\n' +
            '    display: inline-flex;\n' +
            '    align-items: center;\n' +
            '    gap: 0.5rem;\n' +
            '    padding: 0.85rem 1.75rem;\n' +
            '    border-radius: 10px;\n' +
            '    font-weight: 600;\n' +
            '    font-size: 1rem;\n' +
            '    border: none;\n' +
            '    cursor: pointer;\n' +
            '    text-decoration: none;\n' +
            '}\n' +
            '.btn-primary {\n' +
            '    background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));\n' +
            '    color: white;\n' +
            '    box-shadow: 0 4px 20px rgba(255, 107, 0, 0.3);\n' +
            '}\n' +
            '.btn-secondary {\n' +
            '    background: rgba(255, 255, 255, 0.05);\n' +
            '    border: 1px solid var(--border-color);\n' +
            '    color: var(--text-color);\n' +
            '}\n' +
            '.hero { padding: 6rem 0 4rem; text-align: center; }\n' +
            '.hero h1 { font-size: clamp(2.2rem, 4vw, 3.5rem); font-weight: 800; margin-bottom: 1.25rem; }\n' +
            '.hero-subtitle { font-size: 1.2rem; color: var(--muted-color); max-width: 620px; margin: 0 auto 2.5rem; }\n' +
            '.hero-buttons { display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap; }\n' +
            '.features { padding: 5rem 0; }\n' +
            '.features h2 { text-align: center; font-size: 2.25rem; margin-bottom: 3rem; }\n' +
            '.feature-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 2rem; }\n' +
            '.feature-card {\n' +
            '    background: var(--card-bg);\n' +
            '    border: 1px solid var(--border-color);\n' +
            '    padding: 2rem;\n' +
            '    border-radius: 16px;\n' +
            '    text-align: center;\n' +
            '}\n' +
            '.feature-icon { font-size: 3rem; margin-bottom: 1rem; }\n' +
            '.footer { padding: 3rem 0; border-top: 1px solid var(--border-color); margin-top: 4rem; text-align: center; color: var(--muted-color); }\n' +
            '@media (max-width: 768px) {\n' +
            '    .nav-links { display: none; }\n' +
            '    .mobile-menu-btn { display: block; }\n' +
            '}';
    }

    generateSharedJS(requirements) {
        let js = 'console.log("Website initialized");\n';
        js += 'document.addEventListener("DOMContentLoaded", function() {\n';
        js += '    const menuBtn = document.querySelector(".mobile-menu-btn");\n';
        js += '    const navLinks = document.querySelector(".nav-links");\n';
        js += '    if (menuBtn && navLinks) {\n';
        js += '        menuBtn.addEventListener("click", function() {\n';
        js += '            navLinks.style.display = navLinks.style.display === "flex" ? "none" : "flex";\n';
        js += '        });\n';
        js += '    }\n';
        js += '});\n';

        if (requirements.type === 'ecommerce') {
            js += '\n// Shopping Cart\n';
            js += 'let cart = JSON.parse(localStorage.getItem("cart")) || [];\n';
            js += 'function addToCart(productId) {\n';
            js += '    const product = { id: productId, name: "Product " + productId, price: 29.99, quantity: 1 };\n';
            js += '    const existingItem = cart.find(item => item.id === productId);\n';
            js += '    if (existingItem) { existingItem.quantity++; } else { cart.push(product); }\n';
            js += '    localStorage.setItem("cart", JSON.stringify(cart));\n';
            js += '    updateCartCount();\n';
            js += '    alert("Added to cart!");\n';
            js += '}\n';
            js += 'function updateCartCount() {\n';
            js += '    const count = cart.reduce((sum, item) => sum + item.quantity, 0);\n';
            js += '    document.querySelectorAll("#cart-count").forEach(el => el.textContent = count);\n';
            js += '}\n';
            js += 'updateCartCount();\n';
        }

        return js;
    }

    generateReactApp(req) {
        return 'import React from "react";\n' +
            'import { useState } from "react";\n' +
            'import "./index.css";\n\n' +
            'export default function App() {\n' +
            '    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);\n\n' +
            '    return (\n' +
            '        <div className="app">\n' +
            '            <header className="navbar">\n' +
            '                <div className="container">\n' +
            '                    <a href="#top" className="logo">' + (req.website_name || 'Brand') + '</a>\n' +
            '                    <nav className={"nav-links " + (mobileMenuOpen ? "mobile-open" : "")}>\n' +
            '                        <a href="#features">Features</a>\n' +
            '                        <a href="#about">About</a>\n' +
            '                        <a href="#contact">Contact</a>\n' +
            '                    </nav>\n' +
            '                    <button className="mobile-menu-btn" onClick={() => setMobileMenuOpen(!mobileMenuOpen)}>☰</button>\n' +
            '                </div>\n' +
            '            </header>\n' +
            '            <main>{/* Page content here */}</main>\n' +
            '        </div>\n' +
            '    );\n' +
            '}';
    }

    generateReactPage(page, req) {
        return 'export default function ' + page.charAt(0).toUpperCase() + page.slice(1) + '() {\n';
    }

    generateReactAppCSS(req) {
        return this.generateSharedCSS(req);
    }

    generateReactEntry() {
        return 'import React from "react";\n' +
            'import { createRoot } from "react-dom/client";\n' +
            'import App from "./App.jsx";\n' +
            'import "./index.css";\n\n' +
            'const root = createRoot(document.getElementById("root"));\n' +
            'root.render(\n' +
            '    <React.StrictMode>\n' +
            '        <App />\n' +
            '    </React.StrictMode>\n' +
            ');';
    }

    generateReactHTMLTemplate(req) {
        return '<!DOCTYPE html>\n<html lang="en">\n<head>\n' +
            '    <meta charset="UTF-8">\n' +
            '    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n' +
            '    <title>' + (req.website_name || 'My App') + '</title>\n' +
            '</head>\n<body>\n' +
            '    <div id="root"></div>\n' +
            '    <script type="module" src="/src/main.jsx"></script>\n' +
            '</body>\n</html>';
    }

    generatePackageJSON(req) {
        return JSON.stringify({
            name: (req.website_name || 'my-app').toLowerCase().replace(/[^a-z0-9]+/g, '-'),
            version: "1.0.0",
            private: true,
            type: "module",
            scripts: {
                dev: "vite",
                build: "vite build",
                preview: "vite preview"
            },
            dependencies: {
                "react": "^18.3.1",
                "react-dom": "^18.3.1"
            },
            devDependencies: {
                "@vitejs/plugin-react": "^4.3.4",
                "vite": "^5.4.11"
            }
        }, null, 2) + "\n";
    }

    generateFlaskApp(req) {
        return 'from flask import Flask, render_template\n' +
            'app = Flask(__name__)\n\n' +
            '@app.route("/")\n' +
            'def home():\n' +
            '    return render_template("index.html", title="' + (req.website_name || 'My Website') + '")\n\n' +
            'if __name__ == "__main__":\n' +
            '    app.run(debug=True)';
    }

    generateFlaskBaseTemplate(req) {
        return '<!DOCTYPE html>\n<html lang="en">\n<head>\n' +
            '    <meta charset="UTF-8">\n' +
            '    <title>{% block title %}' + (req.website_name || 'My Website') + '{% endblock %}</title>\n' +
            '    <link rel="stylesheet" href="{{ url_for("static", filename="css/style.css") }}">\n' +
            '</head>\n<body>\n' +
            '    {% block content %}{% endblock %}\n' +
            '    <script src="{{ url_for("static", filename="js/main.js") }}"></script>\n' +
            '</body>\n</html>';
    }

    generateNodePackageJSON(req) {
        return JSON.stringify({
            name: (req.website_name || 'my-app').toLowerCase().replace(/[^a-z0-9]+/g, '-'),
            version: "1.0.0",
            main: "server.js",
            scripts: {
                start: "node server.js",
                dev: "nodemon server.js"
            },
            dependencies: {
                "express": "^4.19.2",
                "ejs": "^3.1.10"
            }
        }, null, 2) + "\n";
    }

    generateNodeServer(req) {
        return 'const express = require("express");\n' +
            'const path = require("path");\n' +
            'const app = express();\n\n' +
            'app.set("view engine", "ejs");\n' +
            'app.use(express.static("public"));\n\n' +
            'app.get("/", (req, res) => {\n' +
            '    res.render("index", { title: "' + (req.website_name || 'My Website') + '" });\n' +
            '});\n\n' +
            'app.listen(3000, () => {\n' +
            '    console.log("Server running on http://localhost:3000");\n' +
            '});';
    }

    generateHeaderPartial(req) {
        return '<!DOCTYPE html>\n<html lang="en">\n<head>\n' +
            '    <title><%= title || "' + (req.website_name || 'My Website') + '" %></title>\n' +
            '    <link rel="stylesheet" href="/css/style.css">\n' +
            '</head>\n<body>';
    }

    generateFooterPartial(req) {
        return '    <script src="/js/main.js"></script>\n</body>\n</html>';
    }

    validateProject(project) {
        const errors = [];
        const warnings = [];

        if (!project.entryPoint) {
            errors.push('Missing entry point file');
        }

        Object.entries(project.files).forEach(([filename, content]) => {
            if (filename.endsWith('.html')) {
                if (!content.includes('<!DOCTYPE') && !content.includes('<html')) {
                    warnings.push(filename + ': Missing DOCTYPE or html tag');
                }
                
                const linkMatches = content.match(/href="([^"]+)"/g) || [];
                linkMatches.forEach(match => {
                    const link = match.match(/href="([^"]+)"/)[1];
                    if (link.startsWith('http')) return;
                    if (link.startsWith('#')) return;
                    if (!project.files[link] && !link.includes('.html')) {
                        warnings.push(filename + ': Possibly broken link - ' + link);
                    }
                });

                const openTags = (content.match(/<div/g) || []).length;
                const closeTags = (content.match(/<\/div>/g) || []).length;
                if (openTags !== closeTags) {
                    warnings.push(filename + ': Unbalanced div tags (' + openTags + ' open, ' + closeTags + ' close)');
                }
            }

            if (filename.endsWith('.css')) {
                const openBraces = (content.match(/{/g) || []).length;
                const closeBraces = (content.match(/}/g) || []).length;
                if (openBraces !== closeBraces) {
                    errors.push(filename + ': Unbalanced CSS braces');
                }
            }
        });

        return {
            valid: errors.length === 0,
            errors: errors,
            warnings: warnings
        };
    }

    autoFixIssues(project) {
        const fixed = JSON.parse(JSON.stringify(project));
        
        Object.entries(fixed.files).forEach(([filename, content]) => {
            if (filename.endsWith('.html')) {
                let fixedContent = content;
                
                if (!fixedContent.includes('<!DOCTYPE')) {
                    fixedContent = '<!DOCTYPE html>\n' + fixedContent;
                }
                
                fixedContent = this.balanceHTMLTags(fixedContent);
                fixed.files[filename] = fixedContent;
            }
            
            if (filename.endsWith('.css')) {
                let fixedContent = content;
                const openBraces = (fixedContent.match(/{/g) || []).length;
                const closeBraces = (fixedContent.match(/}/g) || []).length;
                
                if (openBraces > closeBraces) {
                    fixedContent += '\n' + '}'.repeat(openBraces - closeBraces);
                }
                
                fixed.files[filename] = fixedContent;
            }
        });
        
        return fixed;
    }

    balanceHTMLTags(html) {
        const voidTags = ['br', 'hr', 'img', 'input', 'meta', 'link'];
        const stack = [];
        const tagRegex = /<\/?([a-zA-Z0-9-]+)[^>]*>/g;
        let match;
        
        while ((match = tagRegex.exec(html)) !== null) {
            const fullTag = match[0];
            const tagName = match[1].toLowerCase();
            
            if (voidTags.includes(tagName) || fullTag.startsWith('</')) {
                if (fullTag.startsWith('</') && stack[stack.length - 1] === tagName) {
                    stack.pop();
                }
                continue;
            }
            
            if (!fullTag.endsWith('/>')) {
                stack.push(tagName);
            }
        }
        
        while (stack.length > 0) {
            html += '</' + stack.pop() + '>';
        }
        
        return html;
    }
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = WebsiteGenerationEngine;
}