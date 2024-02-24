let url_icap_settings = zzz_https_url + '/z/icap_settings';
let unsaved_html = '<span class="update_fail">Not Saved</span>';
let saving_html = '<span>Saving ICAP Settings...</span>';
let success_html = '<span class="update_success">ICAP Settings Saved</span>';
let error_html = '<span class="update_fail">ERROR Saving ICAP Settings</span>';

let click_to_test_html = '<a class="clickable regex_do_test">test</a>';
let testing_html = '<span class="text_yellow">testing</span>';
let yes_html = '<span class="text_green">yes</span>';
let no_html = '<span class="text_red">no</span>';

let done_loading_data = false;
let icap_upload_found_errors = false;

let regex_compiled = '';
let regex_new_rows_index = 0;
let regex_obj_get_id = /^(new_row|regex_id|main_table_row|new_main_table_row)_(\d+)$/;

let return_data = {
    'post_status': '',
    'post_return_data': ''
};

// apparently "+" doesn't upload, so use "*"
let builtin_regexes = {
    'aside': '(<aside.*?<\/aside>)',
    'iframe': '(<iframe.*?<\/iframe>)',
    'refresh': '(|self\\\.)location\\\.reload\\\(.*?\\\)(|\\\;)',
    'refresh2': '<meta http\-equiv="refresh".*?>',
};
let builtin_types = ['aside', 'iframe', 'refresh'];

// actions: compile_test_regex, delete_regex, load_regexes, save_settings

//-----load the relevant jQuery code for the page-----
function load_js_icap_settings()
{
    // page loads with an empty table, so download the rows
    done_loading_data = false;
    load_table_data();
    
    $('#add_regex_row').click(function() {
        clear_upload_status();
        add_regex_row();
    });
    
    //-----bundle all the settings into a JSON and send it-----
    $('#save_settings').click(function() {
        do_save_icap_settings();
    });
    $('#save_settings2').click(function() {
        do_save_icap_settings();
    });
    
    //aside, iframe, refresh
    $('#add_regex_aside').click(function() {
        add_builtin_regex_row('aside');
    });
    $('#add_regex_iframe').click(function() {
        add_builtin_regex_row('iframe');
    });
    $('#add_regex_refresh').click(function() {
        add_builtin_regex_row('refresh');
    });
    
    $('#toggle_condensed_view').click(function() {
        toggle_condensed_view();
    });

    $('#toggle_nobumpsites').click(function() {
        toggle_nobumpsites();
    });

    $('#edit_nobumpsites').click(function() {
        // url_settings is set in services.js
        window.open(url_settings + '#nobumpsites');
    });

    console.log("ICAP Settings Ready.");
    
    return true;
}

//--------------------------------------------------------------------------------

function toggle_nobumpsites() {
    let is_hidden = $('#nobumpsites').hasClass('hide_item');
    if (is_hidden) {
        $('#nobumpsites').removeClass('hide_item');
        $('#toggle_nobumpsites').html('Hide NoBumpSites');
    } else {
        $('#nobumpsites').addClass('hide_item');
        $('#toggle_nobumpsites').html('Show NoBumpSites');
    }
}

//--------------------------------------------------------------------------------

//TODO: finish this
function toggle_condensed_view() {
    let viewtype = $('#toggle_condensed_view').attr('data-viewtype');
    if (viewtype == 'expanded') {
        $('#toggle_condensed_view').attr('data-viewtype', 'condensed');
        $('#toggle_condensed_view').html('Switch to Expanded View');
    } else {
        $('#toggle_condensed_view').attr('data-viewtype', 'expanded');
        $('#toggle_condensed_view').html('Switch to Condensed View');
    }
}

function is_condensed() {
    let viewtype = $('#toggle_condensed_view').attr('data-viewtype');
    return (viewtype == 'condensed');
}

// table(row id is here) - tbody - tr - td - domain_name/pattern/replacement/notes/enabled
function get_row_id_from_tag(tag_obj) {
    let table_tag = tag_obj.parent().parent().parent().parent();
    let row_id = table_tag.attr('id');
    console.log(`show_test_link() row_id=${row_id}`);
    
    let regex_result = row_id_to_num(row_id);
    if (!regex_result)
    {
        console.log('get_row_id_from_tag() - ERROR getting id_num');
        return ['ERROR', 'ERROR getting id_num'];
    }
    let row_type = regex_result[1];
    let id_num = regex_result[2];

    return [row_type, id_num];
}

