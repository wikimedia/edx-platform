import React, { useEffect } from 'react';
import Select from 'react-select';
import useUpdate from '../hooks/useUpdate';

function Actions (props) {

  const { approved, versionStatus, enableApproveButton, destinationFlag, context } = props;
  const { applied, applied_version, versions } = versionStatus

  const { approveCourseOutline, updateTranslation,
    updateTranslationToInitialState, applyCourseVersion } = useUpdate(context);
  
  
  const [approveTrigger, setApproveTrigger] = React.useState(approved)
  
  const [buttonsVisibility, setButtonsVisibility] = React.useState({apply: false, approve: true})

  const [selectedOption, setSelectedOption] = React.useState({value:-1, label: 'pending translation'})
  
  const [options, setOptions]  = React.useState({})

  const [enableApplyButton, setEnableApplyButton] = React.useState(false)

  const approveTitle = (!destinationFlag? 'Translation is Disabled':
                        !enableApproveButton? 'Incomplete Translation': 
                        approved? 'Approved': 'Approve')
  
  const applyTitle = !enableApplyButton ? 'Applied' : applied_version==selectedOption.value ? 'Apply Now': 'Apply'
  
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
    updateOptionsFromVersion(approved);
    if (approveTrigger) {
      let last_element = versions.slice(-1)[0]
      setSelectedOption({value: last_element.id, label: last_element.date});
      setButtonsVisibility({apply: true, approve: false});
      setApproveTrigger(false);
      setEnableApplyButton(last_element.id != applied_version || !applied);
    } else {
      setEnableApplyButton(selectedOption.value != applied_version || !applied);
    }
  }, [versions, applied, applied_version, approved]);

  const handleChange = (option) => {
    if (option != selectedOption){
      setSelectedOption(option);
      setEnableApplyButton(option.value != applied_version || !applied);
      if (option.value != -1 ){
        updateTranslation({version_id: option.value, ...props});
        setButtonsVisibility({apply: true, approve: false});
      } else {
        updateTranslationToInitialState({...props});
        setButtonsVisibility({apply: false, approve: true});
      }
    }
  };

  const handleApply = (e) => {
    e.stopPropagation();
    if (enableApplyButton){
      applyCourseVersion({version_id: selectedOption.value, ...props});
    }
  }

  const hanldeApprove = (e) => {
    e.stopPropagation();
    if (!approved && enableApproveButton){
        approveCourseOutline({...props});
        setApproveTrigger(true);
    }
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
    </div>
  )
}

export default Actions;
