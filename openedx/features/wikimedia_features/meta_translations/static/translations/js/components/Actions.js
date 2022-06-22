import React, { useEffect } from 'react';
import Select from 'react-select';
import useUpdate from '../hooks/useUpdate';

function Actions (props) {

  const { approved, versionStatus, enableApproveButton, destinationFlag, approveAll, setApproveAll, context } = props;
  const { applied, applied_version, versions } = versionStatus

  const { approveCourseOutline, updateTranslation,
    updateTranslationToInitialState, applyCourseVersion, approveRecursiveCourseOutline } = useUpdate(context);
    
  const [buttonsVisibility, setButtonsVisibility] = React.useState({apply: false, approve: true, approveAll: false})

  const [selectedOption, setSelectedOption] = React.useState({value:-1, label: 'pending translation'})
  
  const [options, setOptions]  = React.useState({})

  const [enableApplyButton, setEnableApplyButton] = React.useState(false)

  const [applyTrigger, setApplyTrigger] = React.useState(false)

  const approveTitle = (!destinationFlag ? 'Translation is Disabled' :
                        !enableApproveButton ? 'Incomplete Translation' : 
                        approved ? 'Approved' : 'Approve')
  
  const applyTitle = (!destinationFlag ? 'Translation is Disabled' :
                      !enableApplyButton ? 'Applied' :
                      'Apply')
  
  
  const updateOptionsFromVersion = () => {
    let newOptions = {
      recent: approved ? []: [{value:-1, label: 'pending translation'}], 
      applied: [],
      other: []
    }
    versions.forEach((version, index) => {
      if (applied && version.id == applied_version){
          newOptions.applied.push({value: version.id, label: version.date})
      } else {
        newOptions.other.push({value: version.id, label: version.date})
      }
    });
    let other = [...newOptions.other].reverse()
    newOptions.other = [...other]
    setOptions(newOptions)
  }

  useEffect(() => {
    setButtonsVisibility((prevState)=> ({...prevState, approveAll: approveAll}));
  }, [approveAll])

  useEffect(() => {
    updateOptionsFromVersion(approved);
    if (approved && !applyTrigger) {
      let last_element = versions.slice(-1)[0]
      setSelectedOption({value: last_element.id, label: last_element.date});
      setButtonsVisibility((prevState)=> ({...prevState, apply: true, approve: false}));
      destinationFlag && setEnableApplyButton(last_element.id != applied_version || !applied);
    } else {
      destinationFlag && setEnableApplyButton(selectedOption.value != applied_version || !applied);
      setApplyTrigger(false);
    }
  }, [versions, applied, applied_version, approved]);

  const handleChange = (option) => {
    if (option.value != selectedOption.value){
      setSelectedOption(option);
      destinationFlag && setEnableApplyButton(option.value != applied_version || !applied);
      if (option.value != -1 ){
        updateTranslation({version_id: option.value, ...props});
        setButtonsVisibility((prevState)=> ({...prevState, apply: true, approve: false}));
      } else {
        updateTranslationToInitialState({...props});
        setButtonsVisibility((prevState)=> ({...prevState, apply: false, approve: true}));
      }
    }
  };

  const handleApply = (e) => {
    e.stopPropagation();
    if (enableApplyButton){
      applyCourseVersion({version_id: selectedOption.value, ...props});
      setApplyTrigger(true);
    }
  }

  const hanldeApprove = (e) => {
    e.stopPropagation();
    if (!approved && enableApproveButton){
        approveCourseOutline({...props});
    }
  }

  const handleApproveAll = (e) => {
    e.stopPropagation();
    approveRecursiveCourseOutline({...props});
    setApproveAll(false);
  }

  return (
    <div className="btn-box">
      {
        <Select
          className="options"
          value={selectedOption}
          onChange={handleChange}
          options={[
            {
              label: 'recent',
              options: options.recent,
            },
            {
              label: 'applied',
              options: options.applied,
            },
            {
              label: 'other',
              options: options.other,
            }
          ]}
        />
      }
      {
        buttonsVisibility.apply && (
          <span className={`btn ${!enableApplyButton? 'disabled': ''}`} title={applyTitle} onClick={handleApply}>
            APPLY
          </span>
        )
      }
      {
        buttonsVisibility.approve && (
          <span className={`btn ${!enableApproveButton? 'disabled': ''}`} title={approveTitle} onClick={hanldeApprove}>
            APPROVE
          </span>
        )
      }
      {
        buttonsVisibility.approveAll && (
          <span className={`btn ${!approveAll? 'disabled': ''}`} title={approveTitle} onClick={handleApproveAll}>
            APPROVE ALL
          </span>
        )
      }
    </div>
  )
}

export default Actions;