function show_not_saved_msg_from_tag(tag_obj) {
    let row_lookup_data = get_row_id_from_tag(tag_obj);
    let row_type = row_lookup_data[0];
    let id_num = row_lookup_data[1];
    show_not_saved_msg(row_type, id_num);
}

//--------------------------------------------------------------------------------

function show_test_link(pattern_tag)
{
    let row_lookup_data = get_row_id_from_tag(pattern_tag);
    let row_type = row_lookup_data[0];
    let id_num = row_lookup_data[1];

    let td_tag_to_modify = null;
    if (row_type=='new_row') { td_tag_to_modify = `#test_link_${id_num}`; }
    else { td_tag_to_modify = `#db_test_link_${id_num}`; }

    //-----skip this if it's already showing-----
    let anchor_tag = $(td_tag_to_modify + ' > a');
    if (! anchor_tag.hasClass('regex_do_test')) {
        $(td_tag_to_modify).html(click_to_test_html);
        // get the new tag
        anchor_tag = $(td_tag_to_modify + ' > a');
    }

    let bound_events = $._data(anchor_tag[0], 'events');
    //-----only attach a click event if there isn't one there already-----
    if (bound_events === undefined) {
        // attach do_test onclick
        anchor_tag.click(function() {
            regex_do_test($(this));
        });
    }

    show_not_saved_msg(row_type, id_num);
}

//--------------------------------------------------------------------------------

//-----new rows don't exist in the DB yet, so just remove them from the HTML-----
function regex_delete_new(new_row_id)
{
    //TEST
    console.log(`deleting from HTML: regex row ${new_row_id}`);
    
    $(`#${new_row_id}`).remove();
}

// input: "123"
function regex_delete(main_table_row_id)
{
    //TEST
    console.log(`deleting from DB: regex row ${main_table_row_id}`);
    
    let regex_result = row_id_to_num(main_table_row_id);
    if (!regex_result)
    {
        console.log('regex_delete() ERROR getting id_num');
        return;
    }
    let row_type = regex_result[1];
    let id_num = regex_result[2];
    console.log(`deleting row_id=${main_table_row_id}, row_type=${row_type}, id_num=${id_num}`);
    
    // submit a delete request to the server
    let postdata = 'action=delete_regex&row_id=' + id_num;

    $.post(url_icap_settings, postdata)
    .done(function(data){
        if (data == 'success') {
            // delete HTML table row
            $(`#${main_table_row_id}`).remove();
        } else {
            show_row_error(row_type, id_num, 'ERROR: delete failed');
        }
    })
    .fail(function(){
        show_row_error(row_type, id_num, 'ERROR: delete POST failed');
        console.log('regex_delete() ERROR: POST failed');
    });
}

// "new_row_123" --> "123"
// "regex_id_123" --> "123"
// "main_table_row_123" --> "123"
// "new_main_table_row_123" --> "123"
function row_id_to_num(row_id)
{
    let result = regex_obj_get_id.exec(row_id);
    return result;
}

//--------------------------------------------------------------------------------

// row_id is for the main table
// EX: main_table_row_123
function get_output_html_tag(row_type, id_num) {
    if (row_type=='new_row') {
        let output_html_tag = $(`#new_compile_message_${id_num}`);
        return output_html_tag;
    }
    
    let output_html_tag = $(`#compile_message_${id_num}`);
    return output_html_tag;
}

//--------------------------------------------------------------------------------

function show_row_error(row_type, id_num, err_msg) {
    let output_html_tag = get_output_html_tag(row_type, id_num);
    let break_tag = '';
    if (is_condensed()) { break_tag = '<br>'; }
    output_html_tag.html(`${break_tag}${err_msg}`);
    output_html_tag.show();
}

function clear_row_error(row_type, id_num) {
    let output_html_tag = get_output_html_tag(row_type, id_num);
    output_html_tag.html('');
    output_html_tag.hide();
}

//--------------------------------------------------------------------------------

