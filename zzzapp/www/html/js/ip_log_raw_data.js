//-----IP Log Raw Data UI-----
// this JS assumes that services.js has been loaded in the page already

var test_mode_ip_log_raw_data = false;

var ip_log_raw_data_logfile_timer = null;
// 60 seconds between logfile menu updates
var ip_log_raw_data_logfile_timer_interval = 60000;
var last_menu_update_time = 0;
var date_obj_ip_log_raw_data = new Date();

var clear_status_save_log_timer = null;

var ip_log_raw_data_checkbox_fields = ['auto_update_file_list', 'connection_external', 'connection_inbound', 'connection_internal', 'connection_outbound', 'extra_analysis', 'flags_any', 'flags_none', 'include_accepted_packets', 'include_blocked_packets', 'prec_tos_zero', 'prec_tos_nonzero', 'protocol_tcp', 'protocol_udp', 'protocol_icmp', 'protocol_other', 'show_max_bps_columns'];

//-----load the relevant jQuery code for the page-----
function load_js_ip_log_raw_data()
{
    //-----events for the IP-block clear/submit buttons-----
    load_js_ip_log_common();

    //-----select the option that was used last time-----
    set_sort_by();

    //-----show/hide buttons-----
    $('#show_hide_src_ip_analysis').click(function() {
        show_hide_object('src_ip_analysis', 'show_hide_src_ip_analysis', 'Show Source IP Analysis', 'Hide Source IP Analysis');
    });
    $('#show_hide_dst_ip_analysis').click(function() {
        show_hide_object('dst_ip_analysis', 'show_hide_dst_ip_analysis', 'Show Destination IP Analysis', 'Hide Destination IP Analysis');
    });
    $('#show_hide_extra_analysis_output').click(function() {
        show_hide_object('extra_analysis_output', 'show_hide_extra_analysis_output', 'Show Extra Analysis', 'Hide Extra Analysis');
    });
    $('#show_hide_logdata').click(function() {
        show_hide_object('logdata', 'show_hide_logdata', 'Show Raw Data', 'Hide Raw Data');
    });
    
    // clicking on the auto_update_file_list checkbox should trigger an immediate update if it has been more than 60 seconds since the last update
    $('#auto_update_file_list').click(function() {
        // return if the box is not checked
        if (! $('#auto_update_file_list').is(':checked')) {
            return;
        }

        // if the box is checked, restart the timer
        // give it an extra second to avoid a race condition with the timer
        if (time_since_last_menu_update() > (ip_log_raw_data_logfile_timer_interval + 1000)) {
            stop_logfile_timer();
            start_logfile_timer();
            get_logfile_menu();
        }
    });

    $('#view_raw_text').click(function() {
        view_raw_text('live');
    });

    $('#saved_view_raw_text').click(function() {
        view_raw_text('saved');
    });

    $('#view_previous_log').click(function() {
        view_log('previous_log');
    });

    $('#view_log').click(function() {
        view_log('current_log');
    });

    $('#view_next_log').click(function() {
        view_log('next_log');
    });

    $('#view_saved_log').click(function() {
        view_log('saved_log');
    });

    $('#save_log').click(function() {
        save_log();
    });

    $('#confirm_delete_log').click(function() {
        delete_log();
    });

    $('#confirm_delete_all_logs').click(function() {
        delete_all_logs();
    });

    $('#confirm_reset_search').click(function() {
        reset_search();
    });

    start_clock();
    start_logfile_timer();
    show_saved_logfile_menu();

    //-----double-check if the user really wants to delete the selected save file-----
    attach_click_events_start_cancel('delete_log', 'confirm_delete_log', 'cancel_delete_log');
    //-----double-check if the user really wants to delete all saved files-----
    attach_click_events_start_cancel('delete_all_logs', 'confirm_delete_all_logs', 'cancel_delete_all_logs');
    //-----double-check if the user really wants to reset search fields-----
    attach_click_events_start_cancel('reset_search', 'confirm_reset_search', 'cancel_reset_search');

    console.log("ip_log_raw_data Ready.");

    return true;
}

//--------------------------------------------------------------------------------

//-----only show the menu if it's not empty-----
function show_saved_logfile_menu() {
    let saved_logfile_menu = $('#saved_logfile_menu').html();
    if (saved_logfile_menu == '') {
        $('#saved_logs_section').hide();
    } else {
        $('#saved_logs_section').show();
    }
}

function start_logfile_timer() {
    ip_log_raw_data_logfile_timer = setInterval(get_logfile_menu, ip_log_raw_data_logfile_timer_interval);
}

