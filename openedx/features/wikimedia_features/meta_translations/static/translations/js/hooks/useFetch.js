import { toast } from 'react-toastify';

import useClient from "./useClient";

export default function useFetch(context) {
    const { client, notification } = useClient();

    const fetchCourses = (setCourses, setLoading, setIsFetched, only_admin_created_courses=false) => {
      setLoading(true);
      let url = context.COURSES_URL
      if(only_admin_created_courses){
        url = `${url}?admin_created_courses=True`
      }
      client.get(url)
      .then((res) => {
        setCourses(res.data);
      })
      .catch((error) => {
        notification(toast.error, context.META_DATA.errors.fetch_courses);
        console.error(error);
      })
      .finally(() => {
        setLoading(false);
        setIsFetched(true);
      })
    }

    const fetchCourseOutline = (rerun_subsection_key, setCourseOutline, setLoading) => {
        setLoading(true);
        client.get(`${context.COURSE_OUTLINE_URL}/${rerun_subsection_key}`)
        .then((res) => {
          setCourseOutline(res.data)
        })
        .catch((error) => {
          notification(toast.error, context.META_DATA.errors.fetch_outline);
          console.error(error);
        })
        .finally(() => {
          setLoading(false);
        })
      }

    const fetchCourseUnit = (props) => {
      const {rerunCourseUnitKey, subsection_id, section_id, unit_id, setCourseOutline, setLoading, showSlide, setApproveAll} = props;

      setLoading(true);
      client.get(`${context.COURSE_UNIT_URL}/${rerunCourseUnitKey}`)
      .then((res) => {
        const { components_data: units, base_components_data: base_units } = res.data;
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
        return res.data.components_data
      })
      .then((units) => {
        showSlide();
        let check = Object.keys(units).some((unit_id)=>{
          let component = units[unit_id]
          if (!component.status.approved && component.status.destination_flag && component.status.is_fully_translated)
            return true
          return false
        })
        setApproveAll(check);
      })
      .catch((error) => {
        notification(toast.error, context.META_DATA.errors.fetch_content);
        console.error(error);
      })
      .finally(() => {
        setLoading(false);
      })
  }
    return { fetchCourses, fetchCourseOutline, fetchCourseUnit };
}
