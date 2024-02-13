import React, { useEffect } from 'react';
import Select from 'react-select';
import useUpdate from '../hooks/useUpdate';

function Actions (props) {

  const { approved, versionStatus, enableApproveButton, destinationFlag, approveAll, setApproveAll, context } = props;
  const { applied, applied_version, versions } = versionStatus;

  const { approveCourseOutline, updateTranslation,
    updateTranslationToInitialState, applyCourseVersion, approveRecursiveCourseOutline } = useUpdate(context);

  const [buttonsVisibility, setButtonsVisibility] = React.useState({apply: false, approve: true, approveAll: false});

  const [selectedOption, setSelectedOption] = React.useState({value:-1, label: context.META_DATA.options_tags.pending});

  const [options, setOptions]  = React.useState({});

  const [enableApplyButton, setEnableApplyButton] = React.useState(false);

  const [applyTrigger, setApplyTrigger] = React.useState(false);

  const approveTitle = (!destinationFlag ? context.META_DATA.approve_button.disabled :
                        !enableApproveButton ? context.META_DATA.approve_button.incomplete :
                        approved ? context.META_DATA.approve_button.approved : context.META_DATA.approve_button.approve);

  const applyTitle = (!destinationFlag ? context.META_DATA.apply_button.disabled :
                      !enableApplyButton ? context.META_DATA.apply_button.applied :
                      context.META_DATA.apply_button.apply);

  const reset_states = () => {
    setButtonsVisibility({apply: false, approve: true, approveAll: false});
    setSelectedOption({value:-1, label: context.META_DATA.options_tags.pending});
    setEnableApplyButton(false);
    setApplyTrigger(false);
  }

  const updateOptionsFromVersion = () => {
    let newOptions = {
      recent: approved ? []: [{value:-1, label: context.META_DATA.options_tags.pending}],
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
  }, [approveAll]);

  useEffect(() => {
    updateOptionsFromVersion();
    if (!applied_version) {
      reset_states();
    } else if (approved && !applyTrigger) {
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
  }

  const handleApply = (e) => {
    e.stopPropagation();
    if (enableApplyButton){
      applyCourseVersion({version_id: selectedOption.value, ...props});
      setApplyTrigger(true);
    }
  }

  const handleApprove = (e) => {
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
    <div className="action-bar btn-box">
      {
        <Select
          className="options"
          value={selectedOption}
          onChange={handleChange}
          options={[
            {
              label: context.META_DATA.options_tags.recent,
              options: options.recent,
            },
            {
              label: context.META_DATA.options_tags.applied,
              options: options.applied,
            },
            {
              label: context.META_DATA.options_tags.other,
              options: options.other,
            }
          ]}
        />
      }
      {
         buttonsVisibility.apply && applyTitle==context.META_DATA.apply_button.applied && (
          <span className="badge badge-success">
            {context.META_DATA.applied_badge.label}
          </span>
        )
      }
      {
        buttonsVisibility.apply && applyTitle!=context.META_DATA.apply_button.applied && (
          <span className={`btn-translations btn-action ${!enableApplyButton? 'disabled': ''}`} title={applyTitle} onClick={handleApply}>
            {context.META_DATA.apply_button.label}
          </span>
        )
      }
      {
        buttonsVisibility.approve && (
          <span className={`btn-translations btn-action ${!enableApproveButton? 'disabled': ''}`} title={approveTitle} onClick={handleApprove}>
            {context.META_DATA.approve_button.label}
          </span>
        )
      }
      {
        buttonsVisibility.approveAll && (
          <span className={`btn-translations btn-action ${!approveAll? 'disabled': ''}`} title={approveTitle} onClick={handleApproveAll}>
            {context.META_DATA.approve_all_button.label}
          </span>
        )
      }
    </div>
  )
}

export default Actions;
