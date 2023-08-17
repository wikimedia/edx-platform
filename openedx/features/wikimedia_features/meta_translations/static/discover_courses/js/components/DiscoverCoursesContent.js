import React, { useEffect, useState } from "react";
import { ToastContainer } from 'react-toastify';
import Select from 'react-select';
import { useHistory } from "react-router-dom";
import useFetch from '../hooks/useFetch';
import Spinner from '../assets/spinner';

function DiscoverCoursesContent({ context }) {
  const history = useHistory();
  const { LANGUAGES, META_DATA } = context
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
      (searchCourse == '' || course.base_course_name.toLowerCase().includes(searchCourse.toLowerCase()))
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
              <h1 className="page-title">{META_DATA.courses_available_for_translation}</h1>
              <div className="grid-header">
                <input
                  type="text"
                  placeholder={META_DATA.serch_course_by_name}
                  value={searchCourse}
                  onChange={(e) => setSearchCourse(e.target.value)}
                  className="search-course-field"
                />
              </div>
              <div className="grid">
                <table className="grid-courses">
                  <thead>
                    <tr>
                      <th>{META_DATA.course_name}</th>
                      <th>{META_DATA.translated_course_name}</th>
                      <th>{META_DATA.from_lang}</th>
                      <th>{META_DATA.to_lang}</th>
                      <th>{META_DATA.translated}</th>
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
                            <td>{`${val.blocks_count ? Math.round((val.blocks_translated/val.blocks_count)*100) : 0}%`}</td>
                          </tr>
                        )
                      })
                    }
                  </tbody>
                </table>
                {
                  !courses.length && (
                    <span>{META_DATA.info.courses_not_found}</span>
                  )
                }
              </div>
            </div>
            <div className="filter-block">
              <div className="filter-header">
                <span className="title">{META_DATA.filters}</span>
              </div>
              <div className="filter-field multi-selector">
                <label className="title">{META_DATA.from_lang}</label>
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
                <label className="title">{META_DATA.to_lang}</label>
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
