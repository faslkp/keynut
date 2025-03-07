document.addEventListener("DOMContentLoaded", function () {
    
    // Sort and Filter 
    document.querySelectorAll(".dropdown-item").forEach(item => {
        item.addEventListener("click", function (event) {
            event.preventDefault(); // Prevent default action
    
            let url = new URL(window.location.href);
            let paramName = this.href.includes("sortby") ? "sortby" : "filter"; // Identify parameter type
            let paramValue = new URL(this.href).searchParams.get(paramName);
    
            url.searchParams.set(paramName, paramValue); // Update the selected parameter
            url.searchParams.delete("page"); // Reset to page 1 after filter change
    
            window.location.href = url.toString(); // Reload with updated URL
        });
    });

    // Search function
    document.querySelector("input[name='q']").addEventListener("keypress", function (event) {
        if (event.key === "Enter") {
            event.preventDefault();
    
            let url = new URL(window.location.href);
            url.searchParams.set("q", this.value.trim()); // Add search query
            url.searchParams.delete("page"); // Reset to page 1 after search
    
            window.location.href = url.toString();
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


    // Edit user buttons event listeners
    document.querySelectorAll(".edit-user").forEach(button => {
        button.addEventListener("click", function (event) {
            // Setting up modal and Save button and disabling to wait for fetching user data
            const modalSaveButton = document.getElementById('addCustomerSubmitButton');
            const newButton = modalSaveButton.cloneNode(true); // Clone the button (without event listeners)
            modalSaveButton.parentNode.replaceChild(newButton, modalSaveButton); // Replace old button
            newButton.disabled = true;
            newButton.innerText = "Please wait"
            document.getElementById('addCustomerModalLabel').innerText = "Edit Customer"
            document.getElementById('id_password').placeholder = "Leave this blank to do not change password."

            // Removing required attribute from password field
            document.getElementById('id_password').removeAttribute("required")

            // Get userID
            const userId = this.dataset.userId

            // Construct URL
            const url = `/admin/customers/${userId}/edit/`

            // Fetch user data
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

                document.getElementById('id_first_name').value = data.first_name
                document.getElementById('id_last_name').value = data.last_name
                document.getElementById('id_email').value = data.email
                document.getElementById('id_phone').value = data.phone

                // Re enable Save button
                newButton.disabled = false;
                newButton.innerText = "Save"

                // Attaching new event listener to the Save button
                newButton.addEventListener('click', function (event) {

                    event.preventDefault();

                    // Get the feedback modal elements
                    const feedbackModalTrigger = document.getElementById('triggerFeedbackModal');
                    let feedbackModalLabel = document.getElementById('blockFeedbackModalLabel');
                    let feedbackModalDesc = document.getElementById('blockFeedbackModalDesc');
                    feedbackModalLabel.innerText = "";
                    feedbackModalDesc.innerText = "";

                    // Add reload event to the modal close button
                    document.getElementById("feedbackModalCloseButton").addEventListener("click", function () {
                        location.reload();
                    }, { once: true });

                    // Form Validation
                    let firstName = document.getElementById("id_first_name").value.trim();
                    let lastName = document.getElementById("id_last_name").value.trim();
                    let email = document.getElementById("id_email").value.trim();
                    let password = document.getElementById("id_password").value.trim();
                    let phone = document.getElementById("id_phone").value.trim();
                    let csrfToken = document.querySelector("[name=csrfmiddlewaretoken]").value;

                    // Validation checks
                    if (!firstName || !lastName || !email || !phone) {
                        alert("All fields other than password are required!");
                        return;
                    }

                    if (!validateEmail(email)) {
                        alert("Enter a valid email address!");
                        return;
                    }

                    if (!validatePhone(phone)) {
                        alert("Enter a valid phone number!");
                        return;
                    }

                    // Disable button to avoid duplicate requests
                    this.disabled = true;
                    this.innerText = "Please wait";

                    // Prepare form data
                    let formData = new FormData();
                    formData.append("first_name", firstName);
                    formData.append("last_name", lastName);
                    formData.append("email", email);
                    formData.append("password", password);
                    formData.append("phone", phone);
                    formData.append("csrfmiddlewaretoken", csrfToken);


                    // Ajax request to edit customer details
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
                console.log("error happened.")
                alert("Something went wrong! Please reload the page.")
            });
        });
    });
    
    // Block user buttons event listeners
    // Select all block buttons and attach a click event listener
    document.querySelectorAll(".block-user").forEach(button => {
        button.addEventListener("click", function (event) {
            event.preventDefault();  // Prevent default anchor behavior

            let userId = this.dataset.userId;  // Get the user ID from data attribute
            let userName = this.dataset.userName;  // Get the user name from data attribute
            let isBlocked = this.dataset.isBlocked;

            // Set confirmation modal details
            let modalLabel = document.getElementById('blockModalLabel');
            let modalDesc = document.getElementById('blockModalDesc');
            modalLabel.innerText = `Confirm ${isBlocked == "True" ? "unblocking" : "blocking"} ${userName}`;
            modalDesc.innerText = `Are you sure you want to ${isBlocked == "True" ? "unblock" : "block"} ${userName}? An email confirmation will be sent to ${userName} regarding block status.`;

            // Get the feedback modal elements
            const feedbackModalTrigger = document.getElementById('triggerFeedbackModal');
            let feedbackModalLabel = document.getElementById('blockFeedbackModalLabel');
            let feedbackModalDesc = document.getElementById('blockFeedbackModalDesc');
            feedbackModalLabel.innerText = "";
            feedbackModalDesc.innerText = "";

            // Select the confirm button in the modal
            let confirmButton = document.getElementById('blockConfirmButton');
            confirmButton.innerText = "Continue"
            confirmButton.disabled = false

            // Remove any previously attached event listeners to avoid multiple listeners
            confirmButton.removeEventListener('click', confirmAction);

            // Select modal close button on getting respose
            modelCloseButton = document.getElementById('blockCloseButton')

            // Attach a new event listener for the current button click
            function confirmAction() {
                console.log('Blocking user with ID:', userId);
                
                // Disabling confirm button to avoid duplicate actions.
                confirmButton.disabled = true;
                confirmButton.innerText = "Please wait"
                
                let url = `/admin/customers/${userId}/block/`;  // Construct the URL

                fetch(url, {
                    method: "POST",
                    credentials: 'include',
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": getCookie("csrftoken")  // CSRF protection
                    },
                    body: JSON.stringify({ action: "block" })  // Send data if needed
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
                        let field = document.getElementById(`block-status-${userId}`);
                        if (field.innerText == "Active") {
                            field.innerText = "Blocked";
                        } else {
                            field.innerText = "Active";
                        }

                        // Update 

                        // Update button data
                        if (isBlocked == "True") {
                            button.dataset.isBlocked = "False"
                            button.innerHTML = "<i class='bi bi-x-circle'></i>"
                            button.classList.remove('text-success');
                            button.classList.add('text-danger');
                        } else {
                            button.dataset.isBlocked = "True"
                            button.innerHTML = "<i class='bi bi-check-circle'></i>"
                            button.classList.remove('text-danger');
                            button.classList.add('text-success');
                        }
                        
                    } else {
                        // Close confirm modal and Trigger error modal
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

    // Modify add customer modal on Add button click
    document.getElementById('addCustomerButton').addEventListener('click', () => {
        document.getElementById('addCustomerModalLabel').innerText = "Add New Customer"
    })

    // Add customer ajax request
    document.getElementById('addCustomerSubmitButton').addEventListener('click', function (event) {
        event.preventDefault();

        // Get the feedback modal elements
        const feedbackModalTrigger = document.getElementById('triggerFeedbackModal');
        let feedbackModalLabel = document.getElementById('blockFeedbackModalLabel');
        let feedbackModalDesc = document.getElementById('blockFeedbackModalDesc');
        feedbackModalLabel.innerText = "";
        feedbackModalDesc.innerText = "";

        // Add reload event to the modal close button
        document.getElementById("feedbackModalCloseButton").addEventListener("click", function () {
            location.reload();
        }, { once: true });

        // Form Validation
        let firstName = document.getElementById("id_first_name").value.trim();
        let lastName = document.getElementById("id_last_name").value.trim();
        let email = document.getElementById("id_email").value.trim();
        let password = document.getElementById("id_password").value.trim();
        let phone = document.getElementById("id_phone").value.trim();
        let csrfToken = document.querySelector("[name=csrfmiddlewaretoken]").value;

        // Validation checks
        if (!firstName || !lastName || !email || !password || !phone) {
            alert("All fields are required!");
            return;
        }

        if (!validateEmail(email)) {
            alert("Enter a valid email address!");
            return;
        }

        if (!validatePhone(phone)) {
            alert("Enter a valid phone number!");
            return;
        }

        // Disable button to avoid duplicate requests
        this.disabled = true;
        this.innerText = "Please wait";

        // Prepare form data
        let formData = new FormData();
        formData.append("first_name", firstName);
        formData.append("last_name", lastName);
        formData.append("email", email);
        formData.append("password", password);
        formData.append("phone", phone);
        formData.append("csrfmiddlewaretoken", csrfToken);

        // AJAX request
        fetch("/admin/customers/add/", {
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

// Email validation function
function validateEmail(email) {
    let re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

// Phone validation function (only numbers and 10-15 characters)
function validatePhone(phone) {
    let re = /^[0-9]{10,15}$/;
    return re.test(phone);
}

