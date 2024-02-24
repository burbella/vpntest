console.log("list_manager.js - START");

let unsaved_html = '<span class="update_fail">Not Saved</span>';

function load_js_list_manager() {
    $('#download_lists').click(function() {
        download_lists();
    });

    $('#save_changes').click(function() {
        save_changes();
    });

    attach_onclick_list_manager();

    attach_content_collapsed_toggle();
}

function load_js_list_edit() {
    if ($('#entries').prop('readonly')) {
        $('#edit_list_save_changes').hide();
    }

    $('#edit_list_save_changes').click(function() {
        edit_list_save_changes($(this).attr("data-onclick"));
    });

    $('#entries').change(function(){
        $('#status_save_changes').html(unsaved_html);
    });

    $('#list_name').change(function(){
        $('#status_save_changes').html(unsaved_html);
    });

    $('#list_url').change(function(){
        $('#status_save_changes').html(unsaved_html);
    });
}

function load_js_list_add() {
    $('#add_list_save_changes').click(function() {
        add_list_save_changes();
    });
}

function load_js_list_delete() {
    $('#delete_list').click(function() {
        delete_list($(this).attr("data-onclick"));
    });
}

//--------------------------------------------------------------------------------

function attach_onclick_list_manager() {
    $('.list_manager_is_active').click(function() {
        show_not_saved($(this).attr("data-onclick"));
    });

    $('.list_manager_auto_update').click(function() {
        show_not_saved($(this).attr("data-onclick"));
    });

    $('.entry_delete').click(function() {
        delete_entry($(this).attr("data-onclick"));
    });

    $('.list_delete').click(function() {
        delete_list_html($(this).attr("data-onclick"));
    });

    $('.list_edit').click(function() {
        edit_list($(this).attr("data-onclick"));
    });

    $('.list_view').click(function() {
        view_list($(this).attr("data-onclick"));
    });
}

//--------------------------------------------------------------------------------

function delete_list(list_id) {
    console.log(`delete_list list_id=${list_id}`);

    let postdata = `action=delete_list&list_id=${list_id}`;
    let status_field = $('#status_delete_list');
    let success_html = '<span class="update_success">List Deleted</span>';
    let error_html = '<span class="update_fail">ERROR</span>';
    let delete_button_html = `<a id="delete_list" class="clickable" data-onclick="${list_id}">Delete List</a>`;

    status_field.html('');
    $('#delete_button').html('<span class="warning_text">Deleting List...</span>');

    $.post({
        'url': url_list_manager,
        'data': postdata,
        'success': null,
        'dataType': 'json' // html, json, script, text, xml
    })
    .done(function(data){
        if (data.status=='success') {
            $('#delete_button').html(success_html);
        } else {
            console.log(data.error_msg);
            let error_html = `<span class="update_fail">ERROR: ${data.error_msg}</span>`;
            status_field.html(error_html);
            $('#delete_button').html(delete_button_html);
        }
    })
    .fail(function(){
        console.log('delete_list() POST failed');
        status_field.html(error_html);
        $('#delete_button').html(delete_button_html);
    });
}

//--------------------------------------------------------------------------------

function delete_entry(entry_id) {
    console.log(`delete entry_id=${entry_id}`);

    let postdata = `action=delete_entry&entry_id=${entry_id}`;
    let status_field = $(`#status_delete_entry_${entry_id}`);
    let success_html = '<span class="update_success">Deleted</span>';
    let error_html = '<span class="update_fail">ERROR</span>';

    $.post({
        'url': url_list_manager,
        'data': postdata,
        'success': null,
        'dataType': 'json' // html, json, script, text, xml
    })
    .done(function(data){
        if (data.status=='success') {
            status_field.html(success_html);
        } else {
            console.log(data.error_msg);
            let error_html = `<span class="update_fail">ERROR: ${data.error_msg}</span>`;
            status_field.html(error_html);
        }
    })
    .fail(function(){
        console.log(`delete_entry(${entry_id}) POST failed`);
        status_field.html(error_html);
    });
}

//--------------------------------------------------------------------------------

function edit_list(list_id) {
    window.open(url_list_manager + '?action=edit_list&list_id=' + list_id);
}

function view_list(list_id) {
    window.open(url_list_manager + '?action=view_list&list_id=' + list_id);
}

function delete_list_html(list_id) {
    window.open(url_list_manager + '?action=delete_list&list_id=' + list_id);
}

function show_not_saved(list_id) {
    $(`#show_not_saved_${list_id}`).html(unsaved_html);
    $('#status_save_changes').html(unsaved_html);
}

function clear_upload_status() {
    $('#status_save_changes').html('');
}

function clear_list_status() {
    $('span[id^=show_not_saved_]').html('');
}

//--------------------------------------------------------------------------------

