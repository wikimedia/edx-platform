$ ->

  window.$$contents = {}
  window.$$discussions = {}

  $(".discussion-module").each (index, elem) ->
    view = new DiscussionModuleView(el: elem)

  $("section.discussion").each (index, elem) ->
    discussionData = DiscussionUtil.getDiscussionData($(elem).attr("_id"))
    discussion = new Discussion()
    discussion.reset(discussionData, {silent: false})
    view = new DiscussionView(el: elem, model: discussion)

  DiscussionUtil.bulkUpdateContentInfo(window.$$annotated_content_info)
