
document.addEventListener("DOMContentLoaded", function () {
    
    // Update order status
    document.querySelectorAll(".update-status-btn").forEach(button => {
        button.addEventListener("click", function () {
            let messageId = this.dataset.messageId;
            let newStatus = document.getElementById(`status-${messageId}`).value;
            let csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content'); // Get CSRF token

            // Get the feedback modal elements
            const feedbackModalTrigger = document.getElementById('triggerFeedbackModal');
            const feedbackModalLabel = document.getElementById('feedbackModalLabel');
            const feedbackModalDesc = document.getElementById('feedbackModalDesc');
            feedbackModalLabel.innerText = "";
            feedbackModalDesc.innerText = "";

            fetch("/admin/messages/update-status/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken // Include CSRF token
                },
                body: JSON.stringify({
                    message_id: messageId, 
                    status: newStatus 
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    feedbackModalLabel.innerText = "Success";
                    feedbackModalDesc.innerText = data.message;
                    feedbackModalTrigger.click();
                    if (newStatus != 'new') {
                        document.getElementById(`message-${messageId}`).classList.remove('fw-bold')
                    } else {
                        document.getElementById(`message-${messageId}`).classList.add('fw-bold')
                    }
                } else {
                    feedbackModalLabel.innerText = "Error";
                    feedbackModalDesc.innerText = data.message;
                    feedbackModalTrigger.click();
                }
            })
            .catch(error => console.error("Error:", error));
        });
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

    // Sort, Filter and Categories
    document.querySelectorAll(".dropdown-item").forEach(item => {
        item.addEventListener("click", function (event) {
            event.preventDefault(); // Prevent default action
    
            let url = new URL(window.location.href);
            
            // Identify parameter type (sortby, filter, or category)
            let paramName;
            if (this.href.includes("sortby")) {
                paramName = "sortby";
            } else if (this.href.includes("status")) {
                paramName = "status";
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

    // View message event listeners 
    document.querySelectorAll(".btn-view-message").forEach(button => {
        button.addEventListener("click", function (event) {
            // Setting up Update Status button and disabling to wait for fetching product data
            document.getElementById('messageDetailsModalLabel').innerText = "Message"

            // Getting order details fields
            const messageDate = document.querySelector('.message-date');
            const messageUser = document.querySelector('.message-user');
            const messageName = document.querySelector('.message-name');
            const messageEmail = document.querySelector('.message-email');
            const messagePhone = document.querySelector('.message-phone');
            const messageMessage = document.querySelector('.message-message');

            // Clear existing values
            messageDate.innerText = "";
            messageUser.innerText = "";
            messageName.innerText = "";
            messageEmail.innerText = "";
            messagePhone.innerText = "";
            messageMessage.innerText = "";

            // Get userID
            const messageId = this.dataset.messageId

            // Construct URL
            const url = `/admin/messages/${messageId}/view/`

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

                // Adding order details to modal
                messageDate.innerText = data.message_date;
                messageUser.innerText = data.message_user;
                messageName.innerText = data.message_name;
                messageEmail.innerText = data.message_email;
                messagePhone.innerText = data.message_phone;
                messageMessage.innerText = data.message_message;

                document.getElementById(`message-${messageId}`).classList.remove('fw-bold')
            })
            .catch(error => {
                console.log("Error occured. " + error)
                alert("Something went wrong! Please reload the page.")
            });
        });
    });
});