function stop_logfile_timer() {
    clearInterval(ip_log_raw_data_logfile_timer);
}

function time_since_last_menu_update() {
    let elapsed = date_obj_ip_log_raw_data.getTime() - last_menu_update_time;
    return elapsed;
}

//--------------------------------------------------------------------------------

function hide_stuff_before_dom_update(filename='') {
    $('#show_all_data').hide();

    $('#view_previous_log').hide();
    $('#view_log').hide();
    $('#view_next_log').hide();
    $('#view_saved_log').hide();

    $('#view_raw_text').hide();
    $('#saved_view_raw_text').hide();

    $('#logdata_misc_info').hide();
    $('#extra_analysis_output').hide();

    $('#loading_msg').html(`Loading ${filename}...`);
}

function show_buttons() {
    $('#view_previous_log').show();
    $('#view_log').show();
    $('#view_next_log').show();
    $('#view_saved_log').show();
    $('#view_raw_text').show();
    $('#saved_view_raw_text').show();
}

//--------------------------------------------------------------------------------

function set_sort_by() {
    // clear all selected options
    $('#sort_by>option').each(function() {
        $(this).removeAttr("selected");
    });

    // select the option that was used last time
    let last_query = $('#sort_by').attr("data-last-query");
    $('#sort_by>option').each(function() {
        let sort_by = $(this).val();
        if (sort_by == last_query) {
            $(this).attr("selected", "selected");
        }
    });
}

//--------------------------------------------------------------------------------

function process_checkboxes() {
    checkbox_url_params = '';
    for (let i=0; i<ip_log_raw_data_checkbox_fields.length; i++) {
        let field = ip_log_raw_data_checkbox_fields[i];
        let is_checked = String($('#'+field).is(':checked'));
        checkbox_url_params += `&${field}=${is_checked}`;
    }
    return checkbox_url_params;
}

//--------------------------------------------------------------------------------

function hide_stuff_before_save_log(msg='') {
    $('#save_log').hide();
    $('#save_this_log').hide();

    $('#loading_msg').html(msg);
}

function clear_status_save_log() {
    $('#save_log').show();
    $('#save_this_log').show();
    $('#loading_msg').html('');
}

//--------------------------------------------------------------------------------

function save_log(filename_to_use='') {
    clearTimeout(clear_status_save_log_timer);

    let status_field = $('#loading_msg');
    let filename = $('#logfile>option:selected').val();
    if (filename_to_use != '') {
        filename = filename_to_use;
    }

    // not allowed to save the current log file for now
    if (filename == 'ipv4.log') {
        status_field.html(`<span class="warning_text">ERROR: Not allowed to save the current log file</span>`);
        //-----auto-clear the message after a short time-----
        clear_status_save_log_timer = setTimeout(clear_status_save_log, 1000);
        return;
    }

    setTimeout(hide_stuff_before_save_log, 1, `Saving ${filename}...`);

    let save_start_time_ms = Date.now();
    let postdata = `action=save_logfile&filename=${filename}`;
    $.post({
        'url': url_ip_log_raw_data,
        'data': postdata,
        'success': null,
        'dataType': 'json' // html, json, script, text, xml
    })
    .done(function(data){
        if (data.status == 'error') {
            status_field.html(`ERROR: ${data.error_msg}`);
            return;
        }
        
        // update the saved logfile menu and sort it
        current_menu_html = $('#saved_logfile_menu').html();
        $('#saved_logfile_menu').html(`${data.saved_logfile_menu_entry}\n${current_menu_html}`);

        // highlight the saved log file in the logfile menu
        $('#logfile>option:selected').addClass('text_green');

        if (filename != '') {
            $('#save_this_log').html('(Log is already saved)');
            $('#save_this_log').show();
        }
    })
    .fail(function(){
        status_field.html('ERROR: AJAX failed');
    })
    .always(function(){
        //-----auto-clear the message after a short time-----
        // status_ip_log_parse_now_timer = setTimeout(clear_status_ip_log_parse_now, 3000);
        // keep the saving message up for a short time
        let save_runtime = Date.now() - save_start_time_ms;
        let sleep_time = 1000 - save_runtime;
        if (sleep_time <= 0) { sleep_time = 1; }
        setTimeout(clear_status_save_log, sleep_time)
        $('#saved_logs_section').show();
    });
}

//--------------------------------------------------------------------------------

