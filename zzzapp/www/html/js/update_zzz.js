function load_js_update_zzz()
{
    // app_versions display
    $('#show_hide_app_versions').click(function() {
        show_hide_object('app_versions', 'show_hide_app_versions', 'Show PIP Versions', 'Hide PIP Versions');
    });

    // pipdeptree_all
    $('#pipdeptree_all').click(function() {
        setTimeout(pipdeptree_button_loading, 1);
        load_pipdeptree('', true);
    });

    //-----refresh the Zzz updates output-----
    $('#refresh_code_diff').click(function() {
        $('#print_pending_updates').html('Requesting latest updates...');

        let postdata = 'action=refresh_code_diff';
        let error_html = '<span class="text_red">ERROR</span>';
        $.post({
            'url': url_update_zzz,
            'data': postdata,
            'success': null,
            'dataType': 'json' // html, json, script, text, xml
        })
        .done(function(data){
            //-----check the return value-----
            if (data.status=='success') {
                //-----success - update the HTML page-----
                $('#print_code_diff').html(data.code_diff);
                $('#print_pytest').html(data.pytest);
                $('#print_installer_output').html(data.installer_output);
                $('#print_git_output').html(data.git_output);
            } else {
                error_html = `<span class="text_red">${data.error_msg}</span>`;
                $('#print_code_diff').html(error_html);
                $('#print_pytest').html('');
                $('#print_installer_output').html('');
                $('#print_git_output').html('');    
            }
        })
        .fail(function(){
            $('#print_code_diff').html(error_html);
            $('#print_pytest').html('');
            $('#print_installer_output').html('');
            $('#print_git_output').html('');
        })
        .always(function(){
        });
    });
    
    //-----request a new list of Zzz updates-----
    $('#request_code_diff').click(function() {
        $('#status_request_code_diff').html('Submitting...');
        
        let postdata = 'action=run_code_diff';
        $.post(url_update_zzz, postdata)
        .done(function(data){
            $('#status_request_code_diff').html(data);
        })
        .fail(function(){
            $('#status_request_code_diff').html('ERROR requesting latest updates');
        });
    });
    
    //-----request a pytest run-----
    $('#request_pytest').click(function() {
        $('#status_request_pytest').html('Submitting...');
        
        let postdata = 'action=run_pytest';
        $.post(url_update_zzz, postdata)
        .done(function(data){
            $('#status_request_pytest').html(data);
        })
        .fail(function(){
            $('#status_request_pytest').html('ERROR requesting pytest');
        });
    });
    
    //-----request a git branch list update-----
    $('#request_git_branch').click(function() {
        setTimeout(function(){
            // re-use the git_diff status field
            $('#status_request_git_diff').html('Submitting...');
        }, 1);

        let postdata = 'action=git_branch';
        $.post(url_update_zzz, postdata)
        .done(function(data){
            $('#status_request_git_diff').html(data);
        })
        .fail(function(){
            $('#status_request_git_diff').html('ERROR requesting git branch');
        });
    });
    
    //-----request a git diff-----
    $('#request_git_diff').click(function() {
        $('#status_request_git_diff').html('Submitting...');

        let branch = $('#git_diff_branch_menu>option:selected').val();
        let postdata = `action=git_diff&branch=${branch}`;
        $.post(url_update_zzz, postdata)
        .done(function(data){
            $('#status_request_git_diff').html(data);
        })
        .fail(function(){
            $('#status_request_git_diff').html('ERROR requesting git diff');
        });
    });
    
    //-----request a git pull-----
    // not needed since git reset does a pull
    /*
    $('#request_git_pull').click(function() {
        $('#status_request_git_pull').html('Submitting...');
        
        let postdata = 'action=git_pull';
        $.post(url_update_zzz, postdata)
        .done(function(data){
            $('#status_request_git_pull').html(data);
        })
        .fail(function(){
            $('#status_request_git_pull').html('ERROR requesting git pull');
        });
    });
    */
    
    //-----request a git reset-----
    $('#request_git_reset').click(function() {
        $('#status_request_git_reset').html('Submitting...');
        
        let branch = $('#git_reset_branch_menu>option:selected').val();
        let postdata = `action=git_reset&branch=${branch}`;
        $.post(url_update_zzz, postdata)
        .done(function(data){
            $('#status_request_git_reset').html(data);
        })
        .fail(function(){
            $('#status_request_git_reset').html('ERROR requesting git reset');
        });
    });
    
    //-----run version checks-----
    $('#version_checks').click(function() {
        $('#status_version_checks').html('Submitting...');
        
        let postdata = 'action=version_checks';
        $.post(url_update_zzz, postdata)
        .done(function(data){
            $('#status_version_checks').html(data);
        })
        .fail(function(){
            $('#status_version_checks').html('ERROR requesting version checks');
        });
    });
    
    $('#load_python_pip_versions').click(function() {
        setTimeout(pip_check_button_loading, 1);

        let postdata = 'action=pip_versions';
        let pip_local_only = $('#pip_local_only').is(':checked');
        let pip_hide_dependencies = $('#pip_hide_dependencies').is(':checked');
        if (pip_local_only) { postdata += '&pip_local_only=1'; }
        if (pip_hide_dependencies) { postdata += '&pip_hide_dependencies=1'; }
        let status_field = $('#python_pip_version_data');

        $.post({
            'url': url_update_zzz,
            'data': postdata,
            'success': null,
            'dataType': 'text' // html, json, script, text, xml
        })    
        .done(function(data){
            status_field.html(data);
            attach_click_events_pipdeptree();
            attach_copy_to_clipboard();
        })
        .fail(function(){
            status_field.html('ERROR requesting PIP versions');
        })
        .always(function(){
            $('#load_python_pip_versions').removeClass('hide_item')
            $('#wait_python_pip_versions').addClass('hide_item')
        });
    });
    
    //-----clear the dev status when the dev menu changes-----
    $('#upgrade_dev_menu').change(function(){
        $('#status_upgrade_dev').html('');
    });

    //--------------------------------------------------------------------------------
    
    //-----double-check if the user really wants to install code updates-----
    attach_click_events_start_cancel_confirm('install_updates', 'confirm_install_updates', 'cancel_install_updates', 'status_install_updates', url_update_zzz, 'action=install_zzz_codebase');
    
    //-----double-check if the user really wants to upgrade the entire Zzz System to the latest version-----
    attach_click_events_start_cancel_confirm('upgrade_zzz', 'confirm_upgrade_zzz', 'cancel_upgrade_zzz', 'status_upgrade_zzz', url_update_zzz, 'action=queue_upgrades', true);
    
    //-----double-check if the user really wants to upgrade the entire Zzz System to the SELECTED DEV version-----
    // this uses custom code for confirm, instead of the default confirm function
    //attach_click_events_start_cancel_confirm('upgrade_dev', 'confirm_upgrade_dev', 'cancel_upgrade_dev', 'status_upgrade_dev', url_update_zzz, 'action=dev_upgrade', true);
    attach_click_events_start_cancel('upgrade_dev', 'confirm_upgrade_dev', 'cancel_upgrade_dev');
	//-----do the requested action on confirm-----
	$('#confirm_upgrade_dev').click(function() {
		$('#status_upgrade_dev').html('Submitting...');
		
		switch_confirm_to_start('upgrade_dev', 'confirm_upgrade_dev', 'cancel_upgrade_dev', true);
        
        let url_click_event = url_update_zzz;
        let dev_version = $("#upgrade_dev_menu>option:selected").val();
        let postdata_click_event = 'action=dev_upgrade&dev_version=' + dev_version;
		
        if (dev_version == "None")
        {
            $('#status_upgrade_dev').html('ERROR: no version selected');
            //-----undo the hide-----
            $('#upgrade_dev').removeClass('hide_item');
            $('#upgrade_dev').addClass('clickable');
        }
        else
        {
            $.post(url_click_event, postdata_click_event)
            .done(function(data){
                $('#status_upgrade_dev').html(data);
            })
            .fail(function(){
                $('#status_upgrade_dev').html('ERROR requesting dev upgrade');
            });    
        }
	});
}

