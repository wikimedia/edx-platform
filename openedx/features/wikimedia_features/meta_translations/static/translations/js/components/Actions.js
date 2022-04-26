import React from 'react';
import useUpdate from '../hooks/useUpdate';

function Actions (props) {

  const { approved, approveAll, context } = props;

  const { approveCourseOutline, approveRecursiveCourseOutline } = useUpdate(context);

  const hanldeApprove = (e) => {
    e.stopPropagation();
    const options = {
      approved: true
    }
    approveCourseOutline({options, ...props});
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
      <span className={`btn approveAll ${!approveAll? 'not-visible': ''}`} title="Approve All" onClick={hanldeApproveAll}>
        <i className="fa fa-list" aria-hidden="true"></i>
      </span>
      <span className={`btn approve ${approved? 'not-visible' : ''}`} title="Approve" onClick={hanldeApprove}>
        <i className="fa fa-check" aria-hidden="true"></i>
      </span>
    </div>
  )
}

export default Actions;
