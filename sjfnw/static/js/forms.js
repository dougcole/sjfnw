'use strict';

/**----------------------------- formUtils ---------------------------------**/
var formUtils = {};

/**
 * Log message to console, if window._sjfDebug flag is set. Adds timestamp.
 *
 * @param {string} message
 */
formUtils.log = function (message) {
  if (!window._sjfDebug) {
    return;
  }
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
 * Initialize forms-related javascript. Must be called in template.
 * 1) Stores given staff override
 * 2) Initializes autosave (see autoSave.init)
 * 3) Initializes file upload handling (see fileUploads.init)
 *
 * @param {string} urlPrefix - beginning of path (i.e. 'apply'). no slashes
 * @param {number} draftId - pk of draft object (draft app or draft report)
 * @param {number} submitId - pk of object used in post (cycle or award)
 * @param {string.alphanum} userId - randomly generated user id for mult edit warning
 * @param {string} [staffUser] - querystring for user override (empty string if n/a)
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
 * Get current time as a string for display.
 *
 * @returns {string} Current datetime in format "May 12, 2:45p.m."
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


var wordLimiter = {};

/**
 * Add word count display before each textarea with .wordlimited.
 * Updates the display on keyup.
 */
wordLimiter.init = function () {
  var word_limited = $('textarea.wordlimited');
  word_limited.after(function () {
    return '<div class="wordcount" id="' + this.name + '_wordcount"></div>';
  });
  word_limited.on('keyup', wordLimiter.handleKeyUp)
  word_limited.keyup();
};

/**
 * Update word limit indicator for text field.
 *
 * Uses event.target's `data-limit` attr; no-op if that is not set.
 *
 * @param {jQuery.Event} event - jQuery keyup event
 */
wordLimiter.handleKeyUp = function (event) {
  var area = event.target;
  if (!area.dataset.limit) return;

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
  var diff = area.dataset.limit - word_count;

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
  INITIAL_DELAY_MS: 10000,
};


autoSave.init = function(urlPrefix, submitId, userId) {
  var baseUrl = '/' + urlPrefix + '/' + submitId;
  autoSave.saveUrl = baseUrl + '/autosave' + formUtils.staffUser;
  autoSave.submitUrl = baseUrl + formUtils.staffUser;
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

autoSave.save = function (submit, force) {
  if (formUtils.staffUser) { // TODO use querystring function
    force = '&force=' + force || 'false';
  } else {
    force = '?force=' + force || 'false';
  }

  formUtils.log('Autosaving');

  $.ajax({
    url: autoSave.saveUrl + force,
    type: 'POST',
    data: $('input,textarea').serialize() + '&user_id=' + autoSave.userId,
    success: function (data, textStatus, jqXHR) {
      if (jqXHR.status === 200) {
        if (submit) {
          // button click - trigger the hidden submit button
          var submitAll = document.getElementById('hidden_submit_app');
          submitAll.click();
        } else {
          // autosave - update 'last saved'
          $('.autosaved').html(formUtils.currentTimeDisplay());
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
        } else if (formUtils.statusTexts[jqXHR.status]) {
          errortext = formUtils.statusTexts[jqXHR.status];
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
var fileUploads = {};

fileUploads.uploading = false;
fileUploads.uploadingSpan = '';
fileUploads.currentField = '';

/**
 * Set up file fields.
 *
 * @param {string} urlPrefix - Beginning of url. Examples: 'apply', 'report'
 * @param {number} draftId - Pk of draft
 */
fileUploads.init = function(urlPrefix, draftId) {
  fileUploads.getUrl = '/get-upload-url/?type=' + urlPrefix + '&id=' + draftId;
  fileUploads.removeUrl = '/' + urlPrefix + '/' + draftId + '/remove/';
  $("[type='file']").change(fileUploads.handleFileChanged);
  $('#id_upload_frame').load(fileUploads.handleIframeUpdated);
  formUtils.log('fileUploads vars loaded, file fields scripted');
  $('.default-file-input').children('a').remove();
};

/**
 * Update draft when file input is changed.
 *
 * Set as change handler in fileUploads.init. Show loader and get upload url
 *
 * @param {jQuery.Event} ev
 **/
fileUploads.handleFileChanged = function (ev) {
  if (fileUploads.uploading) {
    formUtils.log('File changed - Upload still in progress; returning');
    return false;
  }
  var id = ev.target.id;
  var file = document.getElementById(id).value;
  if (file) {
    fileUploads.uploading = true;
    fileUploads.currentField = id.replace('id_', '');
    fileUploads.uploadingSpan = document.getElementById(fileUploads.currentField + '_uploaded');
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

/**
 * Handles iframe update which indicates a server response to a file upload request
 *
 * @param {jQuery.Event} ev
 */
fileUploads.handleIframeUpdated = function (ev) {
  formUtils.log('iframeUpdated');
  var res;
  try {
    res = JSON.parse(ev.target.contentDocument.body.innerText);
    formUtils.log('The iframe changed! New contents: ' + res);
  } catch (err) {
    formUtils.log('Error trying to parse response: ' + err.message);
  }
  if (res) {
    var fileInput = document.getElementById('id_' + res.field);
    if (fileInput && res.url && res.filename) {
      fileUploads.uploadingSpan.innerHTML = [
        '<a href="', res.url, '" target="_blank">', res.filename, '</a>'
      ].join('');
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
