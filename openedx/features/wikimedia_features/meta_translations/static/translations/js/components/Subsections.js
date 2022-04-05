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
            >
              <Units
                key={subsection_id}
                subsection_id={subsection_id}
                baseCourseUnits={baseCourseSubsections[subsection_id].children}
                rerunCourseUnits={rerunCourseSubsections[subsection_id].children}
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
