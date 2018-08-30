// submit.js

$(document)
.ready(function() {

$('#select_market')
  .dropdown({
    allowAdditions: true,
    fullTextSearch: true

 })
;

$('#select_channel')
  .dropdown({
    allowAdditions: true,
    fullTextSearch: true

 })
;

$('#select_subtype')
  .dropdown({
    allowAdditions: true,
    fullTextSearch: true

 })
;


$('.ui.form')
  .form({
    fields: {
      job_title     : 'empty',
    }
  })
;
});