function delete_log() {
    if (clear_status_save_log_timer != null) {
        clearTimeout(clear_status_save_log_timer);
    }
    let filename = $('#saved_logfile_menu>option:selected').val();

    setTimeout(hide_stuff_before_save_log, 1, `Deleting ${filename}...`);

    let status_field = $('#loading_msg');
    let postdata = `action=delete_logfile&filename=${filename}`;
    $.post({
        'url': url_ip_log_raw_data,
        'data': postdata,
        'success': null,
        'dataType': 'json' // html, json, script, text, xml
    })
    .done(function(data){
        if (data.status == 'error') {
            status_field.html(`ERROR: ${data.error_msg}`);
            return;
        }

        // remove the file from the saved logfile menu
        $('#saved_logfile_menu>option:selected').remove();

        // find the filename in the logfile menu and remove the highlighting
        $(`#logfile>option[value='${filename}']`).removeClass('text_green');

        // hide the saved logfile menu if it's empty
        if ($('#saved_logfile_menu').html() == '') {
            $('#saved_logs_section').hide();
        }
    })
    .fail(function(){
        status_field.html('ERROR: AJAX failed');
    })
    .always(function(){
        setTimeout(clear_status_save_log, 1000);
        switch_confirm_to_start('delete_log', 'confirm_delete_log', 'cancel_delete_log');
    });

}

//--------------------------------------------------------------------------------

function delete_all_logs() {
    setTimeout(hide_stuff_before_save_log, 1, `Deleting all saved logfiles...`);

    let status_field = $('#loading_msg');
    let postdata = `action=delete_all_logfiles`;
    $.post({
        'url': url_ip_log_raw_data,
        'data': postdata,
        'success': null,
        'dataType': 'json' // html, json, script, text, xml
    })
    .done(function(data){
        if (data.status == 'error') {
            status_field.html(`ERROR: ${data.error_msg}`);
            return;
        }

        // empty the saved logfile menu and hide it
        $('#saved_logfile_menu').html('');
        $('#saved_logs_section').hide();
    })
    .fail(function(){
        status_field.html('ERROR: AJAX failed');
    })
    .always(function(){
        setTimeout(clear_status_save_log, 1000);
        switch_confirm_to_start('delete_all_logs', 'confirm_delete_all_logs', 'cancel_delete_all_logs');
    });
}

//--------------------------------------------------------------------------------

function add_logdata_to_dom(data, download_start_time_ms, use_saved_log=false) {
    let download_runtime = (Date.now() - download_start_time_ms)/1000;
    print_console_in_test_mode(`download time: ${download_runtime.toFixed(3)} seconds`, test_mode_ip_log_raw_data);
    let download_kb = estimate_memory_size(data) / 1024;
    print_console_in_test_mode(`downloaded data: ${download_kb.toFixed(3)} KB`, test_mode_ip_log_raw_data);

    if (data.status == 'error') {
        $('#loading_msg').html(`ERROR: ${data.error_msg}`);
        return;
    }

    print_console_in_test_mode(`calculation_time: ${data.calculation_time} seconds`, test_mode_ip_log_raw_data);
    let start_time_ms = Date.now();

    $('#loading_msg').html(''); // clear the status message
    $('#logdata').html(data.logdata);
    $('#limit_field_errors').html(data.limit_field_errors);

    $('#src_ip_analysis').html(data.src_ip_analysis);
    $('#dst_ip_analysis').html(data.dst_ip_analysis);

    if ($('#extra_analysis').is(':checked')) {
        $('#src_length_analysis').html(data.src_length_analysis);
        $('#dst_length_analysis').html(data.dst_length_analysis);
        $('#summary_src_length_analysis').html(data.summary_src_length_analysis);
    } else {
        $('#src_length_analysis').html('');
        $('#dst_length_analysis').html('');
        $('#summary_src_length_analysis').html('');
    }

    $('#show_rowcount').html(data.rowcount);
    $('#start_timestamp').html(data.start_timestamp);
    $('#end_timestamp').html(data.end_timestamp);
    $('#duration').html(data.duration);
    $('#bps_limit_displayed').html(data.bps_limit_displayed);

    $('#displayed_src_ports').html(data.displayed_src_ports);
    $('#displayed_dst_ports').html(data.displayed_dst_ports);
    $('#displayed_packet_lengths').html(data.displayed_packet_lengths);
    $('#displayed_packet_ttls').html(data.displayed_packet_ttls);
    $('#displayed_src_not_in_dst').html(data.displayed_src_not_in_dst);
    $('#displayed_dst_not_in_src').html(data.displayed_dst_not_in_src);

    let loaded_from = 'loaded from unsaved log';
    if (use_saved_log) {
        loaded_from = 'loaded from saved log';
    }
    console.log(loaded_from);

    if (data.is_logfile_saved) {
        $('#save_this_log').html('(Log is already saved)');
    } else if (data.filename != 'ipv4.log') {
        // not allowed to save the current log file for now
        //-----add an extra save_log anchor to the dom-----
        let save_button = `<a id="save_this_log_button" class="clickable" data-filename="${data.filename}">Save this log</a>`;
        $('#save_this_log').html(save_button);
        $('#save_this_log_button').click(function() {
            save_log(data.filename);
        });
    } else {
        $('#save_this_log').html('');
    }
    
    $('#logdata_misc_info').show();

    //TEST
    $('#TESTDATA').html(data.TESTDATA);

    //-----make clickable items work-----
    attach_copy_to_clipboard();
    apply_onclick_events();

    $('#show_all_data').show();
    reset_show_hide();

    let runtime = (Date.now() - start_time_ms)/1000;
    print_console_in_test_mode(`browser page update time: ${runtime.toFixed(3)} seconds`, test_mode_ip_log_raw_data);
}

