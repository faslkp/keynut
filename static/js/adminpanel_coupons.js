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
    
    // Edit coupon buttons event listeners
    document.querySelectorAll(".edit-coupon").forEach(button => {
        button.addEventListener("click", function (event) {
            
            // Setting up modal and Save button and disabling to wait for fetching data
            const modalSaveButton = document.getElementById('addCouponSubmitButton');
            const newButton = modalSaveButton.cloneNode(true); // Clone the button (without any previous event listeners)
            modalSaveButton.parentNode.replaceChild(newButton, modalSaveButton); // Replace old button
            newButton.disabled = true;
            newButton.innerText = "Please wait"
            document.getElementById('addCouponModalLabel').innerText = "Edit Coupon"

            // Get userID
            const couponId = this.dataset.couponId
            const couponName = this.dataset.couponName

            // Construct URL
            const url = `/admin/coupons/${couponId}/edit/`

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
                    populateForm(data.data);
                } else {
                    alert(data.message);
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
                let editForm = document.getElementById("couponForm");
                let editFormData = new FormData(editForm);

                let errors = validateFormData(editFormData);
                if (Object.keys(errors).length > 0) {
                    event.preventDefault();
                    displayErrors(errors);
                    return;
                }

                // Disable button to avoid duplicate requests
                this.disabled = true;
                this.innerText = "Please wait";

                // Ajax request to edit category details
                fetch(url, {
                    method: "POST",
                    body: editFormData,
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

    function populateForm(data) {
        for (const field in data) {
            let input = document.querySelector(`#addCouponModal form [name="${field}"]`);
            if (input) {
                if (input.tagName === "SELECT" && input.multiple) {
                    // Handle Multi-Select Dropdowns (Users, Products, Categories)
                    Array.from(input.options).forEach(option => {
                        option.selected = data[field].includes(parseInt(option.value));
                    });
                } else if (input.type === "checkbox") {
                    // Handle Boolean Fields
                    input.checked = data[field];
                } else if (input.type === "datetime-local" || input.type === "date") {
                    // Handle date time fields
                    let dateObj = new Date(data[field]); // Convert UTC string to Date object
                    let localDateTime = new Date(dateObj.getTime() - dateObj.getTimezoneOffset() * 60000)
                        .toISOString()
                        .slice(0, 16);  // Format as "YYYY-MM-DDTHH:MM"
                    input.value = localDateTime;
                } else {
                    // Handle Regular Input Fields
                    input.value = data[field];
                }
            }
        }
    }
    
    
    // Disable Coupon buttons event listeners
    // Select all disable buttons and attach a click event listener
    document.querySelectorAll(".disable-coupon").forEach(button => {
        button.addEventListener("click", function (event) {
            event.preventDefault();  // Prevent default anchor behavior

            let couponId = this.dataset.couponId;  // Get the coupon ID from data attribute
            let couponName = this.dataset.couponName;  // Get the coupon name from data attribute
            let isActive = this.dataset.isActive;  // Get the current status from data attribute

            // Set confirmation modal details
            let modalLabel = document.getElementById('disableModalLabel');
            let modalDesc = document.getElementById('disableModalDesc');
            modalLabel.innerText = `Confirm ${isActive == "True" ? "to disable" : "to enable"}.`;
            modalDesc.innerText = `Are you sure you want to ${isActive == "True" ? "disable" : "enable"} ${couponName}?`;

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
                
                let url = `/admin/coupons/${couponId}/disable/`;  // Construct the URL

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
                        let field = document.getElementById(`active-status-${couponId}`);
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

    // Remove coupon - hard delete
    // Select all delete buttons and attach a click event listener
    document.querySelectorAll(".remove-coupon").forEach(button => {
        button.addEventListener("click", function (event) {
            event.preventDefault();  // Prevent default anchor behavior

            let couponId = this.dataset.couponId;  // Get the coupon ID from data attribute
            let couponName = this.dataset.couponName;  // Get the coupon name from data attribute

            // Set confirmation modal details
            let modalLabel = document.getElementById('disableModalLabel');
            let modalDesc = document.getElementById('disableModalDesc');
            modalLabel.innerText = "Confirm deletion";
            modalDesc.innerHTML = `<span class="text-danger">Are you sure you want to delete ${couponName}?</span><br><span class="text-danger fw-bold">This cannot be undone.</span>`;

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
                
                let url = `/admin/coupons/${couponId}/remove/`;  // Construct the URL

                fetch(url, {
                    method: "POST",
                    credentials: 'include',
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": getCookie("csrftoken")  // CSRF protection
                    },
                    body: JSON.stringify({ action: "remove" })  // Send data if needed
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        console.log('Request succeeded with response:', data);

                        // Trigger acknowledgement modal
                        feedbackModalLabel.innerText = "Success";
                        feedbackModalDesc.innerText = data.message;
                        feedbackModalTrigger.click();
                        
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

    // Update add Coupon modal on Add button click
    document.getElementById('addCouponButton').addEventListener('click', () => {
        document.getElementById('addCouponModalLabel').innerText = "Add New Coupon"
    })

    // Add coupon ajax request
    document.getElementById('addCouponSubmitButton').addEventListener('click', function (event) {
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
        let form = document.getElementById("couponForm");
        let formData = new FormData(form);

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
        fetch("/admin/coupons/add/", {
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
    let multiValueFields = ["products", "categories", "users"];

    for (let [key, value] of formData.entries()) {
        if (typeof value === "string") {
            // Only trim non-multi-value fields
            if (!multiValueFields.includes(key)) {
                formData.set(key, value.trim());
            }
        }
    }
}

// Perform validation
function validateFormData(formData) {
    let errors = {};

    // Trim data first
    trimFormData(formData);

    // Validate code
    if (!formData.get("code")) {
        errors.code = ["Coupon code is required"];
    }

    // Validate discount type
    const discountType = formData.get("discount_type");
    if (!discountType || (discountType !== 'percentage' && discountType !== 'flat')) {
        errors.discount_type = ["Invalid discount type"];
    }

    // Validate discount value
    const discountValue = parseFloat(formData.get("discount_value"));
    if (isNaN(discountValue) || discountValue <= 0) {
        errors.discount_value = ["Discount value must be a positive number"];
    }

    // Validate max discount amount (optional)
    const maxDiscountAmount = formData.get("max_discount_amount");
    if (maxDiscountAmount && (isNaN(parseFloat(maxDiscountAmount)) || parseFloat(maxDiscountAmount) < 0)) {
        errors.max_discount_amount = ["Maximum discount amount must be a positive number"];
    }

    // Validate min purchase value (optional)
    const minPurchaseValue = formData.get("min_purchase_value");
    if (minPurchaseValue && (isNaN(parseFloat(minPurchaseValue)) || parseFloat(minPurchaseValue) < 0)) {
        errors.min_purchase_value = ["Minimum purchase value must be a positive number"];
    }

    // Validate start and end dates
    const startDate = formData.get("start_date") ? new Date(formData.get("start_date")) : null;
    const endDate = formData.get("end_date") ? new Date(formData.get("end_date")) : null;

    if (!startDate) {
        errors.start_date = ["Start date is required"];
    }

    if (!endDate) {
        errors.end_date = ["End date is required"];
    }

    if (startDate && endDate && startDate >= endDate) {
        errors.start_date = ["Start date must be before end date"];
        errors.end_date = ["End date must be after start date"];
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




