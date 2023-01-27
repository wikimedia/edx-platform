import React from "react";
import Actions from "./Actions";

function CourseInfoHeader (props) {

  const { baseTitle, rerunTitle, addClass, rerunCourseId, destinationFlag, isFullyTranslated, versionStatus, pageUrl, pageGroupUrl} = props

  return (
    <div className={`${addClass ? addClass: ''}`}>
      <div className='header course-info-header'>
        <div className='col'>
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
          <div className="content-bar">
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
            approveAll = {false}
            setApproveAll = {()=>{}}
            is_course_info = {true}
            {...props}
          />
        </div>
      </div>
    </div>
  )
}

export default CourseInfoHeader;
