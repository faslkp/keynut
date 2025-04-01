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
            } else if (this.href.includes("category")) {
                paramName = "category";
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


    // Edit product buttons event listeners 
    document.querySelectorAll(".edit-product").forEach(button => {
        button.addEventListener("click", function (event) {
            // Setting up modal and Save button and disabling to wait for fetching product data
            const modalSaveButton = document.getElementById('addProductSubmitButton');
            const newButton = modalSaveButton.cloneNode(true); // Clone the button (without event listeners)
            modalSaveButton.parentNode.replaceChild(newButton, modalSaveButton); // Replace old button
            newButton.disabled = true;
            newButton.innerText = "Please wait"
            document.getElementById('addProductModalLabel').innerText = "Edit Product"

            // Get userID
            const productId = this.dataset.productId

            // Construct URL
            const url = `/admin/products/${productId}/edit/`

            // Fetch product data
            fetch(url, {
                method: "GET",
                credentials: 'include',
                headers: {
                    "Content-Type": "application/json",
                },
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(errData => {
                        throw new Error(`Server error: ${response.status} ${response.statusText} - ${JSON.stringify(errData)}`);
                    });
                }
                return response.json(); // Convert response to JSON if OK
            })
            .then(data => {
                if (!data) throw new Error("No data received from the server");

                console.log(data);
                
                // Assigning existing values to form
                document.getElementById('id_name').value = data.name
                document.getElementById('id_description').value = data.description
                document.getElementById('id_price').value = data.price
                document.getElementById('id_discount').value = data.discount
                document.getElementById('id_category').value = data.category
                document.getElementById('id_unit').value = data.unit
                document.getElementById('id_stock').value = data.stock
                
                // Assigning image to form
                const imagePreview = document.getElementById('image-preview')
                imagePreview.src = data.image
                imagePreview.style.display = 'block';

                // Assigning variants
                const variantsInputs = document.querySelectorAll("input[name='variants']")
                if (data.variants && Array.isArray(data.variants)) {
                    variantsInputs.forEach(input => {
                        data.variants.forEach(variant => {
                            // Convert both values to the same type for comparison
                            if (parseInt(input.value) === parseInt(variant.id)) {
                                input.checked = true;
                            }
                        });
                    });
                }

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

                    // Get form data
                    let form = document.getElementById("productForm");
                    let formData = new FormData(form);
                    let imageFile = formData.get("image");

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

                    // Ajax request to edit product details
                    fetch(url, {
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
                });
            })
            .catch(error => {
                console.log("Error occured.")
                alert("Something went wrong! Please reload the page.")
            });
        });
    });
    
    // Unlist Product buttons event listeners
    // Select all unlist buttons and attach a click event listener
    document.querySelectorAll(".unlist-product").forEach(button => {
        button.addEventListener("click", function (event) {
            event.preventDefault();  // Prevent default anchor behavior

            let productId = this.dataset.productId;  // Get the product ID from data attribute
            let productName = this.dataset.productName;  // Get the product name from data attribute
            let isListed = this.dataset.isListed;

            // Set confirmation modal details
            let modalLabel = document.getElementById('unlistModalLabel');
            let modalDesc = document.getElementById('unlistModalDesc');
            modalLabel.innerText = `Confirm ${isListed == "True" ? "unlisting" : "re-listing"}.`;
            modalDesc.innerText = `Are you sure you want to ${isListed == "True" ? "unlist" : "re-list"} ${productName}?`;

            // Get the feedback modal elements
            const feedbackModalTrigger = document.getElementById('triggerFeedbackModal');
            let feedbackModalLabel = document.getElementById('feedbackModalLabel');
            let feedbackModalDesc = document.getElementById('feedbackModalDesc');
            feedbackModalLabel.innerText = "";
            feedbackModalDesc.innerText = "";

            // Select the confirm button in the modal
            let confirmButton = document.getElementById('unlistConfirmButton');
            confirmButton.innerText = "Continue"
            confirmButton.disabled = false

            // Remove any previously attached event listeners to avoid multiple listeners
            confirmButton.removeEventListener('click', confirmAction);

            // Select modal close button on getting respose
            modelCloseButton = document.getElementById('unlistCloseButton')

            // Attach a new event listener for the current button click
            function confirmAction() {
                console.log('Unlisting product with ID:', productId);
                
                // Disabling confirm button to avoid duplicate actions.
                confirmButton.disabled = true;
                confirmButton.innerText = "Please wait"
                
                let url = `/admin/products/${productId}/unlist/`;  // Construct the URL

                fetch(url, {
                    method: "POST",
                    credentials: 'include',
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": getCookie("csrftoken")  // CSRF protection
                    },
                    body: JSON.stringify({ action: "unlist" })  // Send data if needed
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
                        let field = document.getElementById(`listing-status-${productId}`);
                        if (field.innerText == "Listed") {
                            field.innerText = "Not Listed";
                        } else {
                            field.innerText = "Listed";
                        }

                        // Update button data
                        if (isListed == "True") {
                            button.dataset.isListed = "False"
                            button.innerHTML = "<i class='bi bi-check-circle'></i>"
                            button.classList.remove('text-danger');
                            button.classList.add('text-success');
                        } else {
                            button.dataset.isListed = "True"
                            button.innerHTML = "<i class='bi bi-x-circle'></i>"
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

    // Add stock add event listeners
    document.querySelectorAll(".add-stock").forEach(button => {
        button.addEventListener("click", function (event) {
            
            // Get product details
            const productID = this.dataset.productId
            const productName = this.dataset.productName

            console.log("Adding stock to product ID:" + productID)
            
            // Setting modal with selected product name
            const modalDesc = document.getElementById("addStockModalDesc")
            modalDesc.innerText = `Product: ${productName}`

            // Construct URL
            const url = `/admin/products/${productID}/add-stock/`

            // Removing any existing event listeners from Add Stock button
            const addStockSubmitButton = document.getElementById('addStockSubmitButton');
            const newStockSubmitButton = addStockSubmitButton.cloneNode(true);
            addStockSubmitButton.parentNode.replaceChild(newStockSubmitButton, addStockSubmitButton);
            
            // Add event listener to Add Stock button
            newStockSubmitButton.addEventListener("click", function (event) {
                event.preventDefault();

                // Get the feedback modal elements
                const feedbackModalTrigger = document.getElementById('triggerFeedbackModal');
                let feedbackModalLabel = document.getElementById('feedbackModalLabel');
                let feedbackModalDesc = document.getElementById('feedbackModalDesc');
                feedbackModalLabel.innerText = "";
                feedbackModalDesc.innerText = "";

                // Add reload event to the feedback modal close button
                document.getElementById("feedbackModalCloseButton").addEventListener("click", function () {
                    location.reload();
                }, { once: true });

                // data validation
                const stockQuantity = document.getElementById("id-add-stock").value
                if (!stockQuantity || stockQuantity < 1) {
                    alert("New stock quantity should be atleast 1 unit.")
                    return;
                }

                // Disable button to avoid duplicate requests
                this.disabled = true;
                this.innerText = "Please wait"

                // Prepare form data
                let formData = new FormData();
                formData.append("new-stock", stockQuantity);
                console.log(formData)

                // Ajax request
                fetch(url, {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": getCookie("csrftoken")  // CSRF protection
                    },
                    credentials: "include",
                    body: formData
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
        })
    })

    // Update add product modal on Add button click
    document.getElementById('addProductButton').addEventListener('click', () => {
        document.getElementById('addProductModalLabel').innerText = "Add New Product"
    })

    // Add product ajax request
    document.getElementById('addProductSubmitButton').addEventListener('click', function (event) {
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
        let form = document.getElementById("productForm");
        let formData = new FormData(form); // Collect form data including file inputs


        let imageFile = formData.get("image");

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
        fetch("/admin/products/add/", {
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

    // Cropper
    let imageInput = document.querySelector("input[name='image']");
    let imagePreview = document.getElementById("image-preview");
    let cropButton = document.getElementById("crop-button");
    let editImageButton = document.getElementById("editImageButton");
    let removeImageButton = document.getElementById("removeImageButton");
    let croppedImageDataInput = document.getElementById("cropped_image_data");
    let cropper;
    
    imageInput.addEventListener("change", function (event) {
        let file = event.target.files[0];
        if (file) {
            let reader = new FileReader();
            reader.onload = function (e) {
                imagePreview.src = e.target.result;
                imagePreview.style.display = "block";
                cropButton.style.display = "block";

                if (cropper) {
                    cropper.destroy(); // Remove previous cropper instance
                }

                cropper = new Cropper(imagePreview, {
                    aspectRatio: 1, // 1:1 ratio (square)
                    viewMode: 2, // Restrict cropping area
                });
            };
            reader.readAsDataURL(file);
        }
    });

    // Function to show/hide edit/remove buttons
    function toggleImageButtons(show) {
        editImageButton.style.display = show ? "inline-block" : "none";
        removeImageButton.style.display = show ? "inline-block" : "none";
        cropButton.style.display = show ? "none" : "inline-block";
    }

    cropButton.addEventListener("click", function () {
        if (cropper) {
            let croppedCanvas = cropper.getCroppedCanvas({
                width: 1000,
                height: 1000
            });
    
            // Convert cropped image to Base64
            let croppedImageDataURL = croppedCanvas.toDataURL("image/png");
    
            // Update image preview with cropped image
            imagePreview.src = croppedImageDataURL;
            imagePreview.style.display = "block";
            imagePreview.style.width = "auto";
            imagePreview.style.height = "auto";
            imagePreview.style.maxWidth = "100%";
    
            console.log("Image preview updated:", imagePreview);
    
            // Destroy the cropper instance to remove cropping UI
            cropper.destroy();
            cropper = null; // Reset cropper variable
    
            // Store cropped image data in hidden input
            croppedImageDataInput.value = croppedImageDataURL;

            // Show the buttons
            toggleImageButtons(true);
        }
    });

    // Edit Image: Reinitialize Cropper
    editImageButton.addEventListener("click", function () {
        if (!cropper) {
            cropper = new Cropper(imagePreview, {
                aspectRatio: 1,  
                viewMode: 1
            });
        }
        cropButton.style.display = "inline-block"
    });

    // Remove Image: Reset everything
    removeImageButton.addEventListener("click", function () {
        // Remove preview image
        imagePreview.src = "";
        imagePreview.style.display = "none";

        // Reset file input
        imageInput.value = "";

        // Hide buttons
        toggleImageButtons(false);

        // Destroy Cropper if exists
        if (cropper) {
            cropper.destroy();
            cropper = null;
        }
    });
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
        errors["name"] = ["Product name is required."];
    }

    // Validate description
    if (!formData.get("description") || formData.get("description").trim() === "") {
        errors["description"] = ["Description is required."];
    }

    // Validate price (must be a positive number)
    let price = parseFloat(formData.get("price"));
    if (isNaN(price) || price <= 0) {
        errors["price"] = ["Enter a valid price."];
    }

    // Validate discount (must be a positive number or zero)
    let discount = parseFloat(formData.get("discount"));
    if (isNaN(discount) || discount < 0) {
        errors["discount"] = ["Enter a valid discount. If no discount, enter '0' (zero)."];
    }

    // Validate category
    if (!formData.get("category")) {
        errors["category"] = ["Please select a category."];
    }

    // Validate unit
    if (!formData.get("unit") || formData.get("unit").trim() === "") {
        errors["unit"] = ["Product unit is required."];
    }


    // Validate stock (must be a positive integer)
    let stock = parseInt(formData.get("stock"));
    if (isNaN(stock) || stock < 0) {
        errors["stock"] = ["Stock must be a non-negative number."];
    }

    // Check if form is in edit mode (by detecting existing image)
    let existingImage = document.getElementById("image-preview"); // Assume this contains the image URL if editing
    let imageFile = formData.get("image");
    
    if (!existingImage || (imageFile && imageFile.size > 0)) {
        if (!imageFile || imageFile.size === 0) {
            errors["image"] = ["Please upload an image."];
        } else {
            // If a file is selected, check format and size
            let allowedExtensions = ["jpg", "jpeg", "png", "webp"];
            let fileName = imageFile.name.toLowerCase();
            let fileExtension = fileName.split(".").pop();

            if (!allowedExtensions.includes(fileExtension)) {
                errors["image"] = ["Invalid image format. Allowed: jpg, jpeg, png, webp."];
            }
            if (imageFile.size > 5 * 1024 * 1024) { // 5MB limit
                errors["image"] = ["Image size must be less than 5MB."];
            }
        }
    }

    // Validate cropped image (only if a new image is uploaded)
    let croppedImage = document.getElementById("cropped_image_data").value;

    if (imageFile && imageFile.size > 0 && !croppedImage) {
        errors["image"] = ["Please crop the selected image before submitting."];
    }

    // Validate Variants - At least one must be selected
    let variants = document.querySelectorAll('input[name="variants"]:checked');
    if (variants.length === 0) {
        errors["variants"] = ["Please select at least one variant."];
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
        if (field === "variants") {
            // Fix for variants (checkbox group)
            let variantContainer = document.getElementById("variant-error-container");

            if (!variantContainer) {
                let variantsWrapper = document.getElementById("variants-wrapper");
                if (variantsWrapper) {
                    let errorContainer = document.createElement("div");
                    errorContainer.id = "variant-error-container";
                    errorContainer.classList.add("invalid-feedback", "d-block", "mt-2");
                    errorContainer.innerHTML = errors[field].join("<br>");
                    variantsWrapper.appendChild(errorContainer);
                }
            } else {
                variantContainer.innerHTML = errors[field].join("<br>"); // Update existing error message
            }

            // Prevent checkboxes from being marked as invalid
            document.querySelectorAll('input[name="variants"]').forEach(checkbox => {
                checkbox.classList.remove("is-invalid");
            });
        } else {
            // Normal field error handling
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
        }
    });
}




