document.addEventListener("DOMContentLoaded", function () {
    // Sort, Filter and Categories
    document.querySelectorAll(".dropdown-item").forEach(item => {
        item.addEventListener("click", function (event) {
            event.preventDefault(); // Prevent default action
    
            let url = new URL(window.location.href);
            
            // Identify parameter type (sortby, filter, or category)
            let paramName;
            if (this.href.includes("sortby")) {
                paramName = "sortby";
            } else if (this.href.includes("filter")) {
                paramName = "filter";
            }
    
            let paramValue = new URL(this.href).searchParams.get(paramName);
    
            url.searchParams.set(paramName, paramValue); // Update the selected parameter
    
            window.location.href = url.toString(); // Reload with updated URL
        });
    });
    
    // Search function
    document.querySelector("input[name='q']").addEventListener("keypress", function (event) {
        if (event.key === "Enter") {
            event.preventDefault();
    
            let url = new URL(window.location.href);
            url.searchParams.set("q", this.value.trim()); // Add search query
    
            window.location.href = url.toString(); // Reload with updated URL
        }
    });

    // Handle pagination links dynamically
    document.addEventListener("click", function (event) {
        if (event.target.closest(".pagination-link")) {  // Check if clicked element or parent has .pagination-link
            event.preventDefault();

            let pageNumber = event.target.closest(".pagination-link").getAttribute("data-page");

            if (pageNumber) {
                let url = new URL(window.location.href);
                url.searchParams.set("page", pageNumber); // Update page number

                window.location.href = url.toString();
            }
        }
    });
    
    // Edit category buttons event listeners
    document.querySelectorAll(".edit-category").forEach(button => {
        button.addEventListener("click", function (event) {
            
            // Setting up modal and Save button and disabling to wait for fetching data
            const modalSaveButton = document.getElementById('addCategorySubmitButton');
            const newButton = modalSaveButton.cloneNode(true); // Clone the button (without any previous event listeners)
            modalSaveButton.parentNode.replaceChild(newButton, modalSaveButton); // Replace old button
            newButton.disabled = true;
            newButton.innerText = "Please wait"
            document.getElementById('addCategoryModalLabel').innerText = "Edit Category"

            // Get userID
            const categoryId = this.dataset.categoryId
            const categoryName = this.dataset.categoryName

            // Construct URL
            const url = `/admin/categories/${categoryId}/edit/`

            // Update form with current data
            document.getElementById('id_name').value = categoryName

            // Re enable Save button
            newButton.disabled = false;
            newButton.innerText = "Save"

            // Attaching new event listener to the Save button
            newButton.addEventListener('click', function (event) {
                event.preventDefault();

                // Get the feedback modal elements
                const feedbackModalTrigger = document.getElementById('triggerFeedbackModal');
                let feedbackModalLabel = document.getElementById('feedbackModalLabel');
                let feedbackModalDesc = document.getElementById('feedbackModalDesc');
                feedbackModalLabel.innerText = "";
                feedbackModalDesc.innerText = "";

                // Add reload event to the modal close button
                document.getElementById("feedbackModalCloseButton").addEventListener("click", function () {
                    location.reload();
                }, { once: true });

                // Form Validation
                let name = document.getElementById("id_name").value.trim();

                // Validation checks
                if (!name) {
                    alert("All fields are required!");
                    return;
                }

                // Disable button to avoid duplicate requests
                this.disabled = true;
                this.innerText = "Please wait";

                // Prepare form data
                let formData = new FormData();
                formData.append("name", name);


                // Ajax request to edit category details
                fetch(url, {
                    method: "POST",
                    body: formData,
                    credentials: "include", // Ensure session data is included
                    headers: {
                        "X-CSRFToken": getCookie("csrftoken")  // CSRF protection
                    },
                })
                .then(response => {
                    if (!response.ok) { // Checks for HTTP errors like 500
                        throw new Error(`Server error: ${response.status}`); // Manually trigger error
                    }
                    return response.json()
                })
                .then(data => {
                    if (data.success) {
                        feedbackModalLabel.innerText = "Success";
                        feedbackModalDesc.innerText = data.message;
                        feedbackModalTrigger.click();
                    } else {
                        feedbackModalLabel.innerText = "Error";
                        feedbackModalDesc.innerText = data.message;
                        feedbackModalTrigger.click();
                    }
                })
                .catch(error => {
                    feedbackModalLabel.innerText = "Error";
                    feedbackModalDesc.innerText = "Something went wrong! Please reload the page and try again.";
                    feedbackModalTrigger.click();
                });
            });
        });
    });
    
    // Delete Category buttons event listeners
    // Select all delete buttons and attach a click event listener
    document.querySelectorAll(".delete-category").forEach(button => {
        button.addEventListener("click", function (event) {
            event.preventDefault();  // Prevent default anchor behavior

            let categoryId = this.dataset.categoryId;  // Get the category ID from data attribute
            let categoryName = this.dataset.categoryName;  // Get the category name from data attribute
            let isDeleted = this.dataset.isDeleted;

            // Set confirmation modal details
            let modalLabel = document.getElementById('deleteModalLabel');
            let modalDesc = document.getElementById('deleteModalDesc');
            modalLabel.innerText = `Confirm ${isDeleted == "True" ? "restore" : "deletion"}.`;
            modalDesc.innerText = `Are you sure you want to ${isDeleted == "True" ? "restore" : "delete"} ${categoryName}?`;

            // Get the feedback modal elements
            const feedbackModalTrigger = document.getElementById('triggerFeedbackModal');
            let feedbackModalLabel = document.getElementById('feedbackModalLabel');
            let feedbackModalDesc = document.getElementById('feedbackModalDesc');
            feedbackModalLabel.innerText = "";
            feedbackModalDesc.innerText = "";

            // Select the confirm button in the modal
            let confirmButton = document.getElementById('deleteConfirmButton');
            confirmButton.innerText = "Continue"
            confirmButton.disabled = false

            // Remove any previously attached event listeners to avoid multiple listeners
            confirmButton.removeEventListener('click', confirmAction);

            // Select modal close button on getting respose
            modelCloseButton = document.getElementById('deleteCloseButton')

            // Attach a new event listener for the current button click
            function confirmAction() {                
                // Disabling confirm button to avoid duplicate actions.
                confirmButton.disabled = true;
                confirmButton.innerText = "Please wait"
                
                let url = `/admin/categories/${categoryId}/delete/`;  // Construct the URL

                fetch(url, {
                    method: "POST",
                    credentials: 'include',
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": getCookie("csrftoken")  // CSRF protection
                    },
                    body: JSON.stringify({ action: "delete" })  // Send data if needed
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        console.log('Request succeeded with response:', data);

                        // Trigger acknowledgement modal
                        feedbackModalLabel.innerText = "Success";
                        feedbackModalDesc.innerText = data.message;
                        feedbackModalTrigger.click();

                        // Update the status in the table
                        let field = document.getElementById(`active-status-${categoryId}`);
                        if (field.innerText == "Active") {
                            field.innerText = "Deleted";
                        } else {
                            field.innerText = "Active";
                        }

                        // Update button data
                        if (isDeleted == "True") {
                            button.dataset.isDeleted = "False"
                            button.innerHTML = "<i class='bi bi-trash'></i>"
                            button.classList.remove('text-success');
                            button.classList.add('text-danger');
                        } else {
                            button.dataset.isDeleted = "True"
                            button.innerHTML = "<i class='bi bi-arrow-counterclockwise'></i>"
                            button.classList.remove('text-danger');
                            button.classList.add('text-success');
                        }
                        
                    } else {
                        // Close confirim modal and Trigger error modal
                        feedbackModalLabel.innerText = "Error";
                        feedbackModalDesc.innerText = data.message;
                        feedbackModalTrigger.click();
                    }

                    // Remove the listener after the action is complete
                    confirmButton.removeEventListener('click', confirmAction);
                })
                .catch(error => {
                    feedbackModalLabel.innerText = "Error";
                    feedbackModalDesc.innerText = error;
                    feedbackModalTrigger.click();

                    // Remove the listener after the action is complete (in case of error)
                    confirmButton.removeEventListener('click', confirmAction);
                });
            }

            // Add the confirmAction event listener to the confirm button
            confirmButton.addEventListener('click', confirmAction);
        });
    });

    // Update add category modal on Add button click
    document.getElementById('addCategoryButton').addEventListener('click', () => {
        document.getElementById('addCategoryModalLabel').innerText = "Add New Category"
    })

    // Add product ajax request
    document.getElementById('addCategorySubmitButton').addEventListener('click', function (event) {
        event.preventDefault();

        // Get the feedback modal elements
        const feedbackModalTrigger = document.getElementById('triggerFeedbackModal');
        let feedbackModalLabel = document.getElementById('feedbackModalLabel');
        let feedbackModalDesc = document.getElementById('feedbackModalDesc');
        feedbackModalLabel.innerText = "";
        feedbackModalDesc.innerText = "";

        // Add reload event to the modal close button
        document.getElementById("feedbackModalCloseButton").addEventListener("click", function () {
            location.reload();
        }, { once: true });

        // Get form data
        let form = document.getElementById("categoryForm");
        let formData = new FormData(form); // Collect form data including file inputs

        // Validation checks
        let errors = validateFormData(formData);
        if (Object.keys(errors).length > 0) {
            event.preventDefault();
            displayErrors(errors);
            return;
        }

        // Disable button to avoid duplicate requests
        this.disabled = true;
        this.innerText = "Please wait";

        // AJAX request
        fetch("/admin/categories/add/", {
            method: "POST",
            body: formData,
            credentials: "include" // Ensure session data is included
        })
        .then(response => {
            if (!response.ok) { // Checks for HTTP errors like 500
                throw new Error(`Server error: ${response.status}`); // Manually trigger error
            }
            return response.json()
        })
        .then(data => {
            if (data.success) {
                feedbackModalLabel.innerText = "Success";
                feedbackModalDesc.innerText = data.message;
                feedbackModalTrigger.click();
            } else {
                feedbackModalLabel.innerText = "Error";
                feedbackModalDesc.innerText = data.message;
                feedbackModalTrigger.click();
            }
        })
        .catch(error => {
            feedbackModalLabel.innerText = "Error";
            feedbackModalDesc.innerText = "Something went wrong! Please reload the page and try again.";
            feedbackModalTrigger.click();
        });
    })
});

