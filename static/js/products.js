document.addEventListener("DOMContentLoaded", function () {
    
    // Handling Filter Apply button
    document.getElementById("apply-filters").addEventListener("click", function () {
        let params = new URLSearchParams(window.location.search);
    
        // Preserve the 'q' parameter if it exists
        let searchQuery = params.get("q");
    
        // Reset filters in the URL (remove existing filter params)
        params.delete("sort");
        params.delete("category");
        params.delete("price");
        params.delete("rating");
    
        // Get selected sorting option
        let sortBy = document.querySelector("input[name='sortby']:checked");
        if (sortBy) {
            params.set("sort", sortBy.id);
        }
    
        // Get selected categories
        document.querySelectorAll("input[name='category']:checked").forEach(category => {
            params.append("category", category.id);
        });
    
        // Get selected price ranges
        document.querySelectorAll("input[name='price']:checked").forEach(price => {
            params.append("price", price.id);
        });
    
        // Get selected ratings
        document.querySelectorAll("input[name='rating']:checked").forEach(rating => {
            params.append("rating", rating.id);
        });
    
        // Preserve the search query if it exists
        if (searchQuery) {
            params.set("q", searchQuery);
        }
    
        // Redirect to the updated URL with applied filters
        window.location.href = window.location.pathname + "?" + params.toString();
    });

    // Get URL parameters
    const params = new URLSearchParams(window.location.search);
    if (params.toString()) {
        const selectedSorting = params.get("sort")
        const selectedPrices = params.getAll("price");
        const selectedCategories = params.getAll("category");

        // Sort radio buttons
        if (selectedSorting) {
            document.querySelectorAll("input[name='sortby']").forEach(input => {
                if (selectedSorting == input.id) {
                    input.checked = true;
                } else {
                    input.checked = false;
                }
            })
        }

        // Categories
        document.querySelectorAll("input[name='category']").forEach(input => {
            if (selectedCategories.includes(input.id)) {
                input.checked = true;
            }
        })

        // Price range
        document.querySelectorAll("input[name='price']").forEach(input => {
            if (selectedPrices.includes(input.id)) {
                input.checked = true;
            }
        });
    }

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
});
