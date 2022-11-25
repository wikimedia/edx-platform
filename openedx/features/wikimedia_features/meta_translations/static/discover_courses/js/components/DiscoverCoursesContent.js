import React, { useEffect, useState } from "react";
import { ToastContainer } from 'react-toastify';
import Select from 'react-select';
import { useHistory } from "react-router-dom";
import useFetch from '../hooks/useFetch';
import Spinner from '../assets/spinner';

function DiscoverCoursesContent({ context }) {
  const history = useHistory();
  const { LANGUAGES } = context
  const { fetchCourses } = useFetch(context)
  const [all_courses, setAllCourses] = useState([]);
  const [courses, setCourses] = useState([]);
  const [searchCourse, setSearchCourse] = useState('');
  const [fromLanguge, setFromLanguage] = useState({ label: 'all', value: '' });
  const [toLanguge, setToLanguage] = useState({ label: 'all', value: '' });
  const [loading, setLoading] = useState(true);

  const handleCourseSelect = (course_id) => {
    history.push(`/meta_translations/discover_courses/${course_id}`);
  }

  useEffect(() => {
    fetchCourses(setCourses, setAllCourses, setLoading)
  }, []);

  const isFilteredCourse = (course) => {
    return (
      (toLanguge.value == '' || toLanguge.value == course.course_lang) &&
      (fromLanguge.value == '' || fromLanguge.value == course.base_course_lang) &&
      (searchCourse == '' || course.base_course_name.toLowerCase().startsWith(searchCourse.toLowerCase()))
    )
  }

  useEffect(() => {
    setCourses(all_courses.filter(course => isFilteredCourse(course)));
  }, [searchCourse, fromLanguge, toLanguge]);

  return (
    <div className="discover-courses">
      {
        !loading && (
          <div className="content">
            <div className="grid-block">
              <div className="grid-header">
                <input
                  type="text"
                  placeholder="Search Course by Name"
                  value={searchCourse}
                  onChange={(e) => setSearchCourse(e.target.value)}
                  className="search-course-field"
                />
              </div>
              <div className="grid">
                <table className="grid-courses">
                  <thead>
                    <tr>
                      <th>Course Name</th>
                      <th>Translated Course Name</th>
                      <th>From Language</th>
                      <th>To Language</th>
                    </tr>
                  </thead>
                  <tbody>
                    {
                      courses.map((val) => {
                        return (
                          <tr key={val.course_id} onClick={() => handleCourseSelect(val.course_id)}>
                            <td>{val.base_course_name}</td>
                            <td>{val.course_name}</td>
                            <td>{LANGUAGES[val.base_course_lang]}</td>
                            <td>{LANGUAGES[val.course_lang]}</td>
                          </tr>
                        )
                      })
                    }
                  </tbody>
                </table>
                {
                  !courses.length && (
                    <span>No course found</span>
                  )
                }
              </div>
            </div>
            <div className="filter-block">
              <div className="filter-header">
                <span className="title">Filters</span>
              </div>
              <div className="filter-field multi-selector">
                <label className="title">From Language</label>
                <Select
                  className="options"
                  value={fromLanguge}
                  onChange={setFromLanguage}
                  options={[
                    {
                      label: 'Languages',
                      options: [
                        { value: '', label: 'all' },
                        ...Object.keys(LANGUAGES).map(key => { return { label: LANGUAGES[key], value: key } }),
                      ],
                    },
                  ]}
                />
              </div>
              <div className="filter-field multi-selector">
                <label className="title">To Language</label>
                <Select
                  className="options"
                  value={toLanguge}
                  onChange={setToLanguage}
                  options={[
                    {
                      label: 'Languages',
                      options: [
                        { value: '', label: 'all' },
                        ...Object.keys(LANGUAGES).map(key => { return { label: LANGUAGES[key], value: key } }),
                      ],
                    },
                  ]}
                />
              </div>
            </div>
          </div>
        )
      }
      {
        loading && (
          <Spinner center_in_screen />
        )
      }
      <ToastContainer />
    </div>
  )
}

export default DiscoverCoursesContent;