// Function to get CSRF token (needed for Django security)
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        document.cookie.split(';').forEach(cookie => {
            let trimmed = cookie.trim();
            if (trimmed.startsWith(name + '=')) {
                cookieValue = decodeURIComponent(trimmed.substring(name.length + 1));
            }
        });
    }
    return cookieValue;
}

// Function to validate form data before submitting
function validateFormData(formData) {
    let errors = {}; // Change from array to object

    // Validate name
    if (!formData.get("name") || formData.get("name").trim() === "") {
        errors["name"] = ["Category name is required."];
    }

    return errors;
}

// Function to display validation errors
function displayErrors(errors) {
    console.log("Displaying errors:", errors);

    // Clear previous errors
    document.querySelectorAll(".invalid-feedback").forEach(el => el.remove());
    document.querySelectorAll(".is-invalid").forEach(el => el.classList.remove("is-invalid"));

    // Show new errors
    Object.keys(errors).forEach(field => {
        let inputField = document.querySelector(`[name="${field}"]`);

        if (inputField) {
            inputField.classList.add("is-invalid"); // Highlight field

            let existingError = inputField.parentNode.querySelector(".invalid-feedback");
            if (!existingError) {
                let errorContainer = document.createElement("div");
                errorContainer.classList.add("invalid-feedback");
                errorContainer.innerHTML = errors[field].join("<br>");
                inputField.parentNode.appendChild(errorContainer);
            }
        }
    });
}




