document.addEventListener("DOMContentLoaded", function () {
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
            modelCloseButton = document.getElementById('modelCloseOnResponse')

            // Attach a new event listener for the current button click
            function confirmAction() {
                console.log('Blocking user with ID:', userId);
                
                // Disabling confirm button to avoid duplicate actions.
                confirmButton.disabled = true;
                confirmButton.innerText = "Please wait"
                
                let url = `/admin/customers/${userId}/blocking/`;  // Construct the URL

                fetch(url, {
                    method: "POST",
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
                        // Close confirim modal and Trigger error modal
                        modelCloseOnResponse.click();
                        feedbackModalLabel.innerText = "Error";
                        feedbackModalDesc.innerText = data.message;
                        feedbackModalTrigger.click();
                    }

                    // Remove the listener after the action is complete
                    confirmButton.removeEventListener('click', confirmAction);
                })
                .catch(error => {
                    modelCloseOnResponse.click()
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
