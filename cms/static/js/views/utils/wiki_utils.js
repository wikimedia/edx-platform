/**
 * Provides WikiTranslation utilities for views to work with xblocks.
 */
 define(['jquery', 'underscore', 'gettext', 'common/js/components/utils/view_utils',
 'edx-ui-toolkit/js/utils/string-utils', 'js/utils/wiki_module'],
 function($, _, gettext, ViewUtils, StringUtils, WikiModuleUtils) {
     'use strict';
     var updateDirectionStatus, showWarningOnEdit;

     /**
      * Update a specific xblock with new direction flag.
      * @param {jquery Element}  xblockElement  The xblock element to be updated.
      * @param destinationFlag A boolen to show current status of xblock destination flag.
      * @returns {jQuery promise} A promise representing the update status.
      */
     updateDirectionStatus = function(xblockElement, destinationFlag) {
         var updateStatus = $.Deferred(),
             operation = function() {
                 ViewUtils.runOperationShowingMessage(gettext('Updating'),
                 function(){
                     var locator = xblockElement.data('locator');
                     $.postJSON(WikiModuleUtils.getDirectionUpdateUrl(), {
                         destination_flag: !destinationFlag,
                         locator: locator,
                     }, function(response) {
                         updateStatus.resolve(response);
                     })
                     .fail(function() {
                         updateStatus.reject();
                     });
                     return updateStatus.promise();
                 });
             }
         
         if (destinationFlag){
             ViewUtils.confirmThenRunOperation(
                 StringUtils.interpolate(
                     gettext('Disable Translations for this block?'),
                     true
                 ),
                 gettext('Block data would not be sent to server for translations'),
                 StringUtils.interpolate(
                     gettext('Yes, Disable Translations'),
                     true
                 ),
                 operation
             );
         } else {
             ViewUtils.confirmThenRunOperation(
                 StringUtils.interpolate(
                     gettext('Enable Translations for this block?'),
                     true
                 ),
                 gettext('Block data would be sent to server for translations'),
                 StringUtils.interpolate(
                     gettext('Yes, Enable Translations'),
                     true
                 ),
                 operation
             );
         }
         
         return updateStatus.promise()
     };

    showWarningOnEdit = function(operation) {
        ViewUtils.confirmThenRunOperation(
            StringUtils.interpolate(
                gettext('Do you want to Edit?'),
                true
            ),
            gettext('Please disable translations after an edit, otherwise edited component is overwritten by auto translations.'),
            StringUtils.interpolate(
                gettext('Yes, Start Editing'),
                true
            ),
            operation
        );
    };
     
     return {
         updateDirectionStatus: updateDirectionStatus,
         showWarningOnEdit: showWarningOnEdit,
     };
 });
