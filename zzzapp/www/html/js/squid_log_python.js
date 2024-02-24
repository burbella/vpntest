//-----load the relevant jQuery code for the page-----
function load_js_squid_log()
{
    //-----attach click triggers to clickable page elements-----
    $("#checkbox_403").change(function() {
        //TODO: hide() can skip the process_show_hide() and just hide the matching class
        enable_overlay();
        setTimeout(process_show_hide, 1);
    });

    $("#checkbox_200").change(function() {
        //TODO: hide() can skip the process_show_hide() and just hide the matching class
        enable_overlay();
        setTimeout(process_show_hide, 1);
    });
    
    $("#checkbox_duplicates").change(function() {
        //TODO: hide() can skip the process_show_hide() and just hide the matching class
        enable_overlay();
        setTimeout(process_show_hide, 1);
    });
    
    $("#checkbox_dns_blocked").change(function() {
        //TODO: hide() can skip the process_show_hide() and just hide the matching class
        enable_overlay();
        setTimeout(process_show_hide, 1);
    });
    
    $("#checkbox_extra_columns").change(function() {
        //TODO: hide() can skip the process_show_hide() and just hide the matching class
        enable_overlay();
        setTimeout(process_show_hide, 1);
    });
    
    $("#checkbox_more_columns").change(function() {
        //TODO: hide() can skip the process_show_hide() and just hide the matching class
        enable_overlay();
        setTimeout(process_show_hide, 1);
    });
    
    $('#clear_dns_updates').click(function() {
        //-----clear the list-----
        $('#dns_updates').val('');
        
        //-----clear previous status entries-----
        $('#status_dns_updates').html('');
        
        //-----turn the green items back to red-----
        $('.queued_dns').removeClass('update_success').addClass('clickable_red').removeClass('queued_dns');
    });
    
    $('#dns_commit_updates').click(function() {
        upload_dns_denylist();
    });
    
    //-----toggle whether the selected country is hidden or shown-----
    $(":radio[name=country_display]").change(function() {
        enable_overlay();
        setTimeout(process_show_hide, 1);
    });
    
    $('#update_results').click(function() {
        enable_overlay();
        show_loading_overlay_timer();
        let lines_to_analyze = $('#lines_to_analyze').val();
        load_squid_log_data(lines_to_analyze, do_hide_overlay=true);
        // setTimeout(load_squid_log_data, 1, lines_to_analyze);
    });
    
    //--------------------------------------------------------------------------------
    
    //-----double-check if the user really wants to delete OLD squid log data-----
    attach_click_events_start_cancel_confirm('squid_delete_old', 'confirm_squid_delete_old', 'cancel_squid_delete_old', 'status_squid_delete_old', url_squid_log, 'action=squid_delete_old');
    
    //-----double-check if the user really wants to delete ALL squid log data-----
    attach_click_events_start_cancel_confirm('squid_delete_all', 'confirm_squid_delete_all', 'cancel_squid_delete_all', 'status_squid_delete_all', url_squid_log, 'action=squid_delete_all');
    
    console.log("squid_log Ready.");
    
    return true;
}

//--------------------------------------------------------------------------------

