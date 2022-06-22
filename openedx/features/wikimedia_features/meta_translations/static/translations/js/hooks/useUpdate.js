import { toast } from 'react-toastify';

import useClient from "./useClient";

export default function useUpdate(context) {
    const { client, notification } = useClient(context);

    const on_approved = (component, data) => {
      if (component.usage_key in data){
        let block_data = data[component.usage_key]
        component.version_status = {
          applied: block_data.applied_translation,
          applied_version: block_data.applied_version,
          versions: [
            ...component.version_status.versions,
            {id: block_data.applied_version, date: block_data.applied_version_date}
          ]
        }
        component.status.approved = block_data.approved;
      }
    }

    const approveRecursive = (outline, data) => {
      let currentPosition = outline && (outline.children || outline.units);
      if (outline){
        on_approved(outline, data)
      }
      if (!currentPosition){
        return
      }
      Object.keys(currentPosition).forEach(component_id => {
        approveRecursive(currentPosition[component_id], data)
      })
    }

    const get_block_id = (component) => {
      if (!component.status.approved && component.status.destination_flag && component.status.is_fully_translated){
        return component.usage_key
      }
      return null
    }

    const getValidBlocksIds = (outline, blockIds) => {
      let currentPosition = outline && (outline.children || outline.units);
      if (outline){
        let block_id = get_block_id(outline)
        block_id && blockIds.push(block_id)
      }
      if (!currentPosition){
        return
      }
      Object.keys(currentPosition).forEach(component_id => {
        getValidBlocksIds(currentPosition[component_id], blockIds)
      })
    }

    const geRecursiveBlockIds = (courseOutline, unit_id, subsection_id, section_id) => {
      let contentLocation = null;
      if (unit_id) {
        contentLocation = courseOutline
        .course_outline[section_id]
        .children[subsection_id]
        .children[unit_id];
      } else if (subsection_id) {
        contentLocation = courseOutline
        .course_outline[section_id]
        .children[subsection_id];
      } else {
        contentLocation = courseOutline
        .course_outline[section_id];
      }
      let blockIds = [];
      getValidBlocksIds(contentLocation, blockIds)
      return blockIds
    }



    const approveRecursiveCourseOutline = (props) => {
      const {setLoading, courseOutline, setCourseOutline, unit_id, subsection_id, section_id} = props;
      let blockIds = geRecursiveBlockIds (courseOutline, unit_id, subsection_id, section_id)
      setLoading(true);
      if (!blockIds.length){
        notification(toast.error, `No pending transaltions to be approved`);
        setLoading(false);
        return;
      }
      let options = {
        block_ids: blockIds
      }
      client.put(`${context.COURSE_APPROVE_URL}/`, options)
      .then((res) => {
        setCourseOutline(prevState => {
          let outline = {...prevState};
          let contentLocation = null;
          if (unit_id) {
            contentLocation = outline
            .course_outline[section_id]
            .children[subsection_id]
            .children[unit_id];
          } else if (subsection_id) {
            contentLocation = outline
            .course_outline[section_id]
            .children[subsection_id];
          } else {
            contentLocation = outline
            .course_outline[section_id];
          }
          approveRecursive(contentLocation, res.data)
          return outline;
        })
        if (blockIds.length != 1)
          notification(toast.success, `Congratulations! ${blockIds.length} translations are approved. They're also applied automatically to the Course Blocks`);
        else
          notification(toast.success, `Congratulations! ${blockIds.length} translation is approved. It's also applied automatically to the Course Block`);
      }
      )
      .catch((error) => {
        notification(toast.error, "Unable to approve this time, Please try again later.");
        console.error(error);
      })
      .finally(() => {
        setLoading(false);
      })
    }

    const approveCourseOutline = (props) => {
      const {usageKey, setLoading, setCourseOutline, content_id, unit_id, subsection_id, section_id} = props;
      const options = {
        block_ids : [usageKey]
      }
      setLoading(true);
      client.put(`${context.COURSE_APPROVE_URL}/`, options)
      .then((res) => {
        setCourseOutline(prevState => {
          let courseOutline = {...prevState};
          let contentLocation = null;
          if (content_id) {
            contentLocation = courseOutline
            .course_outline[section_id]
            .children[subsection_id]
            .children[unit_id]
            .units[content_id];
          } else if (unit_id) {
            contentLocation = courseOutline
            .course_outline[section_id]
            .children[subsection_id]
            .children[unit_id];
          } else if (subsection_id) {
            contentLocation = courseOutline
            .course_outline[section_id]
            .children[subsection_id];
          } else {
            contentLocation = courseOutline
            .course_outline[section_id];
          }
          on_approved(contentLocation, res.data)
          return courseOutline;
        })
        notification(toast.success, "Congratulations! The translation is approved. It's also applied automatically to the Course Block");
      })
      .catch((error) => {
        notification(toast.error, "Unable to approve this time, Please try again later.");
        console.error(error);
      })
      .finally(() => {
        setLoading(false);
      })
    }

    const updateTranslation = (props) => {
      const {setLoading, setCourseOutline, content_id, unit_id, subsection_id, section_id, version_id} = props;
      setLoading(true);
      client.get(`${context.COURSE_VERSION_URL}/${version_id}/`)
      .then((res) => {
        setCourseOutline(prevState => {
          let data = res.data.data
          let courseOutline = {...prevState};
          let contentLocation = null;
          if (content_id) {
            contentLocation = courseOutline
            .course_outline[section_id]
            .children[subsection_id]
            .children[unit_id]
            .units[content_id];
          } else if (unit_id) {
            contentLocation = courseOutline
            .course_outline[section_id]
            .children[subsection_id]
            .children[unit_id];
          } else if (subsection_id) {
            contentLocation = courseOutline
            .course_outline[section_id]
            .children[subsection_id];
          } else {
            contentLocation = courseOutline
            .course_outline[section_id];
          }
          if (!('previousState' in contentLocation)){
            contentLocation.previousState = {...contentLocation.data};
          }
          contentLocation.data = data;
          return courseOutline;
        })
      })
      .catch((error) => {
        notification(toast.error, "Unable to fetch translation this time, Please try again later.");
        console.error(error);
      })
      .finally(() => {
        setLoading(false);
      })


    }

    const updateTranslationToInitialState = (props) => {
      const {setLoading, setCourseOutline, content_id, unit_id, subsection_id, section_id} = props;
      setLoading(true);
      setCourseOutline(prevState => {
        let courseOutline = {...prevState};
        let contentLocation = null;
        if (content_id) {
          contentLocation = courseOutline
          .course_outline[section_id]
          .children[subsection_id]
          .children[unit_id]
          .units[content_id];
        } else if (unit_id) {
          contentLocation = courseOutline
          .course_outline[section_id]
          .children[subsection_id]
          .children[unit_id];
        } else if (subsection_id) {
          contentLocation = courseOutline
          .course_outline[section_id]
          .children[subsection_id];
        } else {
          contentLocation = courseOutline
          .course_outline[section_id];
        }
        contentLocation.data = {...contentLocation.previousState};
        return courseOutline;
      });
      setLoading(false);
    }

    const applyCourseVersion = (props) => {
      const {usageKey, setLoading, setCourseOutline, content_id, unit_id, subsection_id, section_id, version_id} = props;
      const options = {
        applied_version: version_id,
      }
      setLoading(true);
      client.put(`${context.COURSE_APPLY_URL}/${usageKey}/`, options)
      .then((res) => {
        setCourseOutline(prevState => {
          let courseOutline = {...prevState};
          let contentLocation = null;
          if (content_id) {
            contentLocation = courseOutline
            .course_outline[section_id]
            .children[subsection_id]
            .children[unit_id]
            .units[content_id];
          } else if (unit_id) {
            contentLocation = courseOutline
            .course_outline[section_id]
            .children[subsection_id]
            .children[unit_id];
          } else if (subsection_id) {
            contentLocation = courseOutline
            .course_outline[section_id]
            .children[subsection_id];
          } else {
            contentLocation = courseOutline
            .course_outline[section_id];
          }
          contentLocation.version_status = {
            ...contentLocation.version_status,
            applied: res.data.applied_translation,
            applied_version: res.data.applied_version
          };
          return courseOutline;
        })
        notification(toast.success, "Congratulations! The translation is applied to the Course Block");
      })
      .catch((error) => {
        notification(toast.error, "Unable to apply this time, Please try again later.");
        console.error(error);
      })
      .finally(() => {
        setLoading(false);
      })
    }

    return { 
      approveCourseOutline,
      updateTranslation,
      updateTranslationToInitialState,
      applyCourseVersion,
      approveRecursiveCourseOutline
    };
}
