/* =========================================================
   NEXUS FLOW AI - LOGIN PAGE SCRIPT
   Password visibility toggle & field management
   ========================================================= */

document.addEventListener("DOMContentLoaded", () => {
    const passwordInput = document.getElementById("password");
    const togglePasswordIcon = document.getElementById("togglePassword");
    const emailInput = document.getElementById("email");
    const loginForm = document.getElementById("loginForm");

    // Single Eye Icon Password Visibility Toggle
    if (passwordInput && togglePasswordIcon) {
        togglePasswordIcon.addEventListener("click", () => {
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

        togglePasswordIcon.addEventListener("keydown", (e) => {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                togglePasswordIcon.click();
            }
        });
    }

    // Clear inputs on load so fields always open empty (prevents browser autofill)
    if (emailInput) emailInput.value = "";
    if (passwordInput) passwordInput.value = "";
});
