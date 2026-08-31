/* =========================================================
   NEXUS FLOW AI - PROFILE PAGE JAVASCRIPT
   ========================================================= */

function toggleMenu() {
    const popup = document.getElementById("uploadPopup");
    if (!popup) return;

    if (popup.style.display === "block") {
        popup.style.display = "none";
    } else {
        popup.style.display = "block";
    }
}

function closeMenu() {
    const popup = document.getElementById("uploadPopup");
    if (popup) {
        popup.style.display = "none";
    }
}

function uploadPhoto() {
    closeMenu();
    const input = document.getElementById("profileInput");
    if (input) {
        input.click();
    }
}

const ALLOWED_PROFILE_TYPES = ["jpg", "jpeg", "png", "webp"];

// Called when the user picks a file: preview it instantly, then
// upload to /profile/upload-image and reload the image from the saved path.
function onProfileFileSelected(event) {
    const input = event.target;
    if (!input.files || input.files.length === 0) return;

    const file = input.files[0];
    const ext = (file.name.split(".").pop() || "").toLowerCase();
    if (ALLOWED_PROFILE_TYPES.indexOf(ext) === -1) {
        alert("Please choose a JPG, JPEG, PNG or WEBP image.");
        input.value = "";
        return;
    }

    const preview = document.getElementById("profilePreview");
    const original = preview ? preview.src : "";

    // 1. Show the selected image immediately on the profile page.
    if (preview) {
        preview.src = URL.createObjectURL(file);
    }

    // 2. Upload to the backend.
    const fd = new FormData();
    fd.append("profile", file);

    fetch("/profile/upload-image", { method: "POST", body: fd })
        .then(function (res) {
            return res.json().then(function (data) {
                return { ok: res.ok, data: data };
            });
        })
        .then(function (result) {
            if (!result.ok || !result.data || !result.data.success) {
                throw new Error((result.data && result.data.message) || "Upload failed.");
            }
            // 3/4. Reload the profile image from the saved path.
            if (preview) {
                preview.src = result.data.image_url;
            }
            const navImg = document.querySelector(".nav-avatar img");
            if (navImg) {
                navImg.src = result.data.image_url;
            }
            input.value = "";
        })
        .catch(function (err) {
            alert("Upload failed: " + err.message);
            if (preview && original) {
                preview.src = original;
            }
            input.value = "";
        });
}

// Remove the saved image and return to the default avatar.
function removeProfilePhoto() {
    closeMenu();
    fetch("/remove_profile", { method: "POST" })
        .then(function (res) {
            return res.json().then(function (data) {
                return { ok: res.ok, data: data };
            });
        })
        .then(function (result) {
            if (result.ok && result.data && result.data.success) {
                const preview = document.getElementById("profilePreview");
                if (preview) {
                    preview.src = "/static/images/profile-icon.png";
                }
                const navImg = document.querySelector(".nav-avatar img");
                if (navImg) {
                    navImg.src = "/static/images/profile-icon.png";
                }
            } else {
                window.location.href = "/remove_profile";
            }
        })
        .catch(function () {
            window.location.href = "/remove_profile";
        });
}

// Close popup menu when clicking outside
document.addEventListener("click", function (event) {
    const popup = document.getElementById("uploadPopup");
    const editButton = document.querySelector(".camera-edit-btn") || document.querySelector(".profile-edit-btn");
    const avatarWrapper = document.querySelector(".profile-avatar") || document.querySelector(".profile-avatar-wrapper");

    if (popup && popup.style.display === "block") {
        const isClickInsidePopup = popup.contains(event.target);
        const isClickOnButton = editButton && editButton.contains(event.target);
        const isClickOnAvatar = avatarWrapper && avatarWrapper.contains(event.target);

        if (!isClickInsidePopup && !isClickOnButton && !isClickOnAvatar) {
            closeMenu();
        }
    }
});