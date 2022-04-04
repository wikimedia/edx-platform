import React, { Fragment, useRef, useState } from "react";

import isEmpty from '../helpers/isEmptyObject';
import Accordion from "./Accordion";
import Unit from "./Unit";

function Units (props) {

  const { baseCourseUnits, rerunCourseUnits } = props;

  return (
    <Fragment>
      {
        !isEmpty(baseCourseUnits) &&
        Object.keys(baseCourseUnits).map((unit_id) => {
          const baseTitle = baseCourseUnits[unit_id].data.display_name;
          const rerunTitle = rerunCourseUnits[unit_id].data.display_name;
          const baseCourseUnitKey = baseCourseUnits[unit_id].usage_key;
          const rerunCourseUnitKey = rerunCourseUnits[unit_id].usage_key;

          return (
            <Accordion
              addClass="units"
              key={unit_id}
              unit_id={unit_id}
              baseTitle={baseTitle}
              rerunTitle={rerunTitle}
              units={true}
              baseContent={baseCourseUnits[unit_id].units}
              baseCourseUnitKey={baseCourseUnitKey}
              rerunCourseUnitKey={rerunCourseUnitKey}
              {...props}
            >
              {
                baseCourseUnits[unit_id].units && (
                  <Unit
                    key={unit_id}
                    unit_id={unit_id}
                    baseContent={baseCourseUnits[unit_id].units}
                    rerunContent={rerunCourseUnits[unit_id].units}
                    {...props}
                  />
                )
              }
            </Accordion>
          )
        })
      }
    </Fragment>
  )
}

export default Units;
