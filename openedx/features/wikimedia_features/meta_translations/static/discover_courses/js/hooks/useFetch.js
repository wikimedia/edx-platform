import { toast } from 'react-toastify';
import useClient from "./useClient";

export default function useFetch(context) {
  const { META_DATA, META_COURSE_TRANSLATIONS_URL, META_COURSES_URL, LANGUAGES } = context;
  const { client, notification } = useClient();

  const fetchCourseTranslations = (course_id, page, blockTypes, translationType, setTranslations, setLoading, setMaxPage, setEnableLoadMoreButton) => {
    setLoading(true);
    client.get(`${META_COURSE_TRANSLATIONS_URL}?course_id=${course_id}&page=${page}&block_types=${blockTypes}&translations=${translationType}`)
      .then((res) => {
        if (page == 1) {
          setMaxPage(res.data.num_pages);
          setTranslations(res.data.results);
          setEnableLoadMoreButton(res.data.num_pages != 1);
        } else {
          setTranslations((prev_translations) => [...prev_translations, ...res.data.results])
        }
      })
      .catch((error) => {
        notification(toast.error, META_DATA.errors.fetch_blocks);
        console.error(error);
      })
      .finally(() => {
        setLoading(false);
      })
  }

  const fetchCourseInfo = (course_id, setCourseInfo, setCourseLoading, setTranslatedPerentage) => {
    setCourseLoading(true);
    client.get(`${META_COURSES_URL}${course_id}`)
      .then((res) => {
        let data = res.data
        data['course_lang'] = LANGUAGES[data['course_lang']]
        data['base_course_lang'] = LANGUAGES[data['base_course_lang']]
        setCourseInfo(data);
        setTranslatedPerentage(Math.round((data['blocks_translated']/data['blocks_count'])*100));
      })
      .catch((error) => {
        notification(toast.error, META_DATA.errors.fetch_course);
        console.error(error);
      })
      .finally(() => {
        setCourseLoading(false);
      })
  }

  const fetchCourses = (setCourses, setAllCourses, setLoading) => {
    setLoading(true);
    client.get(META_COURSES_URL)
      .then((res) => {
        setCourses(res.data);
        setAllCourses(res.data);
      })
      .catch((error) => {
        notification(toast.error, META_DATA.errors.fetch_courses);
        console.error(error);
      })
      .finally(() => {
        setLoading(false);
      })
  }

  return { fetchCourses, fetchCourseInfo, fetchCourseTranslations };
}
