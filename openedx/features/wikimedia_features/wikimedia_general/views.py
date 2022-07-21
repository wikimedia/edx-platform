from opaque_keys.edx.keys import CourseKey
from django.template.loader import render_to_string
from web_fragments.fragment import Fragment
from openedx.core.djangoapps.plugin_api.views import EdxFragmentView
from completion.models import BlockCompletion
from openedx.features.course_experience.utils import get_course_outline_block_tree
from lms.djangoapps.courseware.courses import get_course_blocks_completion_summary, get_course_with_access
from lms.djangoapps.grades.api import CourseGradeFactory


class WikimediaProgressFragmentView(EdxFragmentView):
    """
    """
    def _get_grade_dict(self, course_grade):
        data = {}
        for chapter in course_grade.chapter_grades.values():
            subsections = chapter.get('sections', [])
            for subsection in subsections:
                subsection_grade = subsection.graded_total
                data.update({str(subsection.location): {
                    'score': "{}/{}".format(subsection_grade.earned, subsection_grade.possible),
                    'graded': subsection_grade.graded
                }})
                for problem_location, problem_grade in subsection.problem_scores.items():
                    data.update({str(problem_location): {
                        'score': "{}/{}".format(problem_grade.earned, problem_grade.possible),
                        'graded': problem_grade.graded,
                        'attempted': True if problem_grade.first_attempted else False
                    }})
        return data

    def _update_context_with_score(self, block, grade_dict):
        grade_data = grade_dict.get(block.get('id'))
        if grade_data:
            block.update(grade_data)
        for child in block.get('children', []):
            self._update_context_with_score(child, grade_dict)

    def render_to_fragment(self, request, course_id=None, **kwargs):
        """
        Render the discussion board to a fragment.
        Args:
            request: The Django request.
            course_id: The id of the course in question.

        Returns:
            Fragment: The fragment representing the discussion board
        """
        course_key = CourseKey.from_string(course_id)
        user = request.user

        course = get_course_with_access(request.user, 'load', course_key, check_if_enrolled=True)
        course_grade = CourseGradeFactory().read(user, course)
        grade_dict = self._get_grade_dict(course_grade)

        course_outline_context = get_course_outline_block_tree(
            request, course_id, request.user
        )
        self._update_context_with_score(course_outline_context, grade_dict)
        html = render_to_string(
            'wikimedia_general/wikimedia_progress_fragment.html',
            {"data": course_outline_context}
        )
        # inline_js = render_to_string('discussion/test_js.template', context)

        fragment = Fragment(html)
        self.add_fragment_resource_urls(fragment)
        # fragment.add_javascript(inline_js)
        return fragment


    # def vendor_js_dependencies(self):
    #     """
    #     Returns list of vendor JS files that this view depends on.
    #     The helper function that it uses to obtain the list of vendor JS files
    #     works in conjunction with the Django pipeline to ensure that in development mode
    #     the files are loaded individually, but in production just the single bundle is loaded.
    #     """
    #     dependencies = Set()
    #     dependencies.update(self.get_js_dependencies('discussion_vendor'))
    #     return list(dependencies)

    # def js_dependencies(self):
    #     """
    #     Returns list of JS files that this view depends on.
    #     The helper function that it uses to obtain the list of JS files
    #     works in conjunction with the Django pipeline to ensure that in development mode
    #     the files are loaded individually, but in production just the single bundle is loaded.
    #     """
    #     return self.get_js_dependencies('discussion')

    # def css_dependencies(self):
    #     """
    #     Returns list of CSS files that this view depends on.
    #     The helper function that it uses to obtain the list of CSS files
    #     works in conjunction with the Django pipeline to ensure that in development mode
    #     the files are loaded individually, but in production just the single bundle is loaded.
    #     """
    #     if get_language_bidi():
    #         return self.get_css_dependencies('style-discussion-main-rtl')
    #     else:
    #         return self.get_css_dependencies('style-discussion-main')
