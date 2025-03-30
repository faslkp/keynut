
document.addEventListener("DOMContentLoaded", function () {

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
            } else if (this.href.includes("type")) {
                paramName = "type";
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
            document.getElementById('orderDetailsModalLabel').innerText = "Order Details"

            // Getting order details fields
            const orderIdSpan = document.querySelector('.order-id');
            const orderDateSpan = document.querySelector('.order-date');
            const orderAddressSpan = document.querySelector('.delivery-address');
            const orderSubTotalSpan = document.querySelector('.subtotal');
            const orderTotalSpan = document.querySelector('.order-total');
            const orderItemsSpan = document.querySelector('.order-items-table');
            const paymentsSpan = document.querySelector('.payments-table');
            const orderStatusSpan = document.querySelector('.order-status');

            // Clear existing values
            orderIdSpan.innerText = "";
            orderDateSpan.innerText = "";
            orderAddressSpan.innerText = "";
            orderStatusSpan.innerText = "";
            orderSubTotalSpan.innerText = "";
            orderTotalSpan.innerText = "";
            orderItemsSpan.innerHTML = "";
            paymentsSpan.innerHTML = "";
            

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

                // Adding order details to modal
                orderIdSpan.innerText = data.order_id
                orderDateSpan.innerText = data.order_date.split("T")[0]
                orderStatusSpan.innerText = data.status
                orderSubTotalSpan.innerText = `₹${parseFloat(data.total_amount).toFixed(2)}`
                orderTotalSpan.innerText = `₹${parseFloat(data.total_amount).toFixed(2)}`

                orderAddressSpan.innerText = `${data.address.name}, ${data.address.address_line_1}, ${data.address.address_line_2}, ${data.address.city}, ${data.address.state}, ${data.address.pin}, ${data.address.phone}, `
                
                data.status_choices.forEach(choice => {
                    if (choice[0] == data.status) {
                        orderStatusSpan.innerText = choice[1]
                    }
                });

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
                
                data.payments.forEach(payment => {
                    const newPaymentRow = document.createElement("tr");
                    newPaymentRow.innerHTML = `
                        <td class="py-2 px-3">${payment.payment_date.replace('T', ' ').split('.')[0]}</td>
                        <td class="py-2 px-3">₹${parseFloat(payment.amount).toFixed(2)}</td>
                        <td class="py-2 px-3">${payment.payment_method}<br>(${payment.payment_status})</td>
                        <td class="py-2 px-3">${payment.transaction_id}</td>
                    `;

                    // Append the new row to the tbody
                    paymentsSpan.appendChild(newPaymentRow);
                })
            })
            .catch(error => {
                console.log("Error occured. " + error)
                alert("Something went wrong! Please reload the page.")
            });
        });
    });
});