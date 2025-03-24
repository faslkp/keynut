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
    document.querySelectorAll(".edit-offer").forEach(button => {
        button.addEventListener("click", function (event) {
            
            // Setting up modal and Save button and disabling to wait for fetching data
            const modalSaveButton = document.getElementById('addOfferSubmitButton');
            const newButton = modalSaveButton.cloneNode(true); // Clone the button (without any previous event listeners)
            modalSaveButton.parentNode.replaceChild(newButton, modalSaveButton); // Replace old button
            newButton.disabled = true;
            newButton.innerText = "Please wait"
            document.getElementById('addOfferModalLabel').innerText = "Edit Offer"

            // Get userID
            const offerId = this.dataset.offerId
            const offerName = this.dataset.offerName

            // Construct URL
            const url = `/admin/offers/${offerId}/edit/`

            // Update form with current data
            fetch(url, {
                method: "GET",
                credentials: 'include',
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCookie("csrftoken")  // CSRF protection
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    document.getElementById("id_name").value = data.offer.name;
                    document.getElementById("id_description").value = data.offer.description;
                    document.getElementById("id_discount").value = data.offer.discount;
                    document.getElementById("id_start_date").value = data.offer.start_date;
                    document.getElementById("id_end_date").value = data.offer.end_date;
                } else {
                    alert("Something went wrong! Please reload the page and try again.");
                }
            })
            .catch(error => {
                alert("Something went wrong! Please reload the page and try again.");
            });

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
                let description = document.getElementById("id_description").value.trim();
                let discount = document.getElementById("id_discount").value.trim();
                let start_date = document.getElementById("id_start_date").value.trim();
                let end_date = document.getElementById("id_end_date").value.trim();

                // Validation checks
                let errors = validateFormData({ name, description, discount, start_date, end_date });
                if (Object.keys(errors).length > 0) {
                    event.preventDefault();
                    displayErrors(errors);
                    return;
                }

                // Disable button to avoid duplicate requests
                this.disabled = true;
                this.innerText = "Please wait";

                // Prepare form data
                let formData = new FormData();
                formData.append("name", name);
                formData.append("description", description);
                formData.append("discount", discount);
                formData.append("start_date", start_date);
                formData.append("end_date", end_date);


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
    
    // Disable Offer buttons event listeners
    // Select all disable buttons and attach a click event listener
    document.querySelectorAll(".disable-offer").forEach(button => {
        button.addEventListener("click", function (event) {
            event.preventDefault();  // Prevent default anchor behavior

            let offerId = this.dataset.offerId;  // Get the offer ID from data attribute
            let offerName = this.dataset.offerName;  // Get the offer name from data attribute
            let isActive = this.dataset.isActive;  // Get the current status from data attribute

            // Set confirmation modal details
            let modalLabel = document.getElementById('disableModalLabel');
            let modalDesc = document.getElementById('disableModalDesc');
            modalLabel.innerText = `Confirm ${isActive == "True" ? "to disable" : "to enable"}.`;
            modalDesc.innerText = `Are you sure you want to ${isActive == "True" ? "disable" : "enable"} ${offerName}?`;

            // Get the feedback modal elements
            const feedbackModalTrigger = document.getElementById('triggerFeedbackModal');
            let feedbackModalLabel = document.getElementById('feedbackModalLabel');
            let feedbackModalDesc = document.getElementById('feedbackModalDesc');
            feedbackModalLabel.innerText = "";
            feedbackModalDesc.innerText = "";

            // Select the confirm button in the modal
            let confirmButton = document.getElementById('disableConfirmButton');
            confirmButton.innerText = "Continue"
            confirmButton.disabled = false

            // Remove any previously attached event listeners to avoid multiple listeners
            confirmButton.removeEventListener('click', confirmAction);

            // Select modal close button on getting respose
            modelCloseButton = document.getElementById('disableCloseButton')

            // Attach a new event listener for the current button click
            function confirmAction() {                
                // Disabling confirm button to avoid duplicate actions.
                confirmButton.disabled = true;
                confirmButton.innerText = "Please wait"
                
                let url = `/admin/offers/${offerId}/disable/`;  // Construct the URL

                fetch(url, {
                    method: "POST",
                    credentials: 'include',
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": getCookie("csrftoken")  // CSRF protection
                    },
                    body: JSON.stringify({ action: "disable" })  // Send data if needed
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
                        let field = document.getElementById(`active-status-${offerId}`);
                        if (field.innerText == "Active") {
                            field.innerText = "Disabled";
                        } else {
                            field.innerText = "Active";
                        }

                        // Update button data
                        if (isActive == "True") {
                            button.dataset.isActive = "False"
                            button.innerHTML = "<i class='bi bi-arrow-counterclockwise'></i>"
                            button.classList.remove('text-danger');
                            button.classList.add('text-success');
                        } else {
                            button.dataset.isActive = "True"
                            button.innerHTML = "<i class='bi bi-slash-circle'></i>"
                            button.classList.remove('text-success');
                            button.classList.add('text-danger');
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

    // Update add offer modal on Add button click
    document.getElementById('addOfferButton').addEventListener('click', () => {
        document.getElementById('addOfferModalLabel').innerText = "Add New Offer"
    })

    // Add offer ajax request
    document.getElementById('addOfferSubmitButton').addEventListener('click', function (event) {
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
        let form = document.getElementById("offerForm");
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
        fetch("/admin/offers/add/", {
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
// Trim all text data
function trimFormData(formData) {
    for (let [key, value] of formData.entries()) {
        if (typeof value === "string") {
            formData.set(key, value.trim());
        }
    }
}

// Perform validation
function validateFormData(formData) {
    let errors = {};

    // Trim data first
    trimFormData(formData);

    // Validate offer name
    if (!formData.get("name")) {
        errors.name = ["Offer name is required"];
    }

    // Validate discount (required and must be a number)
    const discount = formData.get("discount_value");
    if (!discount) {
        errors.discount_value = ["Discount value is required"];
    } else if (isNaN(discount) || Number(discount) <= 0) {
        errors.discount_value = ["Discount value must be a valid number greater than 0"];
    }

    // Validate minimum purchase value (optional but must be a valid number)
    const minPurchase = formData.get("min_purchase_value");
    if (minPurchase && (isNaN(minPurchase) || Number(minPurchase) < 0)) {
        errors.minimum_purchase_value = ["Minimum purchase value must be a valid number"];
    }

    // Validate maximum discount amount (optional but must be a valid number)
    const maxDiscount = formData.get("max_discount_amount");
    if (maxDiscount && (isNaN(maxDiscount) || Number(maxDiscount) < 0)) {
        errors.maximum_discount_amount = ["Maximum discount amount must be a valid number"];
    }

    // Validate start and end dates
    const startDate = formData.get("start_date") ? new Date(formData.get("start_date")) : null;
    const endDate = formData.get("end_date") ? new Date(formData.get("end_date")) : null;
    const today = new Date();
    today.setHours(0, 0, 0, 0); // Normalize today to compare only dates

    if (!startDate) {
        errors.start_date = ["Start date is required"];
    } else if (startDate < today) {
        errors.start_date = ["Start date cannot be before today"];
    }

    if (!endDate) {
        errors.end_date = ["End date is required"];
    } else if (endDate < today) {
        errors.end_date = ["End date cannot be before today"];
    }

    if (startDate && endDate && startDate >= endDate) {
        errors.start_date = ["Start date must be before end date"];
        errors.end_date = ["End date must be after start date"];
    }

    // Validate applicable products and categories based on offer type
    const offerType = formData.get("offer_type");

    if (offerType === "product") {
        const selectedProducts = formData.getAll("applicable_products");
        if (selectedProducts.length === 0) {
            errors.applicable_products = ["At least one product must be selected for a product-based offer."];
        }
    } else if (offerType === "category") {
        const selectedCategories = formData.getAll("applicable_categories");
        if (selectedCategories.length === 0) {
            errors.applicable_categories = ["At least one category must be selected for a category-based offer."];
        }
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
            inputField.classList.add("is-invalid");

            // Remove existing error if present
            let existingError = inputField.parentNode.querySelector(".invalid-feedback");
            if (existingError) {
                existingError.remove();
            }

            // Create and display error message
            let errorContainer = document.createElement("div");
            errorContainer.classList.add("invalid-feedback");
            errorContainer.textContent = errors[field].join(" ");
            errorContainer.id = `${field}-error`;

            inputField.parentNode.appendChild(errorContainer);
            inputField.setAttribute("aria-invalid", "true");
            inputField.setAttribute("aria-describedby", `${field}-error`);
        }
    });
}




