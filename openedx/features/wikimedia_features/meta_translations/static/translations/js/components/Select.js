import React, { useState } from 'react';

function Select ({label, courses, value, onSelectChange}) {

  const handleSelectChnage = (e) => {
    onSelectChange(e.target.value);
  }

  const options = Object.keys(courses).map(course => {
    return <option value={courses[course].id} key={courses[course].id}>{courses[course].title}</option>
  });

  return (
    <div>
      <label>{label}</label>
      <div>
        <select className="course-select" value={value} onChange={handleSelectChnage}>
          <option value=''>Select Course</option>
          { options }
        </select>
      </div>
    </div>
  )
}

export default Select;
