'use strict';
/** Shared form functions used by app and yer forms **/

/* TODO
 * Bind onclick for button.remove-file
  <iframe class="upload" id="id_upload_frame" name="upload_frame" onload="fileUploads.iframeUpdated(this);"></iframe>
  (in app and yer templates)
 * submit button 
 *
 * Need to access from outside:
 *   autoSave.save
 *   autoSave.pause
 *   autoSave.resume
 *   formUtils.log
 *
 *   formUtils.init?
 *
 */

window._sjf = {};

(function (namespace) {

  var STATUS_TEXTS = {
    400: '400 Bad request',
    401: '401 Unauthorized',
    403: '403 Forbidden',
    404: '404 Not found',
    408: '408 Request timeout',
    500: '500 Internal server error',
    503: '503 Service unavailable',
    504: '504 Gateway timeout'
  };


  /**
   * @param {string} urlPrefix - beginning of path (i.e. 'apply'). no slashes
   * @param {number} draftId - pk of draft object (draft app or draft yer)
   * @param {number} submitId - pk of object used in post (cycle or award)
   * @param {string.alphanum} userId - randomly generated user id for mult edit warning
   * @param {string} staffUser - querystring for user override (empty string if n/a)
   */
  formUtils.init = function(urlPrefix, draftId, submitId, userId, staffUser) {
    if (staffUser && staffUser !== 'None') {
      formUtils.staffUser = staffUser;
    } else {
      formUtils.staffUser = '';
    }
    autoSave.init(urlPrefix, submitId, userId);
    fileUploads.init(urlPrefix, draftId);
  };


  function getDisplayDateTime() {
    var MONTHS = [
      'January', 'February', 'March', 'April', 'May', 'June',
      'July', 'August', 'September', 'October', 'November', 'December'
    ];
    var date = new Date();
    var hours = date.getHours();
    var dd = 'a.m.';
    if (hours >= 12) {
      hours = hours - 12;
      dd = 'p.m.';
    }
    hours = hours === 0 ? 12 : hours;
    var min = date.getMinutes();
    min = min < 10 ? '0' + min : min;
    return MONTHS[date.getMonth()] + ' ' + date.getDate() + ', ' + hours + ':' + min + dd;
  };


  /**
   * Update word limit indicator for text field.
   *
   * @param {jQuery.Event} event - jQuery keyup event
   */
  function updateWordCount(event) {
    var textarea = event.target;
    var limit = textarea.dataset.limit;
    var display = $('#' + textarea.name + '_wordcount');

    var word_count = 0;
    if (textarea.value && textarea.value.trim()) {
      // match the chars in python's string.punctuation
      // remove non-ascii characters
      word_count = textarea.value
        .replace(/[!"#$%&'()*+,-.\/:;<=>?@\[\\\]\^_`{|}~]/g, '')
        .replace(/[^\x00-\x7F]/g, "")
        .split(/[ \r\n]+/)
        .length;
    }
    var diff = limit - word_count;

    if (diff >= 0) {
      display.html(diff + ' words remaining');
      display.removeClass('wordcount_over').addClass('wordcount');
    } else {
      display.html(diff + ' words over the limit');
      display.removeClass('wordcount').addClass('wordcount_over');
    }
  }

  var INTERVAL_MS = 60000;
  var INITIAL_DELAY_MS = 10000;
  var saveTimer;
  var pauseTimer;


  autoSave.save = function (submit, force) {
    if (formUtils.staffUser) { // TODO use querystring function
      force = '&force=' + force || 'false';
    } else {
      force = '?force=' + force || 'false';
    }

    log('Autosaving');

    $.ajax({
      url: autoSave.saveUrl + force,
      type: 'POST',
      data: $('form').serialize() + '&user_id=' + autoSave.userId,
      success: function(data, textStatus, jqXHR) {
        if (jqXHR.status === 200) {
          if (submit) {
            // button click - trigger the hidden submit button
            var submitAll = document.getElementById('hidden_submit_app');
            submitAll.click();
          } else {
            // autosave - update 'last saved'
            $('.autosaved').html(getDisplayDateTime());
          }
        } else { // unexpected status code
          $('.autosaved').html('Unknown error<br>If you are seeing errors repeatedly please <a href="/apply/support#contact">contact us</a>');
        }
      },
      error: function(jqXHR, textStatus) {
        var errortext = '';
        if (jqXHR.status === 409)  {
          // conflict - pause autosave and confirm force
          window.clearInterval(autoSave.saveTimer);
          showConflictWarning('autosave'); // method defined in org_app.html
        } else {
          if(jqXHR.status === 401) {
            location.href = jqXHR.responseText + '?next=' + location.href;
          } else if (STATUS_TEXTS[jqXHR.status]) {
            errortext = STATUS_TEXTS[jqXHR.status];
          } else if (textStatus === 'timeout') {
            errortext = 'Request timeout';
          } else {
            errortext = 'Unknown error';
          }
          $('.autosaved').html('Error: ' + errortext + '<br>If you are seeing errors repeatedly please <a href="/apply/support#contact">contact us</a>');
        }
      }
    });
  };

  /**------------------------------------ FILE UPLOADS -------------------------------------------**/


  /* each file field has its own form. html element ids use this pattern:
  input field:              'id_' + fieldname
  form:                     fieldname + '_form'
  span for upload status:   fieldname + '_uploaded'
  submit button:            fieldname + '_submit'
  */

  namespace.save = save;
  namespace.pause = pause;
  namespace.resume = resume;
})(window._sjf);
