import React, { Fragment } from "react";

import isEmpty from '../helpers/isEmptyObject';
import Units from './Units';
import Accordion from "./Accordion";

function Subsections (props) {

  const { baseCourseSubsections, rerunCourseSubsections } = props;

  return (
    <Fragment>
      {
        !isEmpty(baseCourseSubsections) &&
        Object.keys(baseCourseSubsections).map((subsection_id) => {
          const baseTitle = baseCourseSubsections[subsection_id].data.display_name;
          const rerunTitle = rerunCourseSubsections[subsection_id].data.display_name;

          return (
            <Accordion
              addClass="sub-sections"
              key={subsection_id}
              baseTitle={baseTitle}
              rerunTitle={rerunTitle}
              subsection_id={subsection_id}
              pageUrl={baseCourseSubsections[subsection_id].links.page_url}
              pageGroupUrl={rerunCourseSubsections[subsection_id].links.page_group_url}
              usageKey={rerunCourseSubsections[subsection_id].usage_key}
              approved={rerunCourseSubsections[subsection_id].status.approved}
              versionStatus={rerunCourseSubsections[subsection_id].version_status}
              destinationFlag={rerunCourseSubsections[subsection_id].status.destination_flag}
              isFullyTranslated={rerunCourseSubsections[subsection_id].status.is_fully_translated}
              {...props}
            >
              <Units
                key={subsection_id}
                subsection_id={subsection_id}
                baseCourseUnits={baseCourseSubsections[subsection_id].children}
                rerunCourseUnits={rerunCourseSubsections[subsection_id].children}
                rerunSubsectionKey={rerunCourseSubsections[subsection_id].usage_key}
                {...props}
              />
            </Accordion>
          )
        })
      }
    </Fragment>
  )
}

export default Subsections;
