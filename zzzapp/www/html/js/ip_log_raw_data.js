//-----IP Log Raw Data UI-----
// this JS assumes that services.js has been loaded in the page already

var ip_log_raw_data_logfile_timer = null;

//-----load the relevant jQuery code for the page-----
function load_js_ip_log_raw_data()
{
    //-----select the option that was used last time-----
    let last_query = $('#sort_by').attr("data-last-query");
    $('#sort_by>option').each(function() {
        let sort_by = $(this).val();
        if (sort_by == last_query) {
            $(this).attr("selected", "selected");
        }
    });

    $('#view_log').click(function() {
        view_log();
    });

    start_clock();
    start_logfile_timer();

    console.log("ip_log_raw_data Ready.");

    return true;
}

//--------------------------------------------------------------------------------

function start_logfile_timer() {
    ip_log_raw_data_logfile_timer = setInterval(get_logfile_menu, 60000);
}

function hide_stuff_before_dom_update(filename='') {
    $('#status_post').html('');
    $('#show_all_data').hide();
    $('#view_log').hide();
    $('#logdata_misc_info').hide();

    $('#loading_msg').html(`Loading ${filename}...`);
    $('#loading_msg').show();
}

//--------------------------------------------------------------------------------

function process_checkboxes() {
    checkbox_fields = ['auto_update_file_list', 'flags_any', 'flags_none', 'hide_internal_connections', 'include_accepted_packets', 'include_blocked_packets', 'prec_tos_zero', 'prec_tos_nonzero', 'protocol_tcp', 'protocol_udp', 'protocol_icmp', 'protocol_other', 'show_max_bps_columns'];
    checkbox_url_params = '';
    for (let i=0; i<checkbox_fields.length; i++) {
        let field = checkbox_fields[i];
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
    let flag_bps_above_value = $('#flag_bps_above_value').val();
    let flag_pps_above_value = $('#flag_pps_above_value').val();

    let sort_by = $("#sort_by>option:selected").val();

    // let hide_internal_connections = String($('#hide_internal_connections').is(':checked'));
    let checkbox_url_params = process_checkboxes();

    let postdata = `action=view_log&filename=${filename}&src_ip=${src_ip}&dst_ip=${dst_ip}&src_ports=${src_ports}&dst_ports=${dst_ports}&sort_by=${sort_by}&flag_bps_above_value=${flag_bps_above_value}&flag_pps_above_value=${flag_pps_above_value}${checkbox_url_params}`;

    $.post({
        'url': url_ip_log_raw_data,
        'data': postdata,
        'success': null,
        'dataType': 'json' // html, json, script, text, xml
    })
    .done(function(data){
        if (data.status == 'error') {
            $('#status_post').html(`<p class="warning_text">ERROR: ${data.error_msg}</p>`);
            return;
        }

        $('#status_post').html(''); // clear the status message
        $('#logdata').html(data.logdata);
        $('#src_ip_analysis').html(data.src_ip_analysis);
        $('#dst_ip_analysis').html(data.dst_ip_analysis);
        $('#show_rowcount').html(data.rowcount);
        $('#start_timestamp').html(data.start_timestamp);
        $('#end_timestamp').html(data.end_timestamp);
        $('#duration').html(data.duration);
        $('#bps_limit_displayed').html(data.bps_limit_displayed);

        $('#displayed_src_ports').html(data.displayed_src_ports);
        $('#displayed_dst_ports').html(data.displayed_dst_ports);
        $('#logdata_misc_info').show();

        //TEST
        $('#TESTDATA').html(data.TESTDATA);

        //-----make clickable items work-----
        attach_copy_to_clipboard();
        apply_onclick_events();

        $('#show_all_data').show();
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
