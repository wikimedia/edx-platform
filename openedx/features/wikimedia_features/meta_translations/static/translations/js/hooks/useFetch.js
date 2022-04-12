import { toast } from 'react-toastify';

import useClient from "./useClient";

export default function useFetch(context) {
    const { client, notification } = useClient();

    const fetchCourses = (setCourses, setLoading) => {
      setLoading(true);
      client.get(context.COURSES_URL)
      .then((res) => res.json())
      .then((res) => {
        setCourses(res);
      })
      .catch((error) => {
        notification(toast.error, "Unable to load Courses.");
        console.error(error);
      })
      .finally(() => {
        setLoading(false);
      })
    }

    const fetchCourseOutline = (rerun_subsection_key, setCourseOutline, setLoading) => {
        setLoading(true);
        client.get(`${context.COURSE_OUTLINE_URL}/${rerun_subsection_key}`)
        .then((res) => res.json())
        .then((res) => {
          setCourseOutline(res)
        })
        .catch((error) => {
          notification(toast.error, "Unable to load Course Outline.");
          console.error(error);
        })
        .finally(() => {
          setLoading(false);
        })
      }

    const fetchCourseUnit = (props) => {
      const {rerunCourseUnitKey, subsection_id, section_id, unit_id, setCourseOutline, setLoading, showSlide} = props;

      setLoading(true);
      client.get(`${context.COURSE_UNIT_URL}/${rerunCourseUnitKey}`)
      .then((res) => res.json())
      .then((res) => {
        const { components_data: units, base_components_data: base_units } = res;
        setCourseOutline((prevState) => {
          const state = {...prevState}
          state
          .base_course_outline[section_id]
          .children[subsection_id]
          .children[unit_id]
          .units = base_units;
          state
          .course_outline[section_id]
          .children[subsection_id]
          .children[unit_id]
          .units = units;

          return state
        });
      })
      .then(() => {
        showSlide()
      })
      .catch((error) => {
        notification(toast.error, "Unable to load content.");
        console.error(error);
      })
      .finally(() => {
        setLoading(false);
      })
  }
    return { fetchCourses, fetchCourseOutline, fetchCourseUnit };
}