// need to submit a compile-test request to the server?
// python regexes may work differently than JS regexes?
function regex_do_test(test_link)
{
    // table(row id is here) - tbody - tr - td - span(compiled_tag) - test_link
    let compiled_tag = test_link.parent();
    let row_id = compiled_tag.parent().parent().parent().parent().attr('id');
    console.log(`regex_do_test() row_id=${row_id}`);
    
    // change status to testing
    compiled_tag.html(testing_html);
    
    let regex_result = row_id_to_num(row_id);
    if (!regex_result)
    {
        console.log('regex_do_test() - ERROR getting id_num');
        return;
    }
    let row_type = regex_result[1];
    let id_num = regex_result[2];
    console.log(`testing regex for row_id=${row_id}, row_type=${row_type}, id_num=${id_num}`);
    
    let output_html_tag = get_output_html_tag(row_type, id_num);
    let regex_pattern = '';
    if (row_type=='new_row') {
        regex_pattern = $(`#new_pattern_${id_num}`).val();
    } else {
        regex_pattern = $(`#pattern_${id_num}`).val();
    }
    console.log(`regex_pattern: ${regex_pattern}`);
    
    // send regex_pattern
    let settings_object = {};
    settings_object.regex_pattern = regex_pattern;
    let settings_data = JSON.stringify(settings_object);
    let postdata = 'action=compile_test_regex&json=' + encodeURIComponent(settings_data);

    $.post(url_icap_settings, postdata)
    .done(function(data){
        if (data == 'success') {
            // test passed
            compiled_tag.html(yes_html);
            output_html_tag.hide();
        } else {
            // test failed
            let break_tag = '';
            if (is_condensed()) { break_tag = '<br>'; }
            output_html_tag.html(`${break_tag}${data}`);
            output_html_tag.show();
            compiled_tag.html(no_html);
        }
    })
    .fail(function(){
        show_row_error(row_type, id_num, 'ERROR: regex test POST failed');
        console.log('regex_do_test() ERROR: POST failed');
    });
}

//--------------------------------------------------------------------------------

// highlight new rows: regex_new_row, queued_for_update, test_regex
function make_regex_tr(main_table_row_id, row_id, regex_new_rows_index, test_link_td, click_to_test_html, pattern_id) {
    if (is_condensed()) {
        let regex_row_template = `
    <tr class="border-yellow" id="${main_table_row_id}"><td colspan="7">
        <table id="${row_id}" class="no_border"><tbody>
        <tr>
            <td class="no_border width_48"><a class="clickable regex_delete_new" data-onclick="${main_table_row_id}">(D)</a></td>
            <td class="no_border width_304"><input type="text" size="40" maxlength="100" id="new_domain_name_${regex_new_rows_index}">
            </td>
            <td class="no_border width_105">
                <span id="${test_link_td}">${click_to_test_html}</span>
                <span id="new_not_saved_${regex_new_rows_index}" class="update_fail">Not Saved</span>
            </td>
            <td class="no_border width_441">
                <input type="text" size="60" maxlength="1024" id="${pattern_id}">
                <span class="hide_item text_red" id="new_compile_message_${regex_new_rows_index}"></span>
            </td>
            <td class="no_border width_63"><input type="checkbox" id="new_enabled_${regex_new_rows_index}" checked="checked"></td>
            <td class="no_border width_441"><input type="text" size="60" maxlength="1024" id="new_replacement_${regex_new_rows_index}"></td>
            <td class="no_border width_441"><input type="text" size="60" maxlength="1024" id="new_notes_${regex_new_rows_index}"></td>
        </tr>
        </tbody></table>
    </td></tr>
            `;
        return regex_row_template;
    }

    let regex_row_template = `
    <tr class="border-yellow" id="${main_table_row_id}"><td>
        <table id="${row_id}" class="no_border"><tbody>
        <tr>
            <td class="no_border"><a class="clickable regex_delete_new" data-onclick="${main_table_row_id}">Delete</a></td>
            <td class="no_border">
                Domain: <input type="text" size="40" maxlength="100" id="new_domain_name_${regex_new_rows_index}">
                <span id="new_not_saved_${regex_new_rows_index}" class="update_fail">Not Saved</span>
            </td>
        </tr>
        <tr>
            <td class="no_border">Compiled OK? <span id="${test_link_td}">${click_to_test_html}</span></td>
            <td class="no_border">
                Regex Pattern: <input type="text" size="60" maxlength="1024" id="${pattern_id}">
            </td>
        </tr>
        <tr>
            <td class="no_border">Enabled: <input type="checkbox" id="new_enabled_${regex_new_rows_index}" checked="checked"></td>
            <td class="no_border">Replacement String: <input type="text" size="60" maxlength="1024" id="new_replacement_${regex_new_rows_index}"></td>
        </tr>
        <tr>
            <td class="no_border" colspan="2">Notes: <input type="text" size="60" maxlength="1024" id="new_notes_${regex_new_rows_index}"></td>
        </tr>
        <tr>
            <td class="no_border">&nbsp;</td>
            <td class="hide_item no_border text_red" id="new_compile_message_${regex_new_rows_index}"></td>
        </tr>
        </tbody></table>
    </td></tr>
    `;
    return regex_row_template;
}

