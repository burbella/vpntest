function load_js_update_os()
{    
    //-----refresh the OS updates printout-----
    $('#refresh_list').click(function() {
        $('#print_pending_updates').html('Requesting latest updates...');
        
        let postdata = 'action=refresh_list';

        $.post({
            'url': url_update_os,
            'data': postdata,
            'success': null,
            'dataType': 'json' // html, json, script, text, xml
        })
        .done(function(data){
            $('#print_pending_updates').html(data.pending_updates);
            $('#os_update_output').html(data.os_update_output);
        })
        .fail(function(){
            $('#print_pending_updates').html('ERROR refreshing update list');
            $('#os_update_output').html('ERROR refreshing OS update output');
        });
    });
    
    //-----request a new list of OS updates-----
    $('#request_pending_updates').click(function() {
        $('#status_request_pending_updates').html('Submitting...');
        
        let postdata = 'action=list_os_updates';

        $.post(url_update_os, postdata)
        .done(function(data){
            $('#status_request_pending_updates').html(data);
        })
        .fail(function(){
            $('#status_request_pending_updates').html('ERROR requesting latest updates');
        });
    });
    
    //-----double-check if the user really wants to install updates-----
    // switch install to confirm_install
    $('#install_updates').click(function() {
        $('#confirm_install_updates').removeClass('hide_item');
        $('#confirm_install_updates').addClass('clickable');
        
        $('#cancel_install_updates').removeClass('hide_item');
        $('#cancel_install_updates').addClass('clickable_red');
        
        $('#install_updates').removeClass('clickable');
        $('#install_updates').addClass('hide_item');
    });
    // switch confirm back to install
    $('#cancel_install_updates').click(function() {
        $('#confirm_install_updates').removeClass('clickable');
        $('#confirm_install_updates').addClass('hide_item');
        
        $('#cancel_install_updates').removeClass('clickable_red');
        $('#cancel_install_updates').addClass('hide_item');
        
        $('#install_updates').removeClass('hide_item');
        $('#install_updates').addClass('clickable');
    });
    
    //-----request the OS updates to be installed-----
    $('#confirm_install_updates').click(function() {
        $('#status_install_updates').html('Submitting...');
        $('#confirm_install_updates').hide();
        $('#cancel_install_updates').hide();

        let postdata = 'action=install_os_updates';

        $.post(url_update_os, postdata)
        .done(function(data){
            $('#status_install_updates').html(data);
        })
        .fail(function(){
            $('#status_install_updates').html('ERROR installing updates');
            $('#install_updates').show();
        });
    });
}
