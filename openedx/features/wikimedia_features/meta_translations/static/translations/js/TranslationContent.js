import React, { useState, useEffect, Fragment } from 'react';
import { ToastContainer } from 'react-toastify';
import Switch from "react-switch";

import Select from 'react-select';
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
  const [filterAdminCourses, setFilterAdminCourses] = useState(false);
  const [expendOutline, setExpendOutline] = useState(0);
  const [isFetched, setIsFetched] = useState(false);

  const getOptionsFromObject = (object) => {
    return Object.keys(object).map(course => ({label: object[course].title, value: object[course].id}));
  }

  useEffect(() => {
    fetchCourses(setBaseCourses, setLoading, setIsFetched, filterAdminCourses);
  }, [filterAdminCourses]);

  const handleBaseCourseChange = (option) => {
    setBaseCourse(option.value);
    setRerunCourse('');
    setCourseOutline({});
    setRerunCourses(option.value ?baseCourses[option.value].rerun : {});
  }

  const handleRerunCourseChange = (option) => {
    if(option.value) {
      setRerunCourse(option.value);
      fetchCourseOutline(option.value, setCourseOutline, setLoading);
    } else {
      setRerunCourse('');
      setCourseOutline({});
    }
  }

  const handleAdminFilterCourses = (event) => {
    setCourseOutline({});
    setRerunCourses({});
    setRerunCourses({});
    setFilterAdminCourses(!filterAdminCourses);
  }

  const renderAdminButton = () => {
    if (context.IS_ADMIN == "True") {
      return (
      <label>
        <span className="meta-translations-message">Filter My Courses</span>
        <Switch onChange={handleAdminFilterCourses} checked={filterAdminCourses} />
      </label>
      )
    }
  }

  const handleExpendOutline = () => {
    setExpendOutline((prevState) => prevState+1);
  }

  return (
    <div className="translations">
      {
        isFetched && (
          <div className="message meta-translations-message">
            {
              isEmpty(baseCourses) &&
              <p>
                No Translated Course Found!
              </p>
            }
          </div>
        )
      }
      {
        isFetched && renderAdminButton()
      }
      <div className="translation-header">
        <div className="col">
        {
          !isEmpty(baseCourses) &&
          <Select
            placeholder= "Select Base Course"
            onChange={handleBaseCourseChange}
            options={getOptionsFromObject(baseCourses)}
          />
        }
        </div>
        <div className="col">
          {
          !isEmpty(rerunCourses) &&
          <Select
            placeholder="Select Rerun Course"
            onChange={handleRerunCourseChange}
            options={getOptionsFromObject(rerunCourses)}
          />
        }
        </div>
      </div>
      {
          !isEmpty(courseOutline) && (
          <Fragment>
            <div className='translation-languages'>
              <div className='col base-block'>
                <strong>
                  {
                    baseCourses[baseCourse].language ?
                    context.LANGUAGES[baseCourses[baseCourse].language] :
                    'NA'
                  }
                </strong>
              </div>
              <div className='col translation-block'>
                <strong>
                  {
                    rerunCourses[rerunCourse].language ?
                    context.LANGUAGES[rerunCourses[rerunCourse].language] :
                    'NA'
                  }
                </strong>
                <button className='btn btn-primary btn-translations' onClick={handleExpendOutline}>
                  {!!!(expendOutline%2) && 'Expand Outline'}
                  {!!(expendOutline%2) && 'Collapse Outline'}
                </button>
              </div>
            </div>
            {
              !isEmpty(courseOutline.base_course_outline) &&
              <Sections
                  expendOutline={expendOutline}
                  context={context}
                  setLoading={setLoading}
                  rerunCourseId={rerunCourse}
                  courseOutline={courseOutline}
                  setCourseOutline={setCourseOutline}
              />
            }
            {
              isEmpty(courseOutline.base_course_outline) &&
              <p className="message">
                No Translations Found!, Please apply mapping.
              </p>
            }

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