// add an HTML table row with form fields
function add_regex_row()
{
    regex_new_rows_index++;
    
    let row_id = `new_row_${regex_new_rows_index}`;
    let main_table_row_id = `new_main_table_row_${regex_new_rows_index}`;
    let pattern_id = `new_pattern_${regex_new_rows_index}`;
    let test_link_td = `test_link_${regex_new_rows_index}`;
    
    let regex_row_template = make_regex_tr(main_table_row_id, row_id, regex_new_rows_index, test_link_td, click_to_test_html, pattern_id);
    $('#regex_table>tbody').append(regex_row_template);
    
    attach_dynamic_events_icap_settings_new_row(main_table_row_id, pattern_id);

    return row_id;
}

//--------------------------------------------------------------------------------

// built-in regex examples: aside, iframe, refresh
function add_builtin_regex_row(builtin_type) {
    if (! builtin_types.includes(builtin_type)) {
        console.log('ERROR: invalid builtin_type');
        return;
    }
    
    // add a new row to the HTML table
    let row_id = add_regex_row();
    let regex_result = row_id_to_num(row_id);
    let id_num = regex_result[2];
    
    // fill-in the row data fields
    $(`#new_pattern_${id_num}`).val(builtin_regexes[builtin_type]);
    $(`#new_notes_${id_num}`).val(`remove ${builtin_type} from pages`);
    
    // extra regex for refresh:
    if (builtin_type=='refresh') {
        let row_id2 = add_regex_row();
        let regex_result2 = row_id_to_num(row_id2);
        let id_num2 = regex_result2[2];
        $(`#new_pattern_${id_num2}`).val(builtin_regexes.refresh2);
        $(`#new_notes_${id_num2}`).val(`remove ${builtin_type} from pages`);
    }
    
    //TODO: scroll the new entry into view
    $(`#new_domain_name_${id_num}`).focus();
}

//--------------------------------------------------------------------------------

// regex pattern fields are sent from the server in JSON, make them readable to the user
function load_data_fields(json_row_data)
{
    for (const [id_num, domain_name] of Object.entries(json_row_data.field_data.domain_name)) {
        $(`#domain_name_${id_num}`).val(domain_name);
    }
    
    for (const [id_num, pattern] of Object.entries(json_row_data.field_data.pattern)) {
        $(`#pattern_${id_num}`).val(pattern);
    }
    
    for (const [id_num, replacement] of Object.entries(json_row_data.field_data.replacement_str)) {
        $(`#replacement_${id_num}`).val(replacement);
    }
    
    for (const [id_num, notes] of Object.entries(json_row_data.field_data.notes)) {
        $(`#notes_${id_num}`).val(notes);
    }
}

//--------------------------------------------------------------------------------

//-----used for existing rows from the DB, on initial page load------
// related function for new rows: attach_dynamic_events_icap_settings_new_row()
function attach_dynamic_events_icap_settings()
{
    //TODO: on change of domain_name, run the domain_name verification
    $('[id^="domain_name_"]').each(function(){
        $(this).change(function() {
            clear_upload_status();
            show_not_saved_msg_from_tag($(this));
        });
    });

    //TODO: just run the regex compile test
    // on change of regex, switch yes/no compile status to a "test" link
    $('[id^="pattern_"]').each(function(){
        $(this).change(function() {
            clear_upload_status();
            show_test_link($(this));
        });
        $(this).keydown(function() {
            clear_upload_status();
            show_test_link($(this));
        });
    });
    
    // make the delete buttons work on all rows
    $(".regex_delete").click(function() {
        regex_delete($(this).attr("data-onclick"));
    });

    // on change of any field, show the "Not Saved" indicator
    //   show_not_saved_msg_from_tag(tag_obj);
    //   domain_name_ - done above
    //   pattern_ - done above
    // replacement_
    $('[id^="replacement_"]').each(function(){
        $(this).change(function() {
            clear_upload_status();
            show_not_saved_msg_from_tag($(this));
        });
    });
    // notes_
    $('[id^="notes_"]').each(function(){
        $(this).change(function() {
            clear_upload_status();
            show_not_saved_msg_from_tag($(this));
        });
    });
    // enabled_
    $('[id^="enabled_"]').each(function(){
        $(this).change(function() {
            clear_upload_status();
            show_not_saved_msg_from_tag($(this));
        });
    });
}

