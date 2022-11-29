import React, { useEffect, useState } from "react";
import { ToastContainer } from 'react-toastify';
import { useParams } from "react-router-dom";
import useFetch from "../hooks/useFetch";
import TranslationBlock from "./TranslationBlock";
import Spinner from '../assets/spinner';

function CourseTranslations({ context }) {
  const { course_id } = useParams();
  const { fetchCourseInfo, fetchCourseTranslations } = useFetch(context);
  const [maxPage, setMaxPage] = useState(1);
  const [page, setPage] = useState(1);
  const [courseLoading, setCourseLoading] = useState(true);
  const [courseInfo, setCourseInfo] = useState(null)
  const [loading, setLoading] = useState(true);
  const [enableLoadMoreButton, setEnableLoadMoreButton] = useState(true);
  const [tranlations, setTranslations] = useState([]);
  const [onToggleApplyFilter, setonToggleApplyFilter] = useState(false);
  const [translatedPercentage, setTranslatedPerentage] = useState(0);

  const [blockFilters, setBlockFilters] = useState({
    'video': true,
    'section-title': true,
    'html': true,
    'problem': true,
  })
  const [translationFilters, setTranslationFilters] = useState({
    'translated': true,
    'untranslated': true,
  })

  const handleTranslationFilters = (blockKey) => {
    const updatedTranslationFilters = {...translationFilters, [`${blockKey}`]: !translationFilters[blockKey] };
    let allow_update = false;
    Object.entries(updatedTranslationFilters).forEach(([key, value])=>{
      allow_update = allow_update || value;
    });
    allow_update && setTranslationFilters(prev => {
      return { ...prev, [`${blockKey}`]: !prev[blockKey] }
    })
  }

  const handleBlockFilters = (blockKey) => {
    const updatedBlockFilters = {...blockFilters, [`${blockKey}`]: !blockFilters[blockKey] };
    let allow_update = false;
    Object.entries(updatedBlockFilters).forEach(([key, value])=>{
      allow_update = allow_update || value;
    });
    allow_update && setBlockFilters(prev => {
      return { ...prev, [`${blockKey}`]: !prev[blockKey] }
    })
  }

  const onLoadMore = () => {
    if (!loading && page + 1 <= maxPage) {
      if (page + 1 == maxPage) {
        setEnableLoadMoreButton(false);
      }
      setPage(page + 1);
    }
  }

  const getBlockTypeFilter = (blockFilters) => {
    let accepted_blocks = []
    blockFilters['section-title'] && accepted_blocks.push('chapter', 'sequential', 'vertical')
    blockFilters['html'] && accepted_blocks.push('html')
    blockFilters['problem'] && accepted_blocks.push('problem')
    blockFilters['video'] && accepted_blocks.push('video')
    return accepted_blocks.join('+')
  }

  const getTranslationFiter = (translationFilters) => {
    return (
      translationFilters.translated && translationFilters.untranslated && 'all' ||
      translationFilters.translated && 'translated' ||
      translationFilters.untranslated && 'untranslated'
    )
  }

  const onClickApply = () => {
    setTranslations([]);
    setPage(1);
    setonToggleApplyFilter(prev=>!prev);
    window.scrollTo(0, 0);
  }

  useEffect(() => {
    fetchCourseInfo(course_id, setCourseInfo, setCourseLoading, setTranslatedPerentage);
  }, [])

  useEffect(() => {
    const blockTypes = getBlockTypeFilter(blockFilters);
    const translationType = getTranslationFiter(translationFilters);
    fetchCourseTranslations(course_id, page, blockTypes, translationType, setTranslations, setLoading, setMaxPage, setEnableLoadMoreButton);
  }, [course_id, page, onToggleApplyFilter]);

  return (
    <div className="discover-courses">
      {
        courseInfo && (
          <div className="content">
            <div className="grid-block">
              <div className="grid-header">
                <span className="title">{courseInfo.course_name}</span>
                <div className="course-info">
                  <span className="badge">
                    Last Updated: {courseInfo.last_fetched_in_hours ? `${Math.round(courseInfo.last_fetched_in_hours * 100)/100} Hrs Ago` : 'N/A'}
                  </span>
                  <span className="badge">
                    Translated: {translatedPercentage}%
                  </span>
                </div>
              </div>
              <div className="grid">
                {
                  tranlations.map((val) =>
                    <TranslationBlock
                      key={val.block_id}
                      id={val.block_id}
                      title={val.base_data.display_name}
                      content={val.base_data.content}
                      blockType={val.block_type}
                      isTranslated={val.translated}
                      isParsed={val.is_parsed_block}
                      redirectUrl={val.group_url}
                    />
                  )
                }
                {
                  !loading && !tranlations.length && <span>No course blocks found</span>
                }
                {
                  loading && <Spinner />
                }
              </div>
              <div className="grid-actions">
                {
                  enableLoadMoreButton && !loading && <button className="btn btn-translations" onClick={onLoadMore}>Load More</button>
                }
              </div>
            </div>
            <div className="filter-block">
              <div className="filter-header">
                <span className="title">Filters</span>
              </div>
              <div className="filter-field">
                <span className="title">From Language</span>
                <div className="block">
                  <span>{courseInfo.base_course_lang}</span>
                </div>
              </div>
              <div className="filter-field">
                <span className="title">To Language</span>
                <div className="block">
                  <span>{courseInfo.course_lang}</span>
                </div>
              </div>
              <div className="filter-field">
                <span className="title">Block Type</span>
                <div className="block">
                  <label className="block-checkbox">
                    <input type="checkbox" checked={blockFilters["section-title"]} onChange={() => handleBlockFilters("section-title")} />
                    Section Header
                  </label>
                  <label className="block-checkbox">
                    <input type="checkbox" checked={blockFilters["video"]} onChange={() => handleBlockFilters("video")} />
                    Video
                  </label>
                  <label className="block-checkbox">
                    <input type="checkbox" checked={blockFilters["html"]} onChange={() => handleBlockFilters("html")} />
                    HTML
                  </label>
                  <label className="block-checkbox">
                    <input type="checkbox" checked={blockFilters["problem"]} onChange={() => handleBlockFilters("problem")} />
                    Problem
                  </label>
                </div>
              </div>
              <div className="filter-field">
                <span className="title">Translation</span>
                <div className="block">
                  <label className="block-checkbox">
                    <input type="checkbox" checked={translationFilters["translated"]} onChange={() => handleTranslationFilters("translated")} />
                    Translated
                  </label>
                  <label className="block-checkbox">
                    <input type="checkbox" checked={translationFilters["untranslated"]} onChange={() => handleTranslationFilters("untranslated")} />
                    Untranslated
                  </label>
                </div>
              </div>
              <button className="btn btn-translations" onClick={onClickApply}>Apply</button>
            </div>
          </div>
        )
      }
      {
        courseLoading && (
          <Spinner center_in_screen />
        )
      }
      <ToastContainer />
    </div>
  )
}

export default CourseTranslations;
