import React, {useState, useRef} from "react";

import useFetch from "../hooks/useFetch";
import Actions from "./Actions";

function Accordion (props) {

  const { baseTitle, rerunTitle, children, units, baseContent, addClass, rerunCourseId, destinationFlag } = props

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
      <div className='header' onClick={hanldeClick}>
        <div className='col'>
          <span className="fa fa-chevron-down"></span>
          <strong className='title'>{baseTitle}</strong>
        </div>
        <div className='col'>
          {
            rerunTitle && (
              <span className="fa fa-chevron-down"></span>
            )
          }
          <strong className='title'>{rerunTitle ? rerunTitle : '--'}</strong>
        </div>
        <Actions
          courseId={rerunCourseId}
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
