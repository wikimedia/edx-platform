import React from "react";
import ReactHtmlParser from 'react-html-parser';

import isEmpty from '../helpers/isEmptyObject';
import Actions from "./Actions";

function Unit (props) {

  const {baseContent, rerunContent, rerunCourseId} = props;

  const isValidTranslations = (data) => {
    if (data.transcript) {
      return data.display_name !='' && data.transcript != []
    }
    return data.display_name != '' && data.content != ''
  }

  const content = (data) => {
    if (data.transcript) {
      return (
        <ul>
          { data.transcript.map((trans, index) => <li key={index}>{trans}</li>) }
        </ul>
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

        return (
          <div className='translation-content' key={content_id}>
            <div className='translation-title'>
              <div className='col'>
                <strong>{baseContent[content_id].data.display_name}</strong>
              </div>
              <div className='col'>
                <strong>{rerunContent[content_id].data.display_name}</strong>
              </div>
              <Actions
                usageKey={rerunContent[content_id].usage_key}
                courseId={rerunCourseId}
                approved={rerunContent[content_id].status.approved}
                content_id={content_id}
                enableApproveButton={(
                    rerunContent[content_id].status.destination_flag &&
                    isValidTranslations(rerunContent[content_id].data)
                  )}
                {...props}
              />
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