//-----process all changes to the show/hide checkboxes and radio buttons-----
function process_show_hide()
{
    show_loading_overlay_timer();

    let selected_user = $(":radio[name=limit_by_user]:checked").val();
    console.log("selected_user=" + selected_user);

    let selected_country = $(":radio[name=limit_by_country]:checked").val();
    console.log("selected_country=" + selected_country);

    let selected_country_display = $(":radio[name=country_display]:checked").val();
    console.log("selected_country_display=" + selected_country_display);

    // START: show all rows (in case some are hidden from a previous filter)
    // if all users and all countries:
    //   just show all
    // if all users and one country:
    //   hide all, show the one country
    // if one user and all countries:
    //   hide all, show the one user
    // if one user and one country:
    //   ???
    if(selected_user=='all' && selected_country=='all')
    {
        //-----never process country_display flag here because it will show all/none results-----
        //-----show all rows-----
        $("tr[class*=' client_']").show();
    }
    else if (selected_user=='all')
    {
        //-----show selected country-----
        // if country_display=='show', show only that country
        // if country_display=='hide', hide only that country
        if (selected_country_display=='hide')
        {
            $("tr[class*=' country_']").show();
            $("." + selected_country).hide();
            console.log("hide selected country");
        }
        else
        {
            $("tr[class*=' country_']").hide();
            $("." + selected_country).show();
            console.log("show selected country");
        }
    }
    else if (selected_country=='all')
    {
        //-----never process country_display flag here because it will show all/none results-----
        //-----show selected user-----
        $("tr[class*=' client_']").hide();
        $("." + selected_user).show();
        console.log("show selected client");
    }
    else
    {
        //-----select by user AND country, without any excess rows appearing-----
        if (selected_country_display=='hide')
        {
            // hide rows from all clients
            // show only rows where user matches selection
            // then hide rows where country matches selection
            $("tr[class*=' client_']").hide();
            $("." + selected_user).show();
            $("." + selected_country).hide();
        }
        else
        {
            // hide rows from all clients
            // show only rows where country and user match selections
            $("tr[class*=' client_']").hide();
            $("." + selected_country).filter("." + selected_user).show();
        }
    }
    
    //-----hide http status-----
    if ($("#checkbox_403:checked").length>0)
    {
        $('.status_403').hide();
        console.log("hide 403");
    }
    
    if ($("#checkbox_200:checked").length>0)
    {
        $('.status_200').hide();
        console.log("hide 200");
    }
    
    if ($("#checkbox_duplicates:checked").length>0)
    {
        $('.dup_domain').hide();
        console.log("hide dup_domain");
    }
    
    if ($("#checkbox_dns_blocked:checked").length>0)
    {
        $('.dns_blocked').hide();
        console.log("hide dns_blocked");
    }
    
    if ($("#checkbox_extra_columns:checked").length>0)
    {
        $('.extra_column').hide();
        console.log("hide extra_column");
    }
    else
    {
        $('.extra_column').show();
        console.log("hide extra_column");
    }
    
    if ($("#checkbox_more_columns:checked").length>0)
    {
        $('.more_column').hide();
        console.log("hide more_column");
    }
    else
    {
        $('.more_column').show();
        console.log("hide more_column");
    }

    hide_loading_overlay_timer();
}

//--------------------------------------------------------------------------------

// elements replaced by AJAX need their click events re-attached
function attach_dynamic_events_squid_log()
{
    //-----hide output from all users except the selected user-----
    // all means show all
    // re-apply the hide() checkboxes from HTTP status codes after making changes here
    $(":radio[name=limit_by_user]").change(function() {
        enable_overlay();
        setTimeout(process_show_hide, 1);
    });
    
    //-----hide output from all countries except the selected country-----
    // all means show all
    // re-apply the hide() checkboxes from HTTP status codes after making changes here
    $(":radio[name=limit_by_country]").change(function() {
        enable_overlay();
        setTimeout(process_show_hide, 1);
    });
    
    //-----assumes the page loaded services.js-----
    attach_copy_to_clipboard();
    apply_onclick_events();
}

//--------------------------------------------------------------------------------

function process_log_data_squid(data)
{
    let start_time = performance.now();
    console.log('process_log_data_squid() - START');
    //console.log(JSON.stringify(data.js_ip_list));
    
    // hide the table for faster row changes
    $('#logdata').hide();
    
    // HTML table - #logdata
    $('#logdata').html('<tbody>' + data.logdata + '</tbody>');

    // ip_list global JS variable initialized in the HTML template
    ip_list = JSON.parse(data.js_ip_list);

    //$('#last_time_parsed').html(data.last_time_parsed);
    //$('#last_time_parsed_seconds').html(data.last_time_parsed_seconds);
    $('#list_of_users').html(data.list_of_users);
    $('#list_of_countries').html(data.list_of_countries);
    
    $('#lines_in_logfile').html(data.lines_in_logfile);
    $('#lines_analyzed').html(data.lines_to_analyze);
    $('#lines_displayed').html(data.lines_displayed);

    $('#rows_in_db').html(data.rows_in_db);
    $('#oldest_entry').html(data.oldest_entry);
    $('#newest_entry').html(data.newest_entry);

    start_calc_minutes_ago();
    attach_dynamic_events_squid_log();
    process_show_hide();

    $('#logdata').show();
    
    let runtime = (performance.now() - start_time)/1000;
    console.log(`process_log_data_squid() - DONE - ${runtime.toFixed(2)} seconds`);
}