//-----used when a new row is added-----
function attach_dynamic_events_icap_settings_new_row(main_table_row_id, pattern_id) {
    // on change of regex, switch yes/no compile status to a "test" link
    let pattern_tag = $(`#${pattern_id}`);
    pattern_tag.change(function() {
        clear_upload_status();
        show_test_link($(`#${pattern_id}`));
    });
    pattern_tag.keydown(function() {
        clear_upload_status();
        show_test_link($(`#${pattern_id}`));
    });

    //-----delete button-----
    let anchor_tag= $(`#${main_table_row_id} > td > table > tbody > tr > td:first-child > a`);
    anchor_tag.click(function() {
        regex_delete_new($(this).attr("data-onclick"));
    });
}

function load_table_data()
{
    icap_condensed=$('#toggle_condensed_view').attr('data-viewtype');
    postdata=`action=load_regexes&icap_condensed=${icap_condensed}`;

    $.post({
        'url': url_icap_settings,
        'data': postdata,
        'success': null,
        'dataType': 'json' // html, json, script, text, xml
    })
    .done(function(data){
        $('#regex_table').hide();
        $('#regex_table>tbody').html(data.html_table_rows);
            
        load_data_fields(data);
        attach_dynamic_events_icap_settings();
        
        $('#regex_table').show();
    })
    .fail(function(){
        console.log('load_table_data() ERROR: POST failed');
    });
}

//--------------------------------------------------------------------------------

//TODO: put all postdata in one big array, then stringify the array
// postdata for uploading all settings
function make_postdata()
{
    let settings_object = {};
    icap_upload_found_errors = false;
    
    // table(id=regex_table)
    //   tbody
    //     tr(id="main_table_row_1")
    //       td
    //         table(id="regex_id_1") - for entries existing in the DB
    //           tbody
    //           tr
    //             td
    //               input(id="domain_name_1")
    //               input(id="pattern_1")
    //               checkbox(id="enabled_1")
    //               input(id="replacement_1")
    //               input(id="notes_1")
    //             td(id="compile_message_1") - read-only, hidden unless there is an error
    //     tr(id="new_main_table_row_1")
    //       td
    //         table(id="new_row_1") - for new entries not yet saved to the DB
    //           tbody
    //           tr
    //             td
    //               input(id="new_domain_name_1")
    //               input(id="new_pattern_1")
    //               checkbox(id="new_enabled_1")
    //               input(id="new_replacement_1")
    //               input(id="new_notes_1")
    //             td(id="new_compile_message_1") - read-only, hidden unless there is an error
    //
    //let table_tag = pattern_tag.parent().parent().parent().parent();
    //let row_id = table_tag.attr('id');
    
    // assemble all the data into a big json
    
    // existing patterns to update
    // UPDATES: main_table_row_*
    settings_object.updates = [];
    $('[id^="regex_id_"]').each(function(){
        let row_id = $(this).attr('id');
        let regex_result = row_id_to_num(row_id);
        if (!regex_result)
        {
            console.log('make_postdata() - ERROR getting id_num from ' + row_id);
            return;
        }
        let row_type = regex_result[1];
        let id_num = regex_result[2];
        
        let regex_pattern = $('#pattern_'+id_num).val();
        if (regex_pattern.length==0) {
            // compile_message_
            show_row_error(row_type, id_num, 'ERROR: empty regex');
            icap_upload_found_errors = true;
        } else {
            clear_row_error(row_type, id_num);
        }
        
        let regex_enabled = 'false';
        if ($('#enabled_'+id_num).is(':checked')) { regex_enabled = 'true'; }
        
        let update_row = {
            'id': id_num,
            'enabled': regex_enabled,
            'domain_name': $('#domain_name_'+id_num).val(),
            'pattern': regex_pattern,
            //TODO: add flags checkboxes
            'flags': [],
            'replacement_str': $('#replacement_'+id_num).val(),
            'notes': $('#notes_'+id_num).val(),
        };
        settings_object.updates.push(update_row);
        
        //TEST
        console.log(`regex update id_num=${id_num}`);
        
        //TODO: missing important fields? (regex_json)
        //      mark border as red
        //      don't send
        //let err_msg = $(`main_table_row_${id_num}`);
    });
    
    // new patterns
    // INSERTS: new_row_*
    settings_object.inserts = [];
    $('[id^="new_row_"]').each(function(){
        //TEST
        let row_id = $(this).attr('id');
        let regex_result = row_id_to_num(row_id);
        if (!regex_result)
        {
            console.log('make_postdata() - ERROR getting id_num from ' + row_id);
            return;
        }
        let row_type = regex_result[1];
        let id_num = regex_result[2];
        
        let regex_pattern = $('#new_pattern_'+id_num).val();
        if (regex_pattern.length==0) {
            // compile_message_
            show_row_error(row_type, id_num, 'ERROR: empty regex');
            icap_upload_found_errors = true;
        } else {
            clear_row_error(row_type, id_num);
        }
        
        let regex_enabled = 'false';
        if ($('#new_enabled_'+id_num).is(':checked')) { regex_enabled = 'true'; }
        
        let insert_row = {
            'enabled': regex_enabled,
            'domain_name': $('#new_domain_name_'+id_num).val(),
            'pattern': regex_pattern,
            //TODO: add flags checkboxes
            'flags': [],
            'replacement_str': $('#new_replacement_'+id_num).val(),
            'notes': $('#new_notes_'+id_num).val(),
        };
        settings_object.inserts.push(insert_row);
        
        //TEST
        console.log(`new row id_num=${id_num}`);
    });
    
    let settings_data = JSON.stringify(settings_object);
    //TEST
    console.log(settings_data);
    
    //let postdata = 'action=save_settings&json=' + settings_data;
    let result = {
        'postdata': 'action=save_settings&json=' + encodeURIComponent(settings_data),
        'found_errors': icap_upload_found_errors,
    };
    return result;
}

