function toggleElementVisibility(element){
    if (element.classList.contains("hidden")){
        element.classList.remove("hidden")
    } else {
        element.classList.add("hidden")
    }
}

function prerequisitsHandler() {
    var all_courses_elements = document.querySelectorAll('.all-courses');
    var follow_up_courses_elements = document.querySelectorAll('.follow-up-courses');    
    all_courses_elements.forEach( element => {
        toggleElementVisibility(element)
    })
    follow_up_courses_elements.forEach( element => {
        toggleElementVisibility(element)
    })

    // toggle button text
    var prerequisite_btn = document.getElementById('study-next-btn');

    if (prerequisite_btn.innerText === 'Show All Courses'){
        prerequisite_btn.innerText = 'What to study next?'
    } else {
        prerequisite_btn.innerText = 'Show All Courses'
    }
}