console.log("TaskFlow JavaScript is connected!");


const searchInput = document.getElementById("searchInput");
const filterButtons = document.querySelectorAll(".filter-button");
const taskItems = document.querySelectorAll(".task-item");

let currentFilter = "all";


function filterTasks() {

    const searchText = searchInput
        ? searchInput.value.toLowerCase().trim()
        : "";


    taskItems.forEach(task => {

        // Get task text
        const textElement = task.querySelector(".task-text");

        const taskText = textElement
            ? textElement.textContent.toLowerCase().trim()
            : "";


        // Check whether task is completed
        const isCompleted =
            task.classList.contains("completed");


        // Check whether task is overdue
        const isOverdue =
            task.classList.contains("overdue");


        // Get priority
        const priorityBadge =
            task.querySelector(".priority-badge");

        const priority =
            priorityBadge
                ? priorityBadge.textContent.toLowerCase()
                : "";


        // -----------------------------
        // Search
        // -----------------------------

        const matchesSearch =
            taskText.includes(searchText);


        // -----------------------------
        // Filter
        // -----------------------------

        let matchesFilter = true;


        switch (currentFilter) {

            case "active":

                matchesFilter = !isCompleted;

                break;


            case "completed":

                matchesFilter = isCompleted;

                break;


            case "high":

                matchesFilter =
                    priority.includes("high");

                break;


            case "overdue":

                matchesFilter =
                    isOverdue && !isCompleted;

                break;


            case "all":

            default:

                matchesFilter = true;

                break;
        }


        // -----------------------------
        // Show / Hide
        // -----------------------------

        if (matchesSearch && matchesFilter) {

            task.style.display = "";

        } else {

            task.style.display = "none";

        }

    });

}


// -----------------------------
// Search
// -----------------------------

if (searchInput) {

    searchInput.addEventListener(
        "input",
        filterTasks
    );

}


// -----------------------------
// Filter buttons
// -----------------------------

filterButtons.forEach(button => {

    button.addEventListener(
        "click",
        function () {

            // Remove active state
            filterButtons.forEach(btn => {

                btn.classList.remove("active");

            });


            // Activate clicked button
            this.classList.add("active");


            // Get filter name
            currentFilter =
                this.dataset.filter;


            console.log(
                "Current filter:",
                currentFilter
            );


            // Apply filter
            filterTasks();

        }
    );

});

// Set progress bar width

const progressBar = document.querySelector(".progress-bar");

if (progressBar) {

    const progress =
        progressBar.dataset.progress;

    progressBar.style.width = `${progress}%`;

}