//--------------------------------------------------------------------------------

function show_not_saved_msg(row_type, id_num) {
    if (row_type=='new_row') {
        $(`#new_not_saved_${id_num}`).html('Not Saved');
    } else {
        $(`#not_saved_${id_num}`).html('Not Saved');
    }
}

//-----clears all status messages-----
function clear_icap_settings_status() {
}

function show_error(error_output_details) {
    $('#error_output_details').html(error_output_details);
    $('#error_output_details2').html(error_output_details);
}

function clear_upload_status() {
    $('#status_save_settings').html('');
    $('#status_save_settings2').html('');
    $('#error_output_details').html('');
    $('#error_output_details2').html('');
}

function show_saving_in_progress() {
    $('#status_save_settings').html(saving_html);
    $('#status_save_settings2').html(saving_html);
}

//--------------------------------------------------------------------------------

//-----upload all settings in one big JSON-----
//function upload_settings(action, regex_pattern, output_html_tag, compiled_tag) {
function upload_settings() {
    show_saving_in_progress();
    
    //let postdata = 'action=' + action + '&json=' + settings_data;
    console.log('make_postdata()');
    //let postdata = make_postdata();
    let result = make_postdata();
    if (result.found_errors) {
        show_error('ERROR validating data. Rows with errors have a red border.');
        $('#status_save_settings').html(error_html);
        $('#status_save_settings2').html(error_html);
        return;
    }
    
    //TEST
    //console.log('postdata: ' + postdata);

    $.post(url_icap_settings, result.postdata)
    .done(function(data){
        if (data == 'success') {
            clear_icap_settings_status();
            $('#status_save_settings').html(success_html);
            $('#status_save_settings2').html(success_html);
            load_table_data();
        } else {
            show_error('upload_settings() ERROR: ');
            $('#status_save_settings').html(error_html);
            $('#status_save_settings2').html(error_html);
        }
    })
    .fail(function(){
        console.log('upload_settings() ERROR: POST failed');
        show_error('ERROR: POST failed');
        $('#status_save_settings').html(error_html);
        $('#status_save_settings2').html(error_html);
    });
}

//--------------------------------------------------------------------------------

function do_save_icap_settings() {
    console.log('do_save_icap_settings()');
    
    show_saving_in_progress();
    
    upload_settings();
}

//--------------------------------------------------------------------------------