//-----AJAX fetch data and load it into the page-----
function load_squid_log_data(lines_to_analyze, initial_load=false, do_hide_overlay=false)
{
    console.log('load_squid_log_data(' + lines_to_analyze + ')');

    let postdata = 'action=squid_log_view&lines_to_analyze=' + lines_to_analyze;
    let status_field = $('#logdata');
    let error_html = '<tbody><tr><td><b>ERROR loading data</b></td></tr></tbody>';

    $.post({
        'url': url_squid_log,
        'data': postdata,
        'success': null,
        'dataType': 'json'
    })
    .done(function(data){
        console.log('POST done');
        if (data.status=='success') {
            process_log_data_squid(data);
            if (do_hide_overlay) { hide_loading_overlay_timer(); }
        } else {
            console.log(data.error_msg);
            error_html = `<tbody><tr><td><b>ERROR loading data: ${data.error_msg}</b></td></tr></tbody>`;
            status_field.html(error_html);
        }
    })
    .fail(function(){
        console.log('POST fail');
        status_field.html(error_html);
        hide_loading_overlay_timer();
    })
    .always(function(){
    });
}

//--------------------------------------------------------------------------------

//-----POST new domains to the server-----
function upload_dns_denylist()
{
    console.log('upload_dns_denylist(): start');
    
    let status_field = $('#status_dns_updates');
    let dns_commit_button = $('#dns_commit_updates');

    //-----change/disable the button while processing the request-----
    dns_commit_button.prop('disabled', true);
    dns_commit_button.val('Uploading...');
    
    //-----clear previous status entries-----
    status_field.html('');
    
    let domain_list = encodeURIComponent($('#dns_updates').val());
    if (domain_list.length==0)
    {
        status_field.html('<span class="text_red">ERROR: empty list</span>');
        return;
    }
    
    // do POST
    let postdata = 'action=add_domains&domain_list=' + domain_list;
    let error_html = '<span class="text_red">ERROR adding domains</span>';

    $.post({
        'url': url_edit_dns,
        'data': postdata,
        'success': null,
        'dataType': 'json'
    })
    .done(function(data){
        console.log('POST done');
        //-----check the return value-----
        if (data.status=='success') {
            //-----success - erase the list from the textarea-----
            $('#dns_updates').val('');
            
            //-----display status-----
            status_field.html('Uploaded OK');
        } else {
            console.log(data.error_msg);
            error_html = `<span class="text_red">${data.status}</span>`;
            status_field.html(error_html);
        }
    })
    .fail(function(){
        console.log('POST fail');
        status_field.html(error_html);
    })
    .always(function(){
        //-----reset the button value-----
        dns_commit_button.prop('disabled', false);
        dns_commit_button.val('Commit DNS Updates');
        console.log('upload_dns_denylist(): end');
    });
}

//--------------------------------------------------------------------------------

//-----copy domain/subdomain entry to DNS-block textbox-----
function block_dns(elem, domain)
{
    console.log('block_dns: ' + domain);
    
    //-----stop repeat queuing of the same domain-----
    if ($(elem).hasClass('update_success')) { return; }
    
    //-----change to yellow while processing the request-----
    $(elem).removeClass('clickable_red').addClass('queued_for_update').addClass('queued_dns');
    
    //-----append to top of textarea-----
    let current_list = $('#dns_updates').val();
    $('#dns_updates').val(domain + "\n" + current_list);
    
    //-----if the request succeeds, change the color to indicate it-----
    console.log('block_dns: remove/add classes');
    $(elem).removeClass('queued_for_update').addClass('update_success');
}

//--------------------------------------------------------------------------------
