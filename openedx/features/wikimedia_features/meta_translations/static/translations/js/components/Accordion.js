import React, {useState, useRef} from "react";

import useFetch from "../hooks/useFetch";
import Actions from "./Actions";

function Accordion (props) {

  const { baseTitle, rerunTitle, children, units, baseContent, addClass, rerunCourseId, destinationFlag, versionStatus } = props

  const [isCollapsed, setCollapsed] = useState(true);
  const ref = useRef();
  const slide = $(ref.current);

  const { fetchCourseUnit } = useFetch(context);

  const hanldeClick = () => {
    if (units && !baseContent) {
      fetchCourseUnit({...props, showSlide});
    } else {
      setCollapsed(!isCollapsed);
      !isCollapsed ? slide.slideUp() : slide.slideDown()
    }
  }

  const showSlide = () => {
    slide.slideDown();
    setCollapsed(false);
  }

  return (
    <div className={`${addClass ? addClass: ''} ${isCollapsed ? 'collapsed': ''}`}>
      <div className='header'>
        <div className='col' onClick={hanldeClick}>
          <span className="fa fa-chevron-down"></span>
          <strong className='title'>{baseTitle}</strong>
        </div>
        <div className='col' onClick={hanldeClick}>
          {
            rerunTitle && (
              <span className="fa fa-chevron-down"></span>
            )
          }
          <strong className='title'>{rerunTitle ? rerunTitle : '--'}</strong>
        </div>
        <Actions
          courseId={rerunCourseId}
          versionStatus={versionStatus}
          destinationFlag={destinationFlag}
          enableApproveButton={(
            destinationFlag &&
            rerunTitle != ''
          )}
          {...props}
        />
      </div>
      <div className="body" ref={ref}>
      { children }
      </div>
    </div>
  )
}

export default Accordion;
