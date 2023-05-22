/* global gettext */
/* eslint react/no-array-index-key: 0 */

import PropTypes from 'prop-types';
import React, { useState, useEffect } from 'react';
import Select from 'react-select';
import ReactDOM from 'react-dom';

export function WikiCourseListing(props) {
  const allowReruns = props.allowReruns;
  const linkClass = props.linkClass;
  const idBase = props.idBase;
  const filterOptions = props.studio_filter_options;
  const [courses, setCourses] = useState([]);
  const [searchCourse, setSearchCourse] = useState('');
  const [organization, setOrganization] = useState({ label: 'all', value: '' });
  const [language, setLanguage] = useState({ label: 'all', value: '' });
  const [enrollment, setEnrollment] = useState({ label: 'all', value: '' });
  const [coursePaced, setCoursePaced] = useState({ label: 'all', value: '' });

  const isFilteredCourse = (course) => {
    return (
      (language.value == '' || language.value == course.language) &&
      (organization.value == '' || organization.value == course.org) &&
      (enrollment.value == '' || enrollment.value == course.enrollment_type) &&
      (coursePaced.value == '' || coursePaced.value == course.paced_type) &&
      (searchCourse == '' || course.display_name.toLowerCase().startsWith(searchCourse.toLowerCase()))
    )
  }

  useEffect(() => {
    setCourses(props.items.filter(course => isFilteredCourse(course)));
  }, [searchCourse, organization, language, enrollment, coursePaced]);

  return (
    <ul className="list-courses">
      <div className="grid-header">
        <input
          type="text"
          placeholder={gettext("Search Course by Name")}
          value={searchCourse}
          onChange={(e) => setSearchCourse(e.target.value)}
          className="search-course-field"
        />
      </div>
      <div className='studio-filters'>
        <div className="filter-field multi-selector">
          <label className="title">{filterOptions.org.name}</label>
          <Select
            className="options"
            value={organization}
            onChange={setOrganization}
            options={[
              {
                label: `${filterOptions.org.name}`,
                options: [
                  { value: '', label: 'all' },
                  ...Object.keys(filterOptions.org.terms).map(key => { return { label: filterOptions.org.terms[key], value: key } }),
                ],
              },
            ]}
          />
        </div>
        <div className="filter-field multi-selector">
          <label className="title">{filterOptions.language.name}</label>
          <Select
            className="options"
            value={language}
            onChange={setLanguage}
            options={[
              {
                label: `${filterOptions.language.name}`,
                options: [
                  { value: '', label: 'all' },
                  ...Object.keys(filterOptions.language.terms).map(key => { return { label: filterOptions.language.terms[key], value: key } }),
                ],
              },
            ]}
          />
        </div>
        <div className="filter-field multi-selector">
          <label className="title">{filterOptions.enrollment.name}</label>
          <Select
            className="options"
            value={enrollment}
            onChange={setEnrollment}
            options={[
              {
                label: `${filterOptions.enrollment.name}`,
                options: [
                  { value: '', label: 'all' },
                  ...Object.keys(filterOptions.enrollment.terms).map(key => { return { label: filterOptions.enrollment.terms[key], value: key } }),
                ],
              },
            ]}
          />
        </div>
        <div className="filter-field multi-selector">
          <label className="title">{filterOptions.course_paced.name}</label>
          <Select
            className="options"
            value={coursePaced}
            onChange={setCoursePaced}
            options={[
              {
                label: `${filterOptions.course_paced.name}`,
                options: [
                  { value: '', label: 'all' },
                  ...Object.keys(filterOptions.course_paced.terms).map(key => { return { label: filterOptions.course_paced.terms[key], value: key } }),
                ],
              },
            ]}
          />
        </div>
      </div>
      {
        courses.map((item, i) =>
          (
            <li key={i} className="course-item" data-course-key={item.course_key}>
              <a className={linkClass} href={item.url}>
                <h3 className="course-title" id={`title-${idBase}-${i}`}>{item.display_name}</h3>
                <div className="course-metadata">
                  <span className="course-org metadata-item">
                    <span className="label">{gettext('Organization:')}</span>
                    <span className="value">{item.org}</span>
                  </span>
                  <span className="course-num metadata-item">
                    <span className="label">{gettext('Course Number:')}</span>
                    <span className="value">{item.number}</span>
                  </span>
                  { item.run &&
                  <span className="course-run metadata-item">
                    <span className="label">{gettext('Course Run:')}</span>
                    <span className="value">{item.run}</span>
                  </span>
                  }
                  { item.can_edit === false &&
                  <span className="extra-metadata">{gettext('(Read-only)')}</span>
                  }
                </div>
              </a>
              { item.lms_link && item.rerun_link &&
              <ul className="item-actions course-actions">
                { item.translation_info &&
                  <div className='course-badge'>
                    <span className="badge badge-fit badge-info" title={`${item.translation_info}`}>
                      {item.translation_info}
                    </span>
                  </div>
                }
                { allowReruns &&
                <li className="action action-rerun">
                  <a
                    href={item.rerun_link}
                    className="button rerun-button"
                    aria-labelledby={`re-run-${idBase}-${i} title-${idBase}-${i}`}
                    id={`re-run-${idBase}-${i}`}
                  >{gettext('Re-run Course')}</a>
                </li>
                }
                <li className="action action-view">
                  <a
                    href={item.lms_link}
                    rel="external"
                    className="button view-button"
                    aria-labelledby={`view-live-${idBase}-${i} title-${idBase}-${i}`}
                    id={`view-live-${idBase}-${i}`}
                  >{gettext('View Live')}</a>
                </li>
              </ul>
              }
            </li>
          ),
        )
      }
    </ul>
  );
}

WikiCourseListing.propTypes = {
  allowReruns: PropTypes.bool.isRequired,
  idBase: PropTypes.string.isRequired,
  items: PropTypes.arrayOf(PropTypes.object).isRequired,
  linkClass: PropTypes.string.isRequired,
  studio_filter_options: PropTypes.object.isRequired,
};