//--------------------------------------------------------------------------------

function lookup_filename(log_type='current_log', use_saved_log=false) {
    let filename = '';
    if (use_saved_log) {
        return $('#saved_logfile_menu>option:selected').val();
    }

    if (log_type=='previous_log') {
        let filename_option = $('#logfile>option:selected').prev();
        if (filename_option.length == 0) {
            // show error message
            $('#loading_msg').html(`ERROR: No newer log file`);
            return '';
        }
        // scroll the menu to the selected option
        $('#logfile>option:selected').prop('selected', false);
        filename_option.prop('selected', true);
    } else if (log_type=='next_log') {
        let filename_option = $('#logfile>option:selected').next();
        if (filename_option.length == 0) {
            // show error message
            $('#loading_msg').html(`ERROR: No older log file`);
            return '';
        }
        // scroll the menu to the selected option
        $('#logfile>option:selected').prop('selected', false);
        filename_option.prop('selected', true);
    }

    filename = $('#logfile>option:selected').val();
    return filename;
}

//-----get the contents of a given log file-----
// returns a promise
// use_saved_log=false, previous_log=false, next_log=false
function view_log(log_type='current_log') {
    let use_saved_log=false;
    if (log_type=='saved_log') { use_saved_log=true; }

    let filename = lookup_filename(log_type, use_saved_log);
    if (filename == '') { return; }

    let action = 'view_log';
    if (use_saved_log) { action = 'view_saved_log'; }

    setTimeout(hide_stuff_before_dom_update, 1, filename);

    let src_ip = $('#src_ip').val();
    let dst_ip = $('#dst_ip').val();
    let src_ports = $('#src_ports').val();
    let dst_ports = $('#dst_ports').val();
    let search_length = $('#search_length').val();
    let ttl = $('#ttl').val();
    let flag_bps_above_value = $('#flag_bps_above_value').val();
    let flag_pps_above_value = $('#flag_pps_above_value').val();
    let min_displayed_packets = $('#min_displayed_packets').val();

    let sort_by = $("#sort_by>option:selected").val();

    // let CHECKBOX_ID = String($('#CHECKBOX_ID').is(':checked'));
    let checkbox_url_params = process_checkboxes();

    let postdata = `action=${action}&filename=${filename}&src_ip=${src_ip}&dst_ip=${dst_ip}&src_ports=${src_ports}&dst_ports=${dst_ports}&search_length=${search_length}&ttl=${ttl}&sort_by=${sort_by}&flag_bps_above_value=${flag_bps_above_value}&flag_pps_above_value=${flag_pps_above_value}&min_displayed_packets=${min_displayed_packets}${checkbox_url_params}`;

    let status_field = $('#loading_msg');
    let download_start_time_ms = Date.now();
    $.post({
        'url': url_ip_log_raw_data,
        'data': postdata,
        'success': null,
        'dataType': 'json' // html, json, script, text, xml
    })
    .done(function(data){
        add_logdata_to_dom(data, download_start_time_ms, use_saved_log);

        $('#loading_msg').html('');
    })
    .fail(function(){
        status_field.html('ERROR: AJAX failed');
    })
    .always(function(){
        //-----auto-clear the message after a short time-----
        // status_ip_log_parse_now_timer = setTimeout(clear_status_ip_log_parse_now, 3000);
        show_buttons();
    });
}

//--------------------------------------------------------------------------------

