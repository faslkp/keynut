document.addEventListener('DOMContentLoaded', function () {

    // Check the active navbar link and apply it on page load
    const navLinks = document.querySelectorAll('.navbar-nav .nav-link')
    const currentUrl = window.location.pathname
    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentUrl) {
            link.classList.add('active');
        }
    });


    // Handling wishlist button on product card
    const wishlistButtons = document.querySelectorAll('.wish-badge-icon');
    
    if (wishlistButtons.length === 0) {
        return; // Exit if there are no wishlist buttons on the page
    }

    async function toggleWishlist(productId, csrftoken) {
        const url = `/wishlist/${productId}/toggle/`;

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken,
                },
            });

            const data = await response.json();

            if (response.ok) {
                if (window.location.pathname === '/wishlist/') {
                    window.location.reload(); // Reload only on wishlist page
                } else {
                    const icon = document.getElementById(`wishlist-icon-${productId}`);
                    icon.classList.toggle('bi-heart-fill');
                    icon.classList.toggle('bi-heart');
                    icon.classList.toggle('text-danger');
                }
            } else {
                alert(data.error || 'Something went wrong');
            }
        } catch (error) {
            console.error('Error:', error);
        }
    }

    wishlistButtons.forEach(button => {
        button.addEventListener('click', function () {
            const productId = this.dataset.productId;
            const csrftoken = this.dataset.csrfToken;
            toggleWishlist(productId, csrftoken);
        });
    });

    // Add to cart button on product card
    const addToCartButtons = document.querySelectorAll('.add-to-cart');
    
    if (addToCartButtons.length === 0) {
        return; // Exit if there are no wishlist buttons on the page
    }

    async function addToCart(productId, csrftoken, button) {
        const url = `/cart/${productId}/add/`;

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken,
                },
            });

            const data = await response.json();

            if (data.success) {
                button.innerText = 'Added to cart ✅';

                // Store original styles before changing
                if (!button.dataset.originalBg) {
                    button.dataset.originalBg = button.style.backgroundColor;
                    button.dataset.originalBorder = button.style.border;
                }

                // Change to success color
                button.style.backgroundColor = 'rgb(25, 135, 84)'; // Success background
                button.style.border = '3px solid rgba(25, 135, 84, 1)'; // Success border

                // Revert back after 10 seconds
                setTimeout(() => {
                    button.style.backgroundColor = button.dataset.originalBg; // Restore original background
                    button.style.border = button.dataset.originalBorder; // Restore original border
                    button.innerText = 'Add to cart'; // Reset text if needed
                }, 3000);
            } else {
                alert(data.message || 'Something went wrong');
            }
        } catch (error) {
            console.error('Error:', error);
        }
    }

    addToCartButtons.forEach(button => {
        button.addEventListener('click', function () {
            console.log('adding to cart button');
            
            const productId = this.dataset.productId;
            const csrftoken = this.dataset.csrfToken;
            addToCart(productId, csrftoken, this);
        });
    });
});
