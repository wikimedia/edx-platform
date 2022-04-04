import React, { useState, useEffect, Fragment } from 'react';
import { ToastContainer } from 'react-toastify';

import Select from "./components/Select";
import useFetch from "./hooks/useFetch";
import Spinner from './assets/spinner';
import isEmpty from './helpers/isEmptyObject';
import Sections from './components/Sections';

function TranslationContent({ context }) {
  const [baseCourses, setBaseCourses] = useState({});
  const [rerunCourses, setRerunCourses] = useState({});
  const [baseCourse, setBaseCourse] = useState('');
  const [rerunCourse, setRerunCourse] = useState('');
  const [courseOutline, setCourseOutline] = useState({});
  const [isLoading, setLoading] = useState(true);
  const { fetchCourses, fetchCourseOutline } = useFetch(context);

  useEffect(() => {
    fetchCourses(setBaseCourses, setLoading);
  }, []);

  const handleBaseCourseChange = (value) => {
    setBaseCourse(value);
    setRerunCourse('');
    setCourseOutline({});
    setRerunCourses(value ? baseCourses[value].rerun : []);
  }

  const handleRerunCourseChange = (value) => {
    if(value) {
      setRerunCourse(value);
      fetchCourseOutline(value, setCourseOutline, setLoading);
    } else {
      setRerunCourse({});
      setCourseOutline({});
    }
  }

  return (
    <div className="translations">
      <div className="translation-header">
        <div className="col">
        {
          !isEmpty(baseCourses) &&
          <Select
          label="Select Base Course"
            value={baseCourse}
            courses={baseCourses}
            onSelectChange={handleBaseCourseChange}
          />
        }
        </div>
        <div className="col">
          {
          !isEmpty(rerunCourses) &&
          <Select
            label="Select Rerun Course"
            value={rerunCourse}
            courses={rerunCourses}
            onSelectChange={handleRerunCourseChange}
          />
        }
        </div>
      </div>
      {
          !isEmpty(courseOutline) && (
          <Fragment>
            <div className='translation-languages'>
              <div className='col'>
                <strong>
                  {
                    courseOutline.base_course_lang ?
                    context.LANGUAGES[courseOutline.base_course_lang]:
                    'English'
                  }
                </strong>
              </div>
              <div className='col'>
                <strong>
                  {
                    context.LANGUAGES[courseOutline.course_lang]
                  }
                </strong>
              </div>
            </div>
            <Sections
              context={context}
              setLoading={setLoading}
              courseOutline={courseOutline}
              setCourseOutline={setCourseOutline}
            />
          </Fragment>
        )
      }
      {
        isLoading && (
          <Spinner center_in_screen />
        )
      }
      <ToastContainer />
    </div>
  )
}

export default TranslationContent;
