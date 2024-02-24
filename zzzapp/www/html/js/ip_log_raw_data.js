//-----IP Log Raw Data UI-----
// this JS assumes that services.js has been loaded in the page already

//-----load the relevant jQuery code for the page-----
function load_js_ip_log_raw_data()
{
    $('#view_log').click(function() {
        view_log();
    });

    console.log("ip_log_raw_data Ready.");

    return true;
}

//--------------------------------------------------------------------------------

function hide_stuff_before_dom_update(filename='') {
    $('#status_post').html('');
    $('#show_all_data').hide();
    $('#view_log').hide();

    $('#loading_msg').html(`Loading ${filename}...`);
    $('#loading_msg').show();
}

//-----get the contents of a given log file-----
// returns a promise
function view_log(){
    let filename = $('#logfile>option:selected').val();
    setTimeout(hide_stuff_before_dom_update, 1, filename);

    let src_ip = $('#src_ip').val();
    let dst_ip = $('#dst_ip').val();
    let src_ports = $('#src_ports').val();
    let dst_ports = $('#dst_ports').val();
    let hide_internal_connections = String($('#hide_internal_connections').is(':checked'));
    let postdata = `action=view_log&filename=${filename}&hide_internal_connections=${hide_internal_connections}&src_ip=${src_ip}&dst_ip=${dst_ip}&src_ports=${src_ports}&dst_ports=${dst_ports}`;

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
        let analysis_stats = `Rows: ${data.rowcount}<br>Time Range: ${data.start_timestamp} - ${data.end_timestamp}<br>Duration: ${data.duration} seconds ${data.bps_limit_displayed}`;
        $('#show_rowcount').html(analysis_stats);

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

