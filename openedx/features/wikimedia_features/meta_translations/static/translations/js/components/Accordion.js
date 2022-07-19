import React, {useState, useRef, useEffect} from "react";

import useFetch from "../hooks/useFetch";
import Actions from "./Actions";

function Accordion (props) {

  const { baseTitle, rerunTitle, children, units, baseContent, addClass, rerunCourseId, destinationFlag, isFullyTranslated,  versionStatus, expendOutline, pageUrl, pageGroupUrl} = props

  const [isCollapsed, setCollapsed] = useState(true);
  const [approveAll, setApproveAll] = useState(false);
  const ref = useRef();
  const slide = $(ref.current);

  const { fetchCourseUnit } = useFetch(context);

  const hanldeClick = () => {
    if (units && !baseContent) {
      fetchCourseUnit({...props, showSlide, setApproveAll});
    } else {
      setCollapsed(!isCollapsed);
      !isCollapsed ? slide.slideUp() : slide.slideDown()
    }
  }

  const showSlide = () => {
    slide.slideDown();
    setCollapsed(false);
  }

  useEffect(()=>{
    if (!units){
      const isExpended = !!(expendOutline % 2)
      if ((isExpended && isCollapsed) || (!isExpended && !isCollapsed)){
        setCollapsed(!isExpended)
        !isCollapsed ? slide.slideUp() : slide.slideDown()
      }
    } else {
      setCollapsed(true)
      slide.slideUp()
    }
  },[expendOutline])

  return (
    <div className={`${addClass ? addClass: ''} ${isCollapsed ? 'collapsed': ''}`}>
      <div className='header'>
        <div className='col' onClick={hanldeClick}>
          <span className="fa fa-chevron-down"></span>
          <strong className='title'>{baseTitle}</strong>
          {
            pageUrl && (
              <a className="btn" href={pageUrl} title='wiki content' target="_blank">
                <i className="fa fa-external-link"></i>
              </a>
            )
          }
        </div>
        <div className='col content-actions'>
          <div className="content-bar" onClick={hanldeClick}>
            <span className="fa fa-chevron-down"></span>
            <strong className='title'>{rerunTitle ? rerunTitle : '--'}</strong>
            {
              pageGroupUrl && (
                <a className="btn" href={pageGroupUrl} title='wiki translation' target="_blank">
                  <i className="fa fa-external-link"></i>
                </a>
              )
            }
          </div>
          <Actions
            courseId={rerunCourseId}
            versionStatus={versionStatus}
            destinationFlag={destinationFlag}
            enableApproveButton={(
              destinationFlag &&
              isFullyTranslated
            )}
            approveAll = {approveAll}
            setApproveAll = {setApproveAll}
            {...props}
          />
        </div>
      </div>
      <div className="body" ref={ref}>
      { children }
      </div>
    </div>
  )
}

export default Accordion;
