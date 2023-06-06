function toggleElementClass(element, class_name = "hidden") {
  if (element.classList.contains(class_name)) {
    element.classList.remove(class_name);
  } else {
    element.classList.add(class_name);
  }
}

function prerequisitsHandler() {
  var all_courses_elements = document.querySelectorAll(".all-courses");
  var follow_up_courses_elements = document.querySelectorAll(".follow-up-courses");
  all_courses_elements.forEach((element) => {
    toggleElementClass(element);
  });
  follow_up_courses_elements.forEach((element) => {
    toggleElementClass(element);
  });

  // toggle button text
  var prerequisite_btn = document.getElementById("study-next-btn");
  const class_name = "showing-follow-courses";

  if (prerequisite_btn.classList.contains(class_name)) {
    prerequisite_btn.innerText = gettext("What to study next?");
    prerequisite_btn.classList.remove(class_name);
  } else {
    prerequisite_btn.innerText = gettext("Show All Courses");
    prerequisite_btn.classList.add(class_name);
  }
}
