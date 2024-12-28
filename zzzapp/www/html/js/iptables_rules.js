//-----iptables Rules UI-----
// this JS assumes that services.js has been loaded in the page already

var iptables_rules_status_fields = [
    'allow_ips',
    'block_low_ttl',
    'block_nonzero_tos',
    'block_non_allowed_ips',
    'block_packet_length',
    'block_tcp',
    'block_udp',
    'bytes_burst',
    'bytes_per_sec',
    'dst_ports',
    'enable_auto_blocking',
    'notes',
    'packets_burst',
    'packets_per_sec',
    'throttle_expire',
    'traffic_direction',
];

//-----load the relevant jQuery code for the page-----
function load_js_iptables_rules(traffic_direction)
{
    //-----load the radio settings-----
    $(`input[name=traffic_direction][value=${traffic_direction}]`).prop('checked', true);

    //-----display unsaved status when a field is edited-----
    for (let i=0; i<iptables_rules_status_fields.length; i++) {
        $('#'+iptables_rules_status_fields[i]).change(function() {
            show_unsaved_status(`status_${iptables_rules_status_fields[i]}`);
        });
    }
    // $('#enable_auto_blocking').change(function() {
    //     show_unsaved_status('status_enable_auto_blocking');
    // });
    //-----end unsaved section-----

    $('#save_iptables_rules').click(function() {
        do_save_settings();
    });

    //-----force at least one protocol checkbox to be checked-----
    $('#block_tcp').change(function() {
        if (!$(this).is(':checked') && !$('#block_udp').is(':checked')) {
            $('#block_udp').prop('checked', true);
        }
    });
    $('#block_udp').change(function() {
        if (!$(this).is(':checked') && !$('#block_tcp').is(':checked')) {
            $('#block_tcp').prop('checked', true);
        }
    });

    console.log("iptables_rules Ready.");

    return true;
}

//--------------------------------------------------------------------------------

// show unsaved status next to the Save button
function show_unsaved_status(status_id='') {
    let unsaved_html = '<span class="update_fail">Not Saved</span>';
    $('#saved_indicator').html(unsaved_html);
    if (status_id=='') { return; }
    $('#'+status_id).html(unsaved_html);
}

function do_save_settings() {
    clear_upload_status();
    // show_saving_in_progress();
    save_iptables_rules();
}

//--------------------------------------------------------------------------------

//-----clears all status messages-----
function clear_settings_status() {
    // $('#status_enable_auto_blocking').html('');
    for (let i=0; i<iptables_rules_status_fields.length; i++) {
        $(`#status_${iptables_rules_status_fields[i]}`).html('');
    }
}

function clear_upload_status() {
    $('#saved_indicator').html('');
    $('#status_save_iptables_rules').html('');
}

//--------------------------------------------------------------------------------

//-----create a JSON string from the settings fields-----
function make_json_settings() {
    let settings_object = {};

    // checkboxes: enable_auto_blocking, block_tcp, block_udp, block_nonzero_tos, block_non_allowed_ips
    settings_object.enable_auto_blocking = String($('#enable_auto_blocking').is(':checked'));
    settings_object.block_tcp = String($('#block_tcp').is(':checked'));
    settings_object.block_udp = String($('#block_udp').is(':checked'));
    settings_object.block_nonzero_tos = String($('#block_nonzero_tos').is(':checked'));
    settings_object.block_non_allowed_ips = String($('#block_non_allowed_ips').is(':checked'));

    // radio buttons: traffic_direction
    settings_object.traffic_direction = $(':radio[name=traffic_direction]:checked').val();

    // text fields: allow_ips(textarea), block_low_ttl, block_packet_length, bytes_per_sec, dst_ports, notes, packets_per_sec, throttle_expire
    settings_object.allow_ips = $('#allow_ips').val();
    settings_object.block_low_ttl = $('#block_low_ttl').val();
    settings_object.block_packet_length = $('#block_packet_length').val();
    settings_object.bytes_burst = $('#bytes_burst').val();
    settings_object.bytes_per_sec = $('#bytes_per_sec').val();
    settings_object.dst_ports = $('#dst_ports').val();
    settings_object.notes = $('#notes').val();
    settings_object.packets_burst = $('#packets_burst').val();
    settings_object.packets_per_sec = $('#packets_per_sec').val();
    settings_object.throttle_expire = $('#throttle_expire').val();

    let iptables_rules_json = JSON.stringify(settings_object);

    return iptables_rules_json;
}

//--------------------------------------------------------------------------------

// update DOM fields: saved_indicator, status_save_iptables_rules
function save_iptables_rules() {
    let success_html = '<span class="update_success">Settings Saved</span>';
    let error_html = '<span class="text_red">ERROR</span>';
    let status_field = $('#status_save_iptables_rules');
    let iptables_rules_json = encodeURIComponent(make_json_settings());
    let postdata = `action=save_iptables_rules&json_data=${iptables_rules_json}`;

    $.post({
        'url': url_iptables_rules,
        'data': postdata,
        'success': null,
        'dataType': 'json' // html, json, script, text, xml
    })
    .done(function(data){
        if (data.status == 'error') {
            status_field.html(`ERROR: ${data.error_msg}`);
            return;
        }
        //-----success - update the HTML page-----
        clear_settings_status();
        $('#saved_indicator').html(success_html);
    })
    .fail(function(){
        status_field.html('ERROR: AJAX failed');
    })
    .always(function(){
        //-----auto-clear the message after a short time-----
        // status_ip_log_parse_now_timer = setTimeout(clear_status_ip_log_parse_now, 3000);
        // keep the saving message up for a short time
    });

}

//--------------------------------------------------------------------------------

