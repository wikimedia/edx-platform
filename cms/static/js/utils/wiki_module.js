 /**
 * Utilities for wiki_modules.
 *
 * Returns:
 *
 * urlRoot: the root for meta_translation.
 * getDirectionUpdateUrl: a utility method that returns the direction update URL
 */
define(['underscore'], function(_) {
    var urlRoot = '/meta_translations';

    var getDirectionUpdateUrl = function() {
        return urlRoot + '/direction/'
    };

    return {
        urlRoot: urlRoot,
        getDirectionUpdateUrl: getDirectionUpdateUrl
    };
});
