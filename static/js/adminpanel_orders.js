
document.addEventListener("DOMContentLoaded", function () {
    
    // Update order status
    document.querySelectorAll(".update-status-btn").forEach(button => {
        button.addEventListener("click", function () {
            let orderId = this.getAttribute("data-order-id");
            let newStatus = document.getElementById(`status-${orderId}`).value;
            let csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content'); // Get CSRF token

            // Get the feedback modal elements
            const feedbackModalTrigger = document.getElementById('triggerFeedbackModal');
            const feedbackModalLabel = document.getElementById('feedbackModalLabel');
            const feedbackModalDesc = document.getElementById('feedbackModalDesc');
            feedbackModalLabel.innerText = "";
            feedbackModalDesc.innerText = "";

            fetch("/admin/orders/update-status/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken // Include CSRF token
                },
                body: JSON.stringify({
                    order_id: orderId, 
                    status: newStatus 
                })
            })
            .then(response => response.json())
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

    // View order event listeners 
    document.querySelectorAll(".btn-view-order").forEach(button => {
        button.addEventListener("click", function (event) {
            // Setting up Update Status button and disabling to wait for fetching product data
            const updateStatusButton = document.getElementById('updateStatusButton');
            const newButton = updateStatusButton.cloneNode(true); // Clone the button (without event listeners)
            updateStatusButton.parentNode.replaceChild(newButton, updateStatusButton); // Replace old button
            newButton.disabled = true;
            newButton.innerText = "Please wait"
            document.getElementById('orderDetailsModalLabel').innerText = "Order Details"

            // Getting order details fields
            const orderIdSpan = document.querySelector('.order-id');
            const orderDateSpan = document.querySelector('.order-date');
            const orderPaymentSpan = document.querySelector('.payment-method');
            const orderAddressSpan = document.querySelector('.delivery-address');
            const orderSubTotalSpan = document.querySelector('.subtotal');
            const orderTotalSpan = document.querySelector('.order-total');
            const orderItemsSpan = document.querySelector('.order-items-table');
            const statusChoicesSpan = document.querySelector('.order-status-dropdown')
            statusChoicesSpan.innerHTML = `<option value="" selected disabled><span class="order-status"></span></option>`
            const orderStatusSpan = document.querySelector('.order-status');

            // Clear existing values
            orderIdSpan.innerText = "";
            orderDateSpan.innerText = "";
            orderPaymentSpan.innerText = "";
            orderAddressSpan.innerText = "";
            orderStatusSpan.innerText = "";
            orderSubTotalSpan.innerText = "";
            orderTotalSpan.innerText = "";
            orderItemsSpan.innerHTML = "";
            

            // Get userID
            const orderId = this.dataset.orderId

            // Construct URL
            const url = `/admin/orders/${orderId}/view/`

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

                console.log(data)

                // Adding order details to modal
                orderIdSpan.innerText = data.order_id
                orderDateSpan.innerText = data.order_date.split("T")[0]
                orderStatusSpan.innerText = data.status
                orderSubTotalSpan.innerText = `₹${parseFloat(data.total_amount).toFixed(2)}`
                orderTotalSpan.innerText = `₹${parseFloat(data.total_amount).toFixed(2)}`

                orderAddressSpan.innerText = `${data.address.name}, ${data.address.address_line_1}, ${data.address.address_line_2}, ${data.address.city}, ${data.address.state}, ${data.address.pin}, ${data.address.phone}, `
                
                // const orderItems = JSON.parse(data.order_items)
                data.order_items.forEach(item => {
                    
                    // Create a new table row
                    const newRow = document.createElement("tr");
                    newRow.innerHTML = `
                        <td class="py-2 px-3">${item.product__name} - ${item.variant} ${item.product__unit}</td>
                        <td class="py-2 px-3">₹${item.product__price}</td>
                        <td class="py-2 px-3">${item.quantity}</td>
                        <td class="py-2 px-3">₹${parseFloat(item.total_amount).toFixed(2)}</td>
                    `;

                    // Append the new row to the tbody
                    orderItemsSpan.appendChild(newRow);
                });

                data.status_choices.forEach(choice => {
                    const option = document.createElement("option"); // Create an <option> element
                    option.value = choice[0]; // Set value
                    option.textContent = choice[1]; // Set display text
                    statusChoicesSpan.appendChild(option); // Append it to <select>
                });

                newButton.dataset.orderId = data.id
                newButton.dataset.orderStatus = data.status

                newButton.disabled = false;
                newButton.innerText = "Update Status"

                // Attaching new event listener to the Update Status button
                newButton.addEventListener('click', function (event) {

                    event.preventDefault();

                    // Disable button to avoid duplicate requests
                    this.disabled = true;
                    this.innerText = "Please wait";

                    let orderId = this.getAttribute("data-order-id");
                    let newStatus = document.getElementById("order-status-dropdown").value;
                    let csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

                    // Ajax request to edit product details
                    fetch("/admin/orders/update-status/", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                            "X-CSRFToken": csrfToken // Include CSRF token
                        },
                        body: JSON.stringify({
                            order_id: orderId, 
                            status: newStatus 
                        })
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            const button = this;
                            button.innerText = "Status updated"
                            button.classList.remove('btn-danger')
                            button.classList.add('btn-success')
                            setTimeout(() => {
                                button.innerText = "Update Status"; // Revert back after 1 seconds
                                button.disabled = false
                                button.classList.remove('btn-success')
                                button.classList.add('btn-danger')
                            }, 2000);
                        } else {
                            alert(data.message)
                        }
                    })
                    .catch(error => console.error("Error:", error));
                });
            })
            .catch(error => {
                console.log("Error occured.")
                alert("Something went wrong! Please reload the page.")
            });
        });
    });
});