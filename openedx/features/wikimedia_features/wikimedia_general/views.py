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
    View to render Wikimedia course progress tab
    """
    def _get_grade_dict(self, course_grade):
        """
        Extract grade dict in following format from edX grade classes for subsections and problem components.
        {
            "subsection1_block_id": {
                "score": 1/2,
                "graded": True
            },
            "problem1_block_id": {
                "score": 1/1,
                "graded": True
            },
            "problem2_block_id": {
                "score": 0/1,
                "graded": True
            }
        }
        """
        data = {}
        if not course_grade:
            return data

        for chapter in course_grade.chapter_grades.values():
            subsections = chapter.get('sections', [])
            for subsection in subsections:
                subsection_grade = subsection.graded_total
                subsection_score = "-"
                if subsection_grade and subsection_grade.possible:
                    subsection_score = "{}/{}".format(round(subsection_grade.earned), round(subsection_grade.possible))
                data.update({str(subsection.location): {
                    'score': subsection_score,
                    'graded': subsection_grade.graded
                }})
                for problem_location, problem_grade in subsection.problem_scores.items():
                    data.update({str(problem_location): {
                        'score': "{}/{}".format(round(problem_grade.earned), round(problem_grade.possible)),
                        'graded': problem_grade.graded,
                    }})
        return data

    def _update_context_with_score_and_progress(self, block, grade_dict):
        """
        Update given block dict with grade and progress percentage info.
        """
        if not block:
            return

        block_grade_data = grade_dict.get(block.get('id'))
        if block_grade_data:
            block.update(block_grade_data)

        progress = 0
        unit_count = 0
        children = block.get('children', [])
        if not len(children):
            if block.get('complete'):
                progress = 100

            # handle case of empty sections/subsections/units
            if block.get('type') not in ['course', 'chapter', 'vertical', 'sequential']:
                unit_count = 1

            block.update({
                'progress': progress,
                'unit_count': unit_count,
            })

        for child in children:
            self._update_context_with_score_and_progress(child, grade_dict)
            progress += child.get('progress', 0) * child.get('unit_count', 0)
            unit_count += child.get('unit_count', 0)

        if children and unit_count:
            block.update({
                'progress': round(progress/unit_count, 1),
                'unit_count': unit_count
            })

    def render_to_fragment(self, request, course_id=None, **kwargs):
        """
        Render wikimedia course progress to a fragment.
        Args:
            request: The Django request.
            course_id: The id of the course in question.

        Returns:
            Fragment: The fragment representing the Wikimedia course progress
        """
        course_key = CourseKey.from_string(course_id)
        user = request.user

        try:
            course = get_course_with_access(request.user, 'load', course_key, check_if_enrolled=True)
            course_grade = CourseGradeFactory().read(user, course)
            grade_dict = self._get_grade_dict(course_grade)
        except Exception as err:
            grade_dict = {}

        course_outline_context = get_course_outline_block_tree(
            request, course_id, request.user
        )
        self._update_context_with_score_and_progress(course_outline_context, grade_dict)
        html = render_to_string(
            'wikimedia_general/wikimedia_progress_fragment.html',
            {"data": course_outline_context}
        )

        fragment = Fragment(html)
        self.add_fragment_resource_urls(fragment)
        return fragment
