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
                'click button.TEST_SEND_TRANSLATIONS': 'handleTestTranslationsButtonPress',
                'click button.TEST_FETCH_TRANSLATIONS': 'handleTestTranslationsButtonPress',
                'click button.TEST_APPLY_TRANSLATIONS': 'handleTestTranslationsButtonPress'
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

            handleTestTranslationsButtonPress: function(event) {
                event.preventDefault();

                var url, msg;
                var commit = $("#argument").val()
                var data_urls = $(".status-course-blocks-mapping").data()

                if (event.target.id == "TEST_SEND_TRANSLATIONS")
                {
                    url = data_urls.blocksSendUrl;
                    msg = "Sending Translations";
                }
                else if (event.target.id == "TEST_FETCH_TRANSLATIONS")
                {
                    url = data_urls.blocksFetchUrl;
                    msg = "Fetching Translations";
                }
                else if (event.target.id == "TEST_APPLY_TRANSLATIONS")
                {
                    url = data_urls.blocksApplyUrl;
                    msg = "Applying Translations";
                }
                else {
                    alert("Error: Unable to understand function");
                    return;
                }

                ViewUtils.runOperationShowingMessage(
                    gettext(msg),
                    function() {
                        return $.ajax({
                            url: url,
                            type: 'POST',
                            dataType: 'json',
                            contentType: 'application/json',
                            data: commit,
                            beforeSend: function() {
                                $("#"+ event.target.id).prop("disabled", true);
                            },
                            success: function(response) {
                                $("#"+ event.target.id).prop("disabled", false);
                            },
                        });
                    }
                );
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
                if ($(".status-course-blocks-mapping").data().isTranslatedOrBaseFlag == 'True')
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
