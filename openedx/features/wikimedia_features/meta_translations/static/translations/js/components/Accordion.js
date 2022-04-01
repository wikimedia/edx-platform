import React, {useState, useRef} from "react";
import useFetch from "../hooks/useFetch";

function Accordion (props) {

  const { baseTitle, rerunTitle, children, units, baseContent, addClass } = props

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
          <span className="fa fa-chevron-down"></span>
          <strong className='title'>{rerunTitle}</strong>
        </div>
      </div>
      <div className="body" ref={ref}>
      { children }
      </div>
    </div>
  )
}

export default Accordion;
