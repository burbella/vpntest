//-----load the relevant jQuery code for the page-----
function load_js_system_command()
{
    let url_system_command = zzz_https_url + $('#url').val();
    let command = $('#command').val();
    let system_command_service_name = $('#service_name').val();
    
    //-----request the system command to run-----
    $('#confirm_command').click(function() {
        $('#status_confirm_command').html('Submitting...');
        
        let postdata = `command=${command}&service_name=${system_command_service_name}`;
        let status_field = $('#status_confirm_command');
        let success_html = '<span class="update_success">Success</span>';
        let error_html = '<span class="text_red">ERROR</span>';

        $.post({
            'url': url_system_command,
            'data': postdata,
            'success': null,
            'dataType': 'text'
        })
        .done(function(data){
            console.log('POST done');
            //-----display status-----
            status_field.html(data);
        })
        .fail(function(){
            console.log('POST fail');
            status_field.html(error_html);
        })
        .always(function(){
            console.log('POST end');
        });
    });
    
    //-----double-check if the user really wants to install updates-----
    attach_click_events_start_cancel_confirm('reboot_linux', 'confirm_reboot_linux', 'cancel_reboot_linux', 'status_confirm_command', url_system_command, 'command=restart&service_name=linux', true);
}