function get_logfile_menu() {
    // return if auto_update_file_list is disabled
    if (! $('#auto_update_file_list').is(':checked')) {
        return;
    }
    last_menu_update_time = date_obj_ip_log_raw_data.getTime();

    let postdata = `action=get_logfile_menu`;
    $.post({
        'url': url_ip_log_raw_data,
        'data': postdata,
        'success': null,
        'dataType': 'json' // html, json, script, text, xml
    })
    .done(function(data){
        if (data.status == 'error') {
            console.log(`ERROR: ${data.error_msg}</p>`);
            return;
        }

        //-----replace the contents of the logfile dropdown-----
        let current_menu = $('#logfile').html();
        let current_saved_menu = $('#saved_logfile_menu').html();
        if (current_menu == data.logfile_menu) {
            console.log('logfile menu unchanged');
        } else {
            $('#logfile').html(data.logfile_menu);
        }
        if (current_saved_menu == data.saved_logfile_menu) {
            console.log('saved logfile menu unchanged');
        } else {
            $('#saved_logfile_menu').html(data.saved_logfile_menu);
            // hide the saved menu if it's empty
            if (data.saved_logfile_menu == '') {
                $('#saved_logs_section').hide();
            } else {
                $('#saved_logs_section').show();
            }
        }

        console.log('logfile menu updated');
    })
    .fail(function(){
        // status_field.html('ERROR');
    })
    .always(function(){
        // $('#view_log').show();
        // $('#loading_msg').hide();
    });
}

//--------------------------------------------------------------------------------

//-----reset all search fields to default values-----
function reset_search() {
    // warnings
    $('#limit_field_errors').html('');

    // checkboxes
    leave_unchecked = ['connection_internal', 'extra_analysis']
    for (let i=0; i<ip_log_raw_data_checkbox_fields.length; i++) {
        let field = ip_log_raw_data_checkbox_fields[i];

        // don't reset the auto-update checkbox
        if (field == 'auto_update_file_list') { continue; }

        if (leave_unchecked.includes(field)) {
            $('#'+field).prop('checked', false);
        } else {
            $('#'+field).prop('checked', true);
        }
    }

    // sort by IP
    $('#sort_by').attr("data-last-query", 'ip');
    set_sort_by();

    // clear all input fields
    $('#src_ip').val('');
    $('#dst_ip').val('');
    $('#src_ports').val('');
    $('#dst_ports').val('');
    $('#search_length').val('');
    $('#ttl').val('');

    let flag_bps_default = $('#flag_bps_above_value').attr('data-default');
    $('#flag_bps_above_value').val(flag_bps_default);

    let flag_pps_default = $('#flag_pps_above_value').attr('data-default');
    $('#flag_pps_above_value').val(flag_pps_default);

    let min_displayed_packets_default = $('#min_displayed_packets').attr('data-default');
    $('#min_displayed_packets').val(min_displayed_packets_default);

    switch_confirm_to_start('reset_search', 'confirm_reset_search', 'cancel_reset_search');
}

//--------------------------------------------------------------------------------

function reset_show_hide() {
    $('#show_hide_src_ip_analysis').html('Hide Source IP Analysis');
    $('#src_ip_analysis').show();

    $('#show_hide_dst_ip_analysis').html('Hide Destination IP Analysis');
    $('#dst_ip_analysis').show();

    $('#show_hide_extra_analysis_output').html('Hide Extra Analysis');
    if ($('#extra_analysis').is(':checked')) {
        $('#extra_analysis_output').show();
    }

    $('#show_hide_logdata').html('Hide Raw Data');
    $('#logdata').show();
}

//--------------------------------------------------------------------------------

function view_raw_text(log_type='live') {
    let filename = '';
    let action = 'view_raw_text';
    if (log_type=='live') {
        filename = $('#logfile>option:selected').val();
    } else if (log_type=='saved') {
        filename = $('#saved_logfile_menu>option:selected').val();
        action = 'saved_view_raw_text';
    }
    setTimeout(hide_stuff_before_dom_update, 1, filename);

    let status_field = $('#loading_msg');
    let postdata = `action=${action}&filename=${filename}`;
    $.post({
        'url': url_ip_log_raw_data,
        'data': postdata,
        'success': null,
        'dataType': 'json' // html, json, script, text, xml
    })
    .done(function(data){
        if (data.status == 'error') {
            status_field.html(`ERROR: ${data.error_msg}`);
            return;
        }

        $('#logdata').html(data.logdata);
        $('#loading_msg').html('');
    })
    .fail(function(){
        status_field.html('ERROR: AJAX failed');
    })
    .always(function(){
        show_buttons();
        $('#show_all_data').show();
        reset_show_hide();
    });

}

//--------------------------------------------------------------------------------
