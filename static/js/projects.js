document.addEventListener("DOMContentLoaded", () => {

    // --- 1. Toast Notification ---
    function showToast(message, isError = false) {
        const toast = document.getElementById("toastNotification");
        const toastIcon = document.getElementById("toastIcon");
        const toastMessage = document.getElementById("toastMessage");

        if (!toast) return;

        toastMessage.textContent = message;
        if (isError) {
            toast.style.borderLeftColor = "#ef4444";
            toastIcon.className = "fa-solid fa-circle-xmark";
            toastIcon.style.color = "#ef4444";
        } else {
            toast.style.borderLeftColor = "var(--accent)";
            toastIcon.className = "fa-solid fa-circle-check";
            toastIcon.style.color = "var(--accent)";
        }

        toast.classList.add("show");
        setTimeout(() => toast.classList.remove("show"), 3500);
    }

    // --- 2. Modal Open / Close Logic ---
    function openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) modal.classList.add("active");
    }

    function closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) modal.classList.remove("active");
    }

    document.querySelectorAll(".pj-modal-close, .closeModalBtn").forEach(btn => {
        btn.addEventListener("click", () => {
            const modalId = btn.getAttribute("data-modal");
            closeModal(modalId);
        });
    });

    document.querySelectorAll(".pj-modal-overlay").forEach(overlay => {
        overlay.addEventListener("click", (e) => {
            if (e.target === overlay) {
                overlay.classList.remove("active");
            }
        });
    });

    // --- 3. Real-time Search Filtering ---
    const searchInput = document.getElementById("projectSearch");
    if (searchInput) {
        searchInput.addEventListener("input", (e) => {
            const query = e.target.value.toLowerCase().trim();
            const projectCards = document.querySelectorAll(".pj-card");
            let visibleCount = 0;

            projectCards.forEach(card => {
                const title = card.getAttribute("data-title") || "";
                const prompt = card.getAttribute("data-prompt") || "";

                if (title.includes(query) || prompt.includes(query)) {
                    card.style.display = "";
                    visibleCount++;
                } else {
                    card.style.display = "none";
                }
            });

            const noResults = document.getElementById("noSearchResults");
            if (noResults) {
                noResults.style.display = visibleCount === 0 && projectCards.length > 0 ? "" : "none";
            }
        });
    }

    // --- 4. Create Project Logic ---
    const openCreateModalBtn = document.getElementById("openCreateModalBtn");
    const emptyCreateBtn = document.getElementById("emptyCreateBtn");
    const createProjectForm = document.getElementById("createProjectForm");

    if (openCreateModalBtn) {
        openCreateModalBtn.addEventListener("click", () => openModal("createProjectModal"));
    }
    if (emptyCreateBtn) {
        emptyCreateBtn.addEventListener("click", () => openModal("createProjectModal"));
    }

    if (createProjectForm) {
        createProjectForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const title = document.getElementById("newTitle").value;
            const prompt = document.getElementById("newPrompt").value;

            try {
                const response = await fetch("/projects/create", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ title, prompt })
                });

                const result = await response.json();
                if (result.success) {
                    showToast(result.message);
                    closeModal("createProjectModal");
                    setTimeout(() => window.location.reload(), 1000);
                } else {
                    showToast(result.error || "Failed to create project", true);
                }
            } catch (err) {
                console.error("Create Project Error:", err);
                showToast("An error occurred while creating project", true);
            }
        });
    }

    // --- 5. Open / Preview Project Logic ---
    let currentPreviewCode = "";

    document.addEventListener("click", async (e) => {
        const openBtn = e.target.closest(".btn-open");
        if (openBtn) {
            const projectId = openBtn.getAttribute("data-id");
            try {
                const response = await fetch(`/projects/get/${projectId}`);
                const data = await response.json();

                if (data.success && data.project) {
                    const project = data.project;
                    currentPreviewCode = project.html_code || "<h1>No HTML Code Available</h1>";

                    document.getElementById("previewProjectTitle").innerHTML = `<i class="fa-solid fa-globe"></i> ${project.title}`;
                    document.getElementById("previewProjectDate").textContent = `Created: ${project.created_at} | Modified: ${project.updated_at || project.created_at}`;

                    const iframe = document.getElementById("projectPreviewIframe");
                    iframe.srcdoc = currentPreviewCode;

                    const codeArea = document.getElementById("sourceCodeArea");
                    codeArea.value = currentPreviewCode;

                    document.getElementById("previewFrameWrapper").style.display = "";
                    document.getElementById("sourceCodeWrapper").style.display = "none";
                    document.getElementById("toggleCodeBtn").innerHTML = `<i class="fa-solid fa-code"></i> Source`;

                    openModal("openProjectModal");
                } else {
                    showToast(data.error || "Failed to fetch project details", true);
                }
            } catch (err) {
                console.error("Open Project Error:", err);
                showToast("Error loading project preview", true);
            }
        }
    });

    // Toggle Code vs Live Preview
    const toggleCodeBtn = document.getElementById("toggleCodeBtn");
    if (toggleCodeBtn) {
        toggleCodeBtn.addEventListener("click", () => {
            const frameWrapper = document.getElementById("previewFrameWrapper");
            const codeWrapper = document.getElementById("sourceCodeWrapper");

            if (codeWrapper.style.display !== "none") {
                codeWrapper.style.display = "none";
                frameWrapper.style.display = "";
                toggleCodeBtn.innerHTML = `<i class="fa-solid fa-code"></i> Source`;
            } else {
                codeWrapper.style.display = "";
                frameWrapper.style.display = "none";
                toggleCodeBtn.innerHTML = `<i class="fa-solid fa-desktop"></i> Preview`;
            }
        });
    }

    // --- 6. Edit Project Logic ---
    document.addEventListener("click", (e) => {
        const editBtn = e.target.closest(".btn-edit");
        if (editBtn) {
            const projectId = editBtn.getAttribute("data-id");
            const title = editBtn.getAttribute("data-title");
            const prompt = editBtn.getAttribute("data-prompt");

            document.getElementById("editProjectId").value = projectId;
            document.getElementById("editTitle").value = title;
            document.getElementById("editPrompt").value = prompt;

            openModal("editProjectModal");
        }
    });

    const editProjectForm = document.getElementById("editProjectForm");
    if (editProjectForm) {
        editProjectForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const projectId = document.getElementById("editProjectId").value;
            const title = document.getElementById("editTitle").value;
            const prompt = document.getElementById("editPrompt").value;

            try {
                const response = await fetch(`/projects/edit/${projectId}`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ title, prompt })
                });

                const result = await response.json();
                if (result.success) {
                    showToast(result.message);
                    closeModal("editProjectModal");

                    // Update UI directly
                    const card = document.getElementById(`card-${projectId}`);
                    if (card) {
                        card.querySelector(".pj-card-title").textContent = title;
                        card.querySelector(".pj-card-desc").textContent = prompt.length > 100 ? prompt.substring(0, 100) + "..." : prompt;
                        card.setAttribute("data-title", title.toLowerCase());
                        card.setAttribute("data-prompt", prompt.toLowerCase());

                        const editBtn = card.querySelector(".btn-edit");
                        if (editBtn) {
                            editBtn.setAttribute("data-title", title);
                            editBtn.setAttribute("data-prompt", prompt);
                        }
                    }
                } else {
                    showToast(result.error || "Failed to update project", true);
                }
            } catch (err) {
                console.error("Edit Project Error:", err);
                showToast("Error updating project", true);
            }
        });
    }

    // --- 7. Duplicate Project Logic ---
    document.addEventListener("click", async (e) => {
        const dupBtn = e.target.closest(".btn-duplicate");
        if (dupBtn) {
            const projectId = dupBtn.getAttribute("data-id");

            try {
                const response = await fetch(`/projects/duplicate/${projectId}`, {
                    method: "POST"
                });

                const result = await response.json();
                if (result.success) {
                    showToast(result.message);
                    setTimeout(() => window.location.reload(), 800);
                } else {
                    showToast(result.error || "Failed to duplicate project", true);
                }
            } catch (err) {
                console.error("Duplicate Project Error:", err);
                showToast("Error duplicating project", true);
            }
        }
    });

    // --- 8. Delete Project Logic ---
    document.addEventListener("click", (e) => {
        const delBtn = e.target.closest(".btn-delete");
        if (delBtn) {
            const projectId = delBtn.getAttribute("data-id");
            const title = delBtn.getAttribute("data-title");

            document.getElementById("deleteProjectId").value = projectId;
            document.getElementById("deleteProjectName").textContent = title;

            openModal("deleteProjectModal");
        }
    });

    const confirmDeleteBtn = document.getElementById("confirmDeleteBtn");
    if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener("click", async () => {
            const projectId = document.getElementById("deleteProjectId").value;

            try {
                const response = await fetch(`/projects/delete/${projectId}`, {
                    method: "POST"
                });

                const result = await response.json();
                if (result.success) {
                    showToast(result.message);
                    closeModal("deleteProjectModal");

                    const card = document.getElementById(`card-${projectId}`);
                    if (card) {
                        card.remove();
                    }

                    // Check if grid is empty
                    const remainingCards = document.querySelectorAll(".pj-card");
                    if (remainingCards.length === 0) {
                        setTimeout(() => window.location.reload(), 500);
                    }
                } else {
                    showToast(result.error || "Failed to delete project", true);
                }
            } catch (err) {
                console.error("Delete Project Error:", err);
                showToast("Error deleting project", true);
            }
        });
    }

    // --- 9. Delete All Projects Logic ---
    const deleteAllBtn = document.getElementById("deleteAllBtn");
    if (deleteAllBtn) {
        deleteAllBtn.addEventListener("click", () => openModal("deleteAllModal"));
    }

    const confirmDeleteAllBtn = document.getElementById("confirmDeleteAllBtn");
    if (confirmDeleteAllBtn) {
        confirmDeleteAllBtn.addEventListener("click", async () => {
            try {
                const response = await fetch("/projects/delete-all", {
                    method: "POST"
                });

                const result = await response.json();
                if (result.success) {
                    showToast(result.message);
                    closeModal("deleteAllModal");
                    setTimeout(() => window.location.reload(), 800);
                } else {
                    showToast(result.error || "Failed to delete all projects", true);
                }
            } catch (err) {
                console.error("Delete All Projects Error:", err);
                showToast("Error deleting all projects", true);
            }
        });
    }

});
