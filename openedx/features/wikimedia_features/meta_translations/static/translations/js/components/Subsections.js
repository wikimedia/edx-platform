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
              usageKey={rerunCourseSubsections[subsection_id].usage_key}
              approved={rerunCourseSubsections[subsection_id].status.approved}
              destinationFlag={rerunCourseSubsections[subsection_id].status.destination_flag}
              approveAll={true}
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