function download_lists() {
    let postdata = 'action=download_lists';
    let status_field = $('#status_download_lists');
    let success_html = '<span class="update_success">Download request queued</span>';
    let error_html = '<span class="update_fail">ERROR requesting download</span>';

    $.post({
        'url': url_list_manager,
        'data': postdata,
        'success': null,
        'dataType': 'json' // html, json, script, text, xml
    })
    .done(function(data){
        if (data.status=='success') {
            status_field.html(success_html);
        } else {
            console.log(data.error_msg);
            let error_html = `<span class="update_fail">ERROR requesting download: ${data.error_msg}</span>`;
            status_field.html(error_html);
        }
    })
    .fail(function(){
        console.log('download_lists() POST failed');
        status_field.html(error_html);
    });
}

//--------------------------------------------------------------------------------

//-----assemble the data into a big JSON-----
function make_json() {
    let list_object = {};

    list_object.active_lists = [];
    $('.list_manager_is_active').each(function(){
        if ($(this).is(':checked')) {
            list_object.active_lists.push($(this).attr('data-onclick'));
        }
    });

    list_object.auto_update = [];
    $('.list_manager_auto_update').each(function(){
        if ($(this).is(':checked')) {
            list_object.auto_update.push($(this).attr('data-onclick'));
        }
    });

    // dictionary of dictionaries
    $('.list_manager_is_active').each(function(){
        let list_id = $(this).attr('data-onclick');
        let is_active = 0;
        if ($(`#is_active_${list_id}`).is(':checked')) { is_active = 1; }
        let auto_update = 0;
        if ($(`#auto_update_${list_id}`).is(':checked')) { auto_update = 1; }

        list_object[list_id] = {
            'is_active': is_active,
            'auto_update': auto_update,
        };
    });

    let list_data = JSON.stringify(list_object);

    return list_data;
}

//--------------------------------------------------------------------------------

function save_changes() {
    clear_upload_status();

    let postdata = 'action=save_changes&json=' + encodeURIComponent(make_json());
    let status_field = $('#status_save_changes');
    let success_html = '<span class="update_success">Changes Saved</span>';
    let error_html = '<span class="update_fail">ERROR Saving Changes</span>';

    $.post({
        'url': url_list_manager,
        'data': postdata,
        'success': null,
        'dataType': 'json' // html, json, script, text, xml
    })
    .done(function(data){
        if (data.status=='success') {
            clear_list_status();
            status_field.html(success_html);
        }
        else {
            let error_html = `<span class="update_fail">${data.error_msg}</span>`;
            status_field.html(error_html);
        }
    })
    .fail(function(){
        console.log('save_changes() POST failed');
        status_field.html(error_html);
    });
}

//--------------------------------------------------------------------------------

function edit_list_make_json(list_id) {
    let list_object = {};

    list_object.list_id = list_id;
    list_object.entries = $('#entries').val();
    list_object.list_name = $('#list_name').val();
    list_object.list_url = $('#list_url').val();

    let entries_data = JSON.stringify(list_object);

    return entries_data;
}

function edit_list_save_changes(list_id) {
    console.log(`edit_list_save_changes(${list_id})`);

    let success_html = '<span class="update_success">Changes Saved</span>';
    let error_html = '<span class="update_fail">ERROR Saving Changes</span>';

    if ($('#entries').prop('readonly')) {
        console.log('List is Readonly');
        $('#status_save_changes').html(error_html);
        return;
    }

    let status_field = $('#status_save_changes');
    let postdata = 'action=save_entries&json=' + encodeURIComponent(edit_list_make_json(list_id));

    $.post({
        'url': url_list_manager,
        'data': postdata,
        'success': null,
        'dataType': 'json' // html, json, script, text, xml
    })
    .done(function(data){
        if (data.status=='success') {
            status_field.html(success_html);
            clear_list_status();
        } else {
            error_html = `<span class="update_fail">${data.error_msg}</span>`;
            status_field.html(error_html);
        }
    })
    .fail(function(){
        status_field.html(error_html);
        console.log('edit_list_save_changes() POST failed');
    });
}

//--------------------------------------------------------------------------------

function add_list_make_json() {
    let list_object = {};

    list_object.list_name = $('#list_name').val();
    list_object.list_url = $('#list_url').val();
    list_object.list_type = $('#list_type').val();

    let entries_data = JSON.stringify(list_object);

    return entries_data;
}

function add_list_save_changes() {
    console.log('add_list_save_changes()');

    let postdata = 'action=add_list&json=' + encodeURIComponent(add_list_make_json());
    let status_field = $('#status_save_changes');
    let success_html = '<span class="update_success">List Added</span>';
    let error_html = '<span class="update_fail">ERROR Adding List</span>';

    status_field.html('');

    $.post({
        'url': url_list_manager,
        'data': postdata,
        'success': null,
        'dataType': 'json' // html, json, script, text, xml
    })
    .done(function(data){
        if (data.status=='success') {
            $('#add_button').html(success_html);
        } else {
            console.log(data.error_msg);
            let error_html = `<span class="update_fail">ERROR Adding List: ${data.error_msg}</span>`;
            status_field.html(error_html);
        }
    })
    .fail(function(){
        console.log('add_list_save_changes() POST failed');
        status_field.html(error_html);
    });
}

//--------------------------------------------------------------------------------

console.log("list_manager.js - LOADED");
