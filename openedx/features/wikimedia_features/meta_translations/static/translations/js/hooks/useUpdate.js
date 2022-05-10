import { toast } from 'react-toastify';

import useClient from "./useClient";

export default function useUpdate(context) {
    const { client, notification } = useClient(context);

    const isValidTranslations = (data) => {
      if (data.transcript) {
        return data.display_name !='' && data.transcript != []
      }
      return data.display_name != '' && data.content != ''
    }

    const updateUnits = (currentUnit) => {
      let units = currentUnit.units;
      if (currentUnit.status.destination_flag && currentUnit.data.display_name != ''){
        currentUnit.status.approved = true;
      }
      Object.keys(units).forEach(unit => {
        if (units[unit].status.destination_flag && isValidTranslations(currentUnit.data)){
          units[unit].status.approved = true;
        }
      })
    }

    const updateSubsections = (currentSubsection) => {
      let subsections = currentSubsection.children;
      if (currentSubsection.status.destination_flag && currentSubsection.data.display_name != '') {
        currentSubsection.status.approved = true;
      }
      Object.keys(subsections).forEach(subsection => {
        subsections[subsection].status.approved = true;

        if (subsections[subsection].units) {
          updateUnits(subsections[subsection]);
        }
      })
    }

    const approveCourseOutline = (props) => {
      const {usageKey, courseId, options, setLoading, setCourseOutline, content_id, unit_id, subsection_id, section_id} = props;

      setLoading(true);
      client.put(`${context.COURSE_APPROVE_URL}/${courseId}/translations/${usageKey}/`, options)
      .then((res) => {
        setCourseOutline(prevState => {
          let courseOutline = {...prevState};
          if (content_id) {
            courseOutline
            .course_outline[section_id]
            .children[subsection_id]
            .children[unit_id]
            .units[content_id]
            .status.approved = true;
          } else if (unit_id) {
            courseOutline
            .course_outline[section_id]
            .children[subsection_id]
            .children[unit_id]
            .status.approved = true;
          } else if (subsection_id) {
            courseOutline
            .course_outline[section_id]
            .children[subsection_id]
            .status.approved = true;
          } else {
            courseOutline
            .course_outline[section_id]
            .status.approved = true;
          }
          return courseOutline;
        })
      })
      .catch((error) => {
        notification(toast.error, "Unable to approve this time, Please try again later.");
        console.error(error);
      })
      .finally(() => {
        setLoading(false);
      })
    }

    const approveRecursiveCourseOutline = (props) => {
      const {usageKey, courseId, options, setLoading, setCourseOutline, unit_id, subsection_id, section_id} = props;

      setLoading(true);
      client.put(`${context.COURSE_APPROVE_URL}/${courseId}/translations/${usageKey}/`, options)
      .then((res) => {
        setCourseOutline(prevState => {
          let courseOutline = {...prevState};

          if (unit_id) {
            let currentUnit = courseOutline
            .course_outline[section_id]
            .children[subsection_id]
            .children[unit_id];
            updateUnits(currentUnit);
          } else {
            let currentSubsection = courseOutline.course_outline[section_id].children[subsection_id];
            updateSubsections(currentSubsection);
          }

          return courseOutline;
        })
      })
      .catch((error) => {
        notification(toast.error, "Unable to approve this time, Please try again later.");
        console.error(error);
      })
      .finally(() => {
        setLoading(false);
      })
    }

    return { approveCourseOutline, approveRecursiveCourseOutline };
}
