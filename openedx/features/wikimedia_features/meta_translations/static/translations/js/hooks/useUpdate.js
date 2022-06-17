import { toast } from 'react-toastify';

import useClient from "./useClient";

export default function useUpdate(context) {
    const { client, notification } = useClient(context);

    const approveCourseOutline = (props) => {
      const {usageKey, courseId, setLoading, setCourseOutline, content_id, unit_id, subsection_id, section_id} = props;
      const options = {
        approved: true,
      }
      setLoading(true);
      client.put(`${context.COURSE_APPROVE_URL}/${courseId}/translations/${usageKey}/`, options)
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
            applied: res.data.applied_translation,
            applied_version: res.data.applied_version,
            versions: [
              ...contentLocation.version_status.versions,
              {id: res.data.applied_version, date: res.data.applied_version_date}
            ]
          }
          contentLocation.status.approved = res.data.approved;
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
      applyCourseVersion
    };
}
