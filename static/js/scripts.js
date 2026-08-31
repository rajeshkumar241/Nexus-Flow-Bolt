/* =========================================================
   NEXUS FLOW AI - LANDING PAGE & PLATFORM INTERACTIVE SCRIPTS
   ========================================================= */

// Mobile Navigation Toggle
const menuIcon = document.querySelector("#menu-icon");
const navbar = document.querySelector("nav");

if (menuIcon && navbar) {
    menuIcon.onclick = () => {
        menuIcon.classList.toggle("fa-xmark");
        navbar.classList.toggle("active");
    };
}

// Active Nav Link on Scroll & Sticky Header
const sections = document.querySelectorAll("section");
const navLinks = document.querySelectorAll("header nav a");

window.onscroll = () => {
    let top = window.scrollY;

    sections.forEach(sec => {
        let offset = sec.offsetTop - 150;
        let height = sec.offsetHeight;
        let id = sec.getAttribute("id");

        if (top >= offset && top < offset + height) {
            navLinks.forEach(link => {
                link.classList.remove("active");
            });
            const activeLink = document.querySelector(`header nav a[href="#${id}"]`);
            if (activeLink) {
                activeLink.classList.add("active");
            }
        }
    });

    const header = document.querySelector("header");
    if (header) {
        if (top > 80) {
            header.classList.add("sticky");
        } else {
            header.classList.remove("sticky");
        }
    }
};

// Smooth Scrolling for Nav Links & Back-To-Top
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener("click", function (e) {
        const targetId = this.getAttribute("href");
        if (targetId === "#" || !targetId) return;
        const target = document.querySelector(targetId);

        if (target) {
            e.preventDefault();
            if (navbar && navbar.classList.contains("active")) {
                navbar.classList.remove("active");
                if (menuIcon) menuIcon.classList.remove("fa-xmark");
            }
            target.scrollIntoView({
                behavior: "smooth"
            });
        }
    });
});

// Counter Animation for About Section
let animatedCounters = false;
function animateCounters() {
    const counters = document.querySelectorAll('.counter-number');
    counters.forEach(counter => {
        const target = parseInt(counter.getAttribute('data-target'), 10);
        let current = 0;
        const duration = 1800; // ms
        const stepTime = 25;
        const steps = duration / stepTime;
        const increment = Math.ceil(target / steps);

        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                current = target;
                clearInterval(timer);
            }
            counter.textContent = current.toLocaleString() + "+";
        }, stepTime);
    });
}

// Intersection Observer for Reveal Animations & Stats Trigger
const observerOptions = {
    threshold: 0.15
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add("show");

            // Trigger counter animation when about section comes into view
            if (entry.target.classList.contains('about-section') && !animatedCounters) {
                animatedCounters = true;
                animateCounters();
            }
        }
    });
}, observerOptions);

document.querySelectorAll(".reveal-on-scroll, .hidden").forEach(el => {
    observer.observe(el);
});

// Password Toggle Handling (Single Eye Icon)
const passwordInput = document.getElementById("password");
const togglePasswordIcon = document.getElementById("togglePassword");

if (passwordInput && togglePasswordIcon) {
    togglePasswordIcon.addEventListener("click", function () {
        const isPassword = passwordInput.getAttribute("type") === "password";
        if (isPassword) {
            passwordInput.setAttribute("type", "text");
            togglePasswordIcon.classList.remove("fa-eye");
            togglePasswordIcon.classList.add("fa-eye-slash");
            togglePasswordIcon.setAttribute("title", "Hide password");
        } else {
            passwordInput.setAttribute("type", "password");
            togglePasswordIcon.classList.remove("fa-eye-slash");
            togglePasswordIcon.classList.add("fa-eye");
            togglePasswordIcon.setAttribute("title", "Show password");
        }
    });

    togglePasswordIcon.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            togglePasswordIcon.click();
        }
    });
}

// Generate Button Fallback
const genBtn = document.getElementById("generateBtn");
if (genBtn) {
    genBtn.addEventListener("click", async () => {
        const promptEl = document.getElementById("prompt");
        if (!promptEl) return;
        const prompt = promptEl.value;

        const formData = new FormData();
        formData.append("prompt", prompt);

        try {
            const response = await fetch("/generate", {
                method: "POST",
                body: formData
            });
            const data = await response.json();
            const resultEl = document.getElementById("result");
            if (resultEl) resultEl.innerHTML = data.result;
        } catch (err) {
            console.error(err);
        }
    });
}