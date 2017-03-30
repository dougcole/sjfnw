'use strict';
/** Shared form functions - utils, autosave, file handling **/

/**----------------------------- formUtils ---------------------------------**/
var formUtils = {};

formUtils.log = function (message) {
  var d = new Date();
  var min = d.getMinutes();
  min = min < 10 ? '0' + min : min;
  var dateString = d.getHours() + ':' + min + ':' + d.getSeconds();

  console.log(dateString, message);
};

formUtils.loadingImage = '<img src="/static/images/ajaxloader2.gif" height="16" width="16" alt="Loading...">';

formUtils.statusTexts = { // for ajax error messages
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


/**
 * Return current time as a string for display. Format: May 12, 2:45p.m.
 */
formUtils.currentTimeDisplay = function() {
  var monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
                    'July', 'August', 'September', 'October', 'November', 'December'];
  var d = new Date();
  var h = d.getHours();
  var m = d.getMinutes();
  var dd = 'a.m.';
  if (h >= 12) {
    h = h - 12;
    dd = 'p.m.';
  }
  h = h === 0 ? 12 : h;
  m = m < 10 ? '0' + m : m;
  return monthNames[d.getMonth()] + ' ' + d.getDate() + ', ' + h + ':' + m + dd;
};


/**
 * Update word limit indicator for text field.
 *
 * @param {jQuery.Event} event - jQuery keyup event
 */
function updateWordCount(event) {
  var area = event.target;
  var limit = area.dataset.limit;
  var display = $('#' + area.name + '_wordcount');

  var word_count = 0;
  if (area.value && area.value.trim()) {
    // match the chars in python's string.punctuation
    // remove non-ascii characters
    word_count = area.value
      .replace(/[!"#$%&'()*+,-.\/:;<=>?@\[\\\]\^_`{|}~]/g, '')
      .replace(/[^\x00-\x7F]/g, "")
      .split(/[ \r\n]+/)
      .length;
  }
  var diff = limit - word_count;

  if (diff >= 0) {
    display.html(diff + ' words remaining');
    display.removeClass('wordcount_over');
  } else {
    display.html(-diff + ' words over the limit');
    display.addClass('wordcount_over');
  }
}

/**------------------------------- autoSave --------------------------------**/

var autoSave = {
  INTERVAL_MS: 60000,
  INITIAL_DELAY_MS: 10000
};
autoSave.saveTimer = false;
autoSave.pauseTimer = false;


autoSave.init = function(urlPrefix, submitId, userId) {
  autoSave.submitUrl = '/' + urlPrefix + '/' + submitId;
  autoSave.saveUrl = autoSave.submitUrl + '/autosave' + formUtils.staffUser;
  autoSave.submitUrl += formUtils.staffUser;
  if (userId) {
    autoSave.userId = userId;
  } else {
    autoSave.userId = '';
  }
  formUtils.log('Autosave variables loaded');
  autoSave.resume();
};


autoSave.pause = function() {
  if ( !window.onfocus ) {
    formUtils.log('autoSave.pause called; setting timer to pause');

    // clear initial delay timeout if applicable
    window.clearTimeout(autoSave.initialDelayTimeout);

    // pause auto save
    autoSave.pauseTimer = window.setTimeout(function () {
      formUtils.log('Pausing autosave');
      window.clearInterval(autoSave.saveTimer);
      autoSave.pauseTimer = false;
    }, autoSave.INTERVAL_MS);

    // set to resume when window gains focus
    $(window).on('focus', autoSave.resume);
    // don't watch for further blurs
    $(window).off('blur');
  } else {
    formUtils.log('autoSave.pause called, but already paused');
  }
};

autoSave.resume = function (firstTime) {
  if ( !window.onblur ) { // avoid double-firing - if onblur is already set up, skip
    formUtils.log(' autoSave.resume called');

    if (autoSave.pauseTimer) {
      // clear timer if window recently lost focus (in this case autosave is still going)
      formUtils.log('pause had been set; clearing it');
      window.clearTimeout(autoSave.pauseTimer);
      autoSave.pauseTimer = false;
    } else if (firstTime) {
      // just loaded page - delay and then resume autosave
      formUtils.log('Waiting 10s to start autosave timer');
      autoSave.initialDelayTimeout = window.setTimeout(autoSave.resume, autoSave.INITIAL_DELAY_MS);
    } else {
      // was paused - resume autosave
      formUtils.log('Starting autosave at 60s intreval');
      autoSave.saveTimer = window.setInterval(autoSave.save, autoSave.INTERVAL_MS);
    }

    // listen for blurs again
    $(window).on('blur', autoSave.pause);
    // stop listening to focus
    $(window).off('focus');
  } else {
    formUtils.log('autoSave.resume called but window already has onblur');
  }
};

/**
 * Save the current draft by sending form data to server.
 *
 * @param {Object} options
 *   @param {boolean} options.force (optional) - override conflict warning
 *   @param {boolean} options.submit (optional) - whether submit button was clicked
 */
autoSave.save = function (options) {
  options = options || {};
  options.force = options.force || options.submit; // use force when submitting

  var qs = '';

  if (options.force) {
    qs += formUtils.staffUser ? '&' : '?'; // TODO use querystring function
    qs += 'force=' + options.force;
  }

  formUtils.log('Autosaving');

  $.ajax({
    url: autoSave.saveUrl + qs,
    type: 'POST',
    data: $('form').serialize() + '&user_id=' + autoSave.userId,
    success: function (data, textStatus, jqXHR) {
      if (jqXHR.status === 200) {
        if (options.submit) {
          // button click - trigger the hidden submit button
          var submitAll = document.getElementById('hidden_submit_app');
          submitAll.click();
        } else {
          $('.autosaved').html(formUtils.currentTimeDisplay());
        }
      } else { // unexpected status code
        $('.autosaved').html('Unknown error<br>If you are seeing errors repeatedly please <a href="/apply/support#contact">contact us</a>');
      }
    },
    error: function (jqXHR, textStatus) {
      if (jqXHR.status === 409)  {
        // conflict - pause autosave and confirm force
        window.clearInterval(autoSave.saveTimer);
        showConflictWarning();
      } else if(jqXHR.status === 401) {
        location.href = jqXHR.responseText + '?next=' + location.href;
      } else {
        var errortext = 'Unknown error';

        if (formUtils.statusTexts[jqXHR.status]) {
          errortext = formUtils.statusTexts[jqXHR.status];
        } else if (textStatus === 'timeout') {
          errortext = 'Request timeout';
        }
        $('.autosaved').html('Error: ' + errortext + '<br>If you are seeing errors repeatedly please <a href="/apply/support#contact">contact us</a>');
      }
    }
  });
};

/**------------------------------------ FILE UPLOADS -------------------------------------------**/
var fileUploads = {};

fileUploads.uploading = false;
fileUploads.uploadingSpan = '';
fileUploads.currentField = '';

fileUploads.init = function(urlPrefix, draftId) {
  fileUploads.getUrl = '/get-upload-url/?type=' + urlPrefix + '&id=' + draftId;
  fileUploads.removeUrl = '/' + urlPrefix + '/' + draftId + '/remove/';
  $("[type='file']").change(function() {
      fileUploads.fileChanged(this.id);
    });
  formUtils.log('fileUploads vars loaded, file fields scripted');
  $('.default-file-input').children('a').remove();
};

/* each file field has its own form. html element ids use this pattern:
  input field: 							'id_' + fieldname
  form: 										fieldname + '_form'
  span for upload status: 	fieldname + '_uploaded'
  submit button: 						fieldname + '_submit' */

fileUploads.clickFileInput = function(event, inputId) {
  /* triggered when 'choose file' label is clicked
     transfers the click to the hidden file input */
  formUtils.log('clickFileInput' + inputId);
  var input = document.getElementById(inputId);
  if (input) {
    input.control.click();
  } else {
    formUtils.log('clickFileInput error - no input found with id ' + inputId);
  }
};

/**
 * Update draft when file input is changed.
 *
 * @param fieldId - id of the file field that changed
 *
 * Set as change handler in fileUploads.init. Show loader and get upload url
 **/
fileUploads.fileChanged = function (fieldId) {
  if (fileUploads.uploading) {
    formUtils.log('fileChanged - Upload in progress; returning');
    return false;
  }
  var file = document.getElementById(fieldId).value;
  if (file) {
    fileUploads.uploading = true;
    fileUploads.currentField = fieldId.replace('id_', '');
    fileUploads.uploadingSpan = document.getElementById(fieldId.replace('id_', '') + '_uploaded');
    fileUploads.uploadingSpan.innerHTML = formUtils.loadingImage;
    fileUploads.getUploadURL();
  }
};

/**
 * Fetch blobstore file upload url from backend, then trigger upload.
 *
 * Click hidden submit button for file field to trigger its upload
 */
fileUploads.getUploadURL = function () {
  formUtils.log('getUploadURL calld');
  $.ajax({
    url: fileUploads.getUrl,
    success: function(data) {
      formUtils.log('got upload url for field: ' + fileUploads.currentField);
      var cform = document.getElementById(fileUploads.currentField + '_form');
      cform.action = data;
      var cbutton = document.getElementById(fileUploads.currentField + '_submit');
      cbutton.click();
    }
  });
};

fileUploads.iframeUpdated = function(iframe) { // process response
  formUtils.log('iframeUpdated');
  var results = iframe.contentDocument.body.innerHTML;
  formUtils.log('The iframe changed! New contents: ' + results);
  if (results) {
    var fieldName = results.split('~~')[0];
    var linky = results.split('~~')[1];
    var fileInput = document.getElementById('id_' + fieldName);
    if (fileInput && linky) {
      fileUploads.uploadingSpan.innerHTML = linky;
    } else {
      fileUploads.uploadingSpan.innerHTML = 'There was an error uploading your file. Try again or <a href="/apply/support">contact us</a>.';
    }
    fileUploads.uploading = false;
  }
};

fileUploads.removeFile = function(fieldName) {
  $.ajax({
    url: fileUploads.removeUrl + fieldName + formUtils.staffUser,
    success: function() {
      var rSpan = document.getElementById(fieldName + '_uploaded');
      rSpan.innerHTML = '<i>no file uploaded</i>';
    }
  });
};
