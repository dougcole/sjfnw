'use strict';

var LOADING_IMG = '<img src="/static/images/ajaxloader2.gif" alt="Loading...">';

const AUTOSAVE_ERR_STR = '<br>If you are seeing errors repeatedly please <a href="/apply/support#contact">contact us</a>'

function log(*args) {
  if (namespace.enableLogging) {
    var d = new Date();
    var min = d.getMinutes();
    min = min < 10 ? '0' + min : min;
    var dateString = d.getHours() + ':' + min + ':' + d.getSeconds();

    console.log(dateString, *args);
  }
};

class Draft {
  constructor(options) {
    this.draftType = options.draftType; // 'report' or 'apply'
    this.draftId = options.draftId;
    this.submitId = options.submitId; // cycle or award id
    this.staffUser = options.staffUser;
    this.userId = options.userId || '';
    this.resumeAutosave();
  }

  pauseAutosave() {
    if (window.onfocus) {
      log('autoSave.pause called, but already paused');
      return;
    }
    log('pauseAutosave called; starting pause timer');

    // pause auto save
    this.pauseTimer = window.setTimeout(() => {
      log('Pausing autosave');
      window.clearInterval(this.saveTimer);
      this.pauseTimer = false;
    }.bind(this), INTERVAL_MS);

    $(window).on('focus', this.resumeAutosave.bind(this));
    $(window).off('blur');
  }

  resumeAutosave() {
    if (window.onblur) { // avoid double-firing - if onblur is already set up, skip
      log('resumeAutosave called but window already has onblur; skipping');
      return;
    }

    if (this.pauseTimer) {
      // clear timer if window recently lost focus (in this case autosave is still going)
      log('resumeAutosave called - clearing pause timer');
      window.clearTimeout(this.pauseTimer);
      this.pauseTimer = false;
    } else {
      // was paused or hadn't started - resume autosave
      log('Starting autosave at 60s intreval');
      this.saveTimer = window.setInterval(this.save.bind(this), INTERVAL_MS);
    }

    $(window).on('blur', this.pause.bind(this));
    $(window).off('focus');
  }

  save(submit, force) {
    if (this.staffUser) { // TODO use querystring function
      force = '&force=' + force || 'false';
    } else {
      force = '?force=' + force || 'false';
    }

    log('Autosaving');

    $.ajax({
      url: `/${this.draftType}/${this.submitId}/autosave${this.staffUser}${force}`;
      type: 'POST',
      data: $('form').serialize() + '&user_id=' + this.userId,
      success: this.handleSaveSuccess.bind(this),
      error: this.handleSaveFailure.bind(this)
    });
  }

  handleSaveSuccess(data, textStatus, jqXHR) {
    if (jqXHR.status === 200) {
      if (submit) {
        $('#hidden_submit_app').click(); // trigger the hidden submit button
      } else {
        $('.autosaved').html(getDisplayDateTime()); // update 'last saved'
      }
    } else { // unexpected status code
      this.displayAutosaveError();
    }
  }

  handleSaveFailure(jqXHR, textStatus) {
    var errortext = '';
    if (jqXHR.status === 409)  {
      // conflict - pause autosave and confirm force
      window.clearInterval(this.saveTimer);
      showConflictWarning('autosave'); // TODO method defined in org_app.html
    } else if(jqXHR.status === 401) {
        location.href = jqXHR.responseText + '?next=' + location.href;
    } else {
      var errortext;
      if (STATUS_TEXTS[jqXHR.status]) {
        errortext = STATUS_TEXTS[jqXHR.status];
      } else if (textStatus === 'timeout') {
        errortext = 'Request timeout';
      }
      this.displayAutosaveError(errortext);
    }
  }

  displayAutosaveError(desc) {
    $('.autosaved').html(`${desc || 'Unknown error'}${AUTOSAVE_ERR_STR}`);
  }
}

class FileHandler {

  constructor(urlPrefix, draftId) {
    this.uploading = false;
    this.uploadingSpan = '';
    this.currentField = '';
    this.urls = {
      getUploadUrl: `/get-upload-url/?type=${urlPrefix}&id=${draftId}`,
      removeFile: `/${urlPrefix}/${draftId}/remove/`
    };
    this.setUpListeners();
    $('.default-file-input').children('a').remove(); // TODO why?
    log('fileUploads vars loaded, file fields scripted');
  }

  setUpListeners() {
    $("[type='file']").change(this.handleFileChanged.bind(this));
  }

  handleClick(event, inputId) {
    log(`clickFileInput: ${inputId}`);
    const input = document.getElementById(inputId);
    if (input) {
      input.control.click();
    } else {
      log(`clickFileInput error - no input found with id ${inputId}`);
    }
  }

  handleFileChanged(fieldId) {
    if (this.uploading) {
      log('file changed while upload is in progress; returning');
      return false; // prevent event propagation
    }
    var file = document.getElementById(fieldId).value;
    if (file) {
      this.uploading = true;
      this.currentField = fieldId.replace('id_', '');
      this.uploadingSpan = document.getElementById(fieldId.replace('id_', '') + '_uploaded');
      this.uploadingSpan.innerHTML = LOADING_IMG;
      this.fetchUploadUrl();
    }
  }

  handleIframeUpdated() {
    log('iframeUpdated');
    var results = iframe.contentDocument.body.innerHTML;
    log('The iframe changed! New contents: ' + results);
    if (results) {
      results = results.split('~~');
      var fieldName = results[0];
      var link = results[1];
      var fileInput = document.getElementById('id_' + fieldName);
      if (fileInput && link) {
        uploadingSpan.innerHTML = link;
      } else {
        uploadingSpan.innerHTML = 'There was an error uploading your file. Try again or <a href="/apply/support">contact us</a>.';
      }
      this.uploading = false;
    }
  }

  fetchUploadUrl() {
    log('fetching upload url');
    $.ajax({
      url: this.urls.getUploadUrl,
      success: (data) => {
        log('got upload url for field:', this.currentField);
        var cform = document.getElementById(this.currentField + '_form');
        cform.action = data;
        var cbutton = document.getElementById(this.currentField + '_submit');
        cbutton.click();
      }
    });
  }

  removeFile() {
    $.ajax({
      url: this.urls.removeFile + fieldName + formUtils.staffUser,
      success: function() {
        var rSpan = document.getElementById(fieldName + '_uploaded');
        rSpan.innerHTML = '<i>no file uploaded</i>';
      }
    });
  }
}
