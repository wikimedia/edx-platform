import React from "react";
import ReactHtmlParser from 'react-html-parser';

import isEmpty from '../helpers/isEmptyObject';
import Actions from "./Actions";

function Unit (props) {

  const {baseContent, rerunContent, rerunCourseId} = props;

  const content = (data) => {
    if (data.transcript && typeof data.transcript === 'object') {
      return (
        <ol>
          { Object.entries(data.transcript).map(item => <li key={item[0]}>{item[1] ? item[1] : '--'}</li>) }
        </ol>
      )
    }
    else if (data.content && typeof data.content === 'object') {
      return (
        <ol>
          { Object.entries(data.content).map(item => <li key={item[0]}>{item[1] ? item[1] : '--'}</li>) }
        </ol>
      );
    } else {
      return (ReactHtmlParser(data.content))
    }
  }
  return (
    <div>
    {
      !isEmpty(baseContent) &&
      Object.keys(baseContent).map((content_id) => {
        const pageUrl = baseContent[content_id].links.page_url;
        const pageGroupUrl = rerunContent[content_id].links.page_group_url;
        return (
          <div className='translation-content' key={content_id}>
            <div className='translation-title'>
              <div className='col'>
                <strong>{baseContent[content_id].data.display_name}</strong>
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
                  <strong>{rerunContent[content_id].data.display_name ? rerunContent[content_id].data.display_name: '--'}</strong>
                  {
                    pageGroupUrl && (
                      <a className="btn" href={pageGroupUrl} title='wiki translation' target="_blank">
                        <i className="fa fa-external-link"></i>
                      </a>
                    )
                  }
                </div>
                <Actions
                  usageKey={rerunContent[content_id].usage_key}
                  courseId={rerunCourseId}
                  approved={rerunContent[content_id].status.approved}
                  versionStatus={rerunContent[content_id].version_status}
                  content_id={content_id}
                  destinationFlag={rerunContent[content_id].status.destination_flag}
                  isFullyTranslated={rerunContent[content_id].status.is_fully_translated}
                  enableApproveButton={(
                      rerunContent[content_id].status.destination_flag &&
                      rerunContent[content_id].status.is_fully_translated
                    )}
                  {...props}
                />
              </div>
            </div>
            <div className='translation-body'>
              <div className='col'>
                { content(baseContent[content_id].data) }
              </div>
              <div className='col'>
                { content(rerunContent[content_id].data) }
              </div>
            </div>
          </div>
          )
      })

    }
    </div>
  )
}

export default Unit;
