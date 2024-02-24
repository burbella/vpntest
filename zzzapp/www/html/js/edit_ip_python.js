//-----upload either a new list or added IPs-----
// actions: add_ips, replace_ips
//TODO: make this similar to the code in squid_log.js
function upload_list_to_server(action, ip_list) {
    let postdata = 'action=' + action + '&ip_list=' + ip_list;

    $.post(url_edit_ip, postdata)
    .done(function(data){
        update_status(action, data);
    })
    .fail(function(){
        update_status(action, 'ERROR uploading IP list');
    });
}

//-----choose which status field to update-----
function update_status(action, data) {
    if (action == 'add_ips')
    {
        if (data == 'success')
        {
            $('#status_submit_added_ips').html('<p>Uploading...Done</p>');
        }
        else
        {
            $('#status_submit_added_ips').html('<pre>' + data + '</pre>');
        }
    }
    else
    {
        if (data == 'success')
        {
            $('#status_submit_new_list').html('<p>Uploading...Done</p>');
        }
        else
        {
            $('#status_submit_new_list').html('<pre>' + data + '</pre>');
        }
    }
}

function get_ip_backup_file(filename) {
    let postdata = 'action=get_ip_file&filename=' + filename;

    $.post(url_edit_ip, postdata)
    .done(function(data){
        $('#show_file').val(data);
    })
    .fail(function(){
        console.log('ERROR downloading IP file');
    });
}

function attach_get_ip_backup_file() {
    $('.get_ip_backup_file').click(function() {
        get_ip_backup_file($(this).attr("data-onclick"));
    });
}

function load_js_edit_ip()
{
    $('#submit_added_ips').click(function() {
        $('#status_submit_added_ips').html('<p>Uploading...</p>');
        
        upload_list_to_server('add_ips', encodeURIComponent($('#ips_to_add').val()));
    });
    
    $('#submit_new_list').click(function() {
        $('#status_submit_new_list').html('<p>Uploading...</p>');
        
        upload_list_to_server('replace_ips', encodeURIComponent($('#replace_ip_list').val()));
    });
    
    $('#copy_to_replace').click(function() {
        $('#replace_ip_list').val($('#show_file').val());
    });
    
    attach_content_collapsed_toggle();
    attach_get_ip_backup_file();
}
