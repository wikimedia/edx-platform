import React from 'react';
import useUpdate from '../hooks/useUpdate';

function Actions (props) {

  const { approved, approveAll, enableApproveButton, context } = props;

  const { approveCourseOutline, approveRecursiveCourseOutline } = useUpdate(context);

  const title = !enableApproveButton? 'No Translations': approved? 'Approved': 'Approve'
  
  const hanldeApprove = (e) => {
    e.stopPropagation();
    if (!approved && enableApproveButton){
        const options = {
          approved: true
        }
        approveCourseOutline({options, ...props});
    }
  }

  const hanldeApproveAll = (e) => {
    e.stopPropagation();
    const options = {
      approved: true,
      apply_all: true
    }
    approveRecursiveCourseOutline({options, ...props});
  }
  return (
    <div className="btn-box">
      {
        approveAll && (
          <span className="btn approveAll" title="Approve All" onClick={hanldeApproveAll}>
            <i className="fa fa-list" aria-hidden="true"></i>
          </span>
        )
      }
      {
        <span className={`btn ${!enableApproveButton? 'disabled': approved? 'approved': ''}`} title={title} onClick={hanldeApprove}>
          <i className="fa fa-check" aria-hidden="true"></i>
        </span>
      }
    </div>
  )
}

export default Actions;
