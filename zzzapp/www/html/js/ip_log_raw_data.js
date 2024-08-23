//-----IP Log Raw Data UI-----
// this JS assumes that services.js has been loaded in the page already

var ip_log_raw_data_logfile_timer = null;
var ip_log_raw_data_logfile_timer_interval = 60000;
var last_menu_update_time = 0;
var date_obj_ip_log_raw_data = new Date();

var ip_log_raw_data_checkbox_fields = ['auto_update_file_list', 'connection_external', 'connection_internal', 'extra_analysis', 'flags_any', 'flags_none', 'include_accepted_packets', 'include_blocked_packets', 'prec_tos_zero', 'prec_tos_nonzero', 'protocol_tcp', 'protocol_udp', 'protocol_icmp', 'protocol_other', 'show_max_bps_columns'];

//-----load the relevant jQuery code for the page-----
function load_js_ip_log_raw_data()
{
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

    $('#view_log').click(function() {
        view_log();
    });

    $('#reset_search').click(function() {
        reset_search();
    });

    start_clock();
    start_logfile_timer();

    console.log("ip_log_raw_data Ready.");

    return true;
}

//--------------------------------------------------------------------------------

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

function hide_stuff_before_dom_update(filename='') {
    $('#status_post').html('');
    $('#show_all_data').hide();
    $('#view_log').hide();
    $('#logdata_misc_info').hide();
    $('#extra_analysis_output').hide();

    $('#loading_msg').html(`Loading ${filename}...`);
    $('#loading_msg').show();
}

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

//-----get the contents of a given log file-----
// returns a promise
function view_log(){
    let filename = $('#logfile>option:selected').val();
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

    let postdata = `action=view_log&filename=${filename}&src_ip=${src_ip}&dst_ip=${dst_ip}&src_ports=${src_ports}&dst_ports=${dst_ports}&search_length=${search_length}&ttl=${ttl}&sort_by=${sort_by}&flag_bps_above_value=${flag_bps_above_value}&flag_pps_above_value=${flag_pps_above_value}&min_displayed_packets=${min_displayed_packets}${checkbox_url_params}`;

    let download_start_time_ms = Date.now();
    $.post({
        'url': url_ip_log_raw_data,
        'data': postdata,
        'success': null,
        'dataType': 'json' // html, json, script, text, xml
    })
    .done(function(data){
        let download_runtime = (Date.now() - download_start_time_ms)/1000;
        console.log(`download time: ${download_runtime.toFixed(3)} seconds`);
        download_kb = estimate_memory_size(data) / 1024;
        console.log(`downloaded data: ${download_kb.toFixed(3)} KB`);

        if (data.status == 'error') {
            $('#status_post').html(`<p class="warning_text">ERROR: ${data.error_msg}</p>`);
            return;
        }

        //TEST
        console.log(`calculation_time: ${data.calculation_time} seconds`);
        let start_time_ms = Date.now();

        $('#status_post').html(''); // clear the status message
        $('#logdata').html(data.logdata);

        $('#src_ip_analysis').html(data.src_ip_analysis);
        $('#dst_ip_analysis').html(data.dst_ip_analysis);

        if ($('#extra_analysis').is(':checked')) {
            $('#src_length_analysis').html(data.src_length_analysis);
            $('#dst_length_analysis').html(data.dst_length_analysis);
            $('#summary_src_length_analysis').html(data.summary_src_length_analysis);
            // $('#extra_analysis_output').show();
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

        $('#logdata_misc_info').show();

        //TEST
        $('#TESTDATA').html(data.TESTDATA);

        //-----make clickable items work-----
        attach_copy_to_clipboard();
        apply_onclick_events();

        $('#show_all_data').show();
        reset_show_hide();

        let runtime = (Date.now() - start_time_ms)/1000;
        console.log(`browser page update time: ${runtime.toFixed(3)} seconds`);
    })
    .fail(function(){
        // status_field.html('ERROR');
    })
    .always(function(){
        //-----auto-clear the message after a short time-----
        // status_ip_log_parse_now_timer = setTimeout(clear_status_ip_log_parse_now, 3000);
        $('#view_log').show();
        $('#loading_msg').hide();
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
        if (current_menu == data.logfile_menu) {
            console.log('logfile menu unchanged');
            return;
        }

        $('#logfile').html(data.logfile_menu);
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