//--------------------------------------------------------------------------------

function pip_check_button_loading() {
    $('#load_python_pip_versions').addClass('hide_item')
    $('#wait_python_pip_versions').removeClass('hide_item')
    $('#python_pip_version_data').html('Loading... (should take around 12 seconds)');
    $('#pipdeptree').html('');
}

//--------------------------------------------------------------------------------

function pipdeptree_button_loading() {
    $("#pip_info")[0].scrollIntoView();
    $('#pipdeptree').html('<p><span class="warning_text">Loading PipDepTree data...</span></p>');
    $('#pipdeptree').show();
}

//--------------------------------------------------------------------------------

function attach_click_events_pipdeptree() {
    ($('.pipdeptree')).click(function(){
        setTimeout(pipdeptree_button_loading, 1);
        load_pipdeptree($(this).attr("data-onclick"));
    });
}

//--------------------------------------------------------------------------------

function load_pipdeptree(package_name, all_packages=false) {
    let postdata = `action=pipdeptree&package_name=${package_name}`;
    if (all_packages) { postdata += '&all_packages=TRUE'; }
    let status_field = $('#pipdeptree');
    let error_html = '<span class="text_red">ERROR</span>';

    $.post({
        'url': url_update_zzz,
        'data': postdata,
        'success': null,
        'dataType': 'text' // html, json, script, text, xml
    })
    .done(function(data){
        status_field.html(data);
    })
    .fail(function(){
        status_field.html(error_html);
    });
}
