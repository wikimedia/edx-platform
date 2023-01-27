import React from "react";

import Subsections from "./Subsections";
import Accordion from "./Accordion";
import CourseInfoHeader from "./CourseInfoHeader";

function Sections(props) {
  const { META_DATA } = props.context
  const { base_course_info, course_info, base_course_outline, course_outline } = props.courseOutline;

  return (
    <div className="translation-frame">
      <div className="section-header">
        <div className="title">{META_DATA.course_name}</div>
      </div>
      {
        (
          <CourseInfoHeader
            addClass="sections"
            key={'course_info'}
            baseTitle={base_course_info.data.display_name}
            rerunTitle={course_info.data.display_name}
            pageUrl={base_course_info.links.page_url}
            pageGroupUrl={course_info.links.page_group_url}
            usageKey={course_info.usage_key}
            approved={course_info.status.approved}
            versionStatus={course_info.version_status}
            destinationFlag={course_info.status.destination_flag}
            isFullyTranslated={course_info.status.is_fully_translated}
            {...props}
          >
          </CourseInfoHeader>
        )
      }
      <div className="section-header">
        <div className="title">{META_DATA.outline}</div>
      </div>
      {
        Object.keys(base_course_outline)
        .map(section_id => {
          const baseTitle = base_course_outline[section_id].data.display_name;
          const rerunTitle = course_outline[section_id].data.display_name;

          return (
            <Accordion
              addClass="sections"
              key={section_id}
              baseTitle={baseTitle}
              section_id={section_id}
              rerunTitle={rerunTitle}
              pageUrl={base_course_outline[section_id].links.page_url}
              pageGroupUrl={course_outline[section_id].links.page_group_url}
              usageKey={course_outline[section_id].usage_key}
              approved={course_outline[section_id].status.approved}
              versionStatus={course_outline[section_id].version_status}
              destinationFlag={course_outline[section_id].status.destination_flag}
              isFullyTranslated={course_outline[section_id].status.is_fully_translated}
              {...props}
            >
              <Subsections
                section_id={section_id}
                baseCourseSubsections={base_course_outline[section_id].children}
                rerunCourseSubsections={course_outline[section_id].children}
                {...props}
              />
            </Accordion>
          )
        })
      }
    </div>
  );
}

export default Sections;
