define([
    'jquery', 'underscore', 'backbone', 'js/utils/templates', 'js/views/modals/course_outline_modals',
    'edx-ui-toolkit/js/utils/html-utils', 'common/js/components/utils/view_utils'],
    function(
        $, _, Backbone, TemplateUtils, CourseOutlineModalsFactory, HtmlUtils, ViewUtils
    ) {
        'use strict';
        var CourseBlocksMappingView = Backbone.View.extend({
            events: {
                'click button.status-course-blocks-mapping-value': 'handleMappingButtonPress',
                'keypress button.status-course-blocks-mapping-value': 'handleMappingButtonPress'
            },

            initialize: function() {
                this.template = TemplateUtils.loadTemplate('course-blocks-mapping');
            },

            handleMappingButtonPress: function(event) {
                if (event.type === 'click' || event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    this.blocksMappingXBlock();
                }
            },

            blocksMappingXBlock: function() {
                var modelData = this.model.attributes
                ViewUtils.runOperationShowingMessage(
                    gettext('Mapping Blocks'),
                    function() {
                        return $.ajax({
                            url: $(".status-course-blocks-mapping").data().blocksMappingUrl,
                            type: 'POST',
                            dataType: 'json',
                            contentType: 'application/json',
                            data: JSON.stringify(modelData),
                            beforeSend: function() {
                                $("#status-course-blocks-mapping-value").prop("disabled", true);
                            },
                            success: function(response) {
                                $("#status-course-blocks-mapping-value").prop("disabled", false);
                            },
                        });
                    }
                );
            },

            render: function() {
                var isTranslatedOrBaseData = $("#python-context-var").data().isTranslatedOrBase
                if (isTranslatedOrBaseData && ['BASE', 'TRANSLATED'].includes(isTranslatedOrBaseData.toUpperCase()))
                {
                    var html = this.template(this.model.attributes);
                    HtmlUtils.setHtml(this.$el, HtmlUtils.HTML(html));
                }
                return this;
            }
        });

        return CourseBlocksMappingView;
    }
);
