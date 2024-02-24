//-----IP Log UI-----
// this JS assumes that services.js has been loaded in the page already

//-----load the relevant jQuery code for the page-----
function load_js_ip_log()
{
    //-----attach click triggers to clickable page elements-----
    $("#checkbox_private_ip").change(function() {
        //TODO: hide() can skip the process_show_hide() and just hide the matching class
        //show_loading_overlay_timer();
        //$('#loading_overlay').show();
        //process_show_hide();
        enable_overlay();
        setTimeout(process_show_hide, 1);
        //$('#loading_overlay').hide();
        //hide_loading_overlay_timer();
    });
    
    $("#checkbox_accepted").change(function() {
        //TODO: hide() can skip the process_show_hide() and just hide the matching class
        //show_loading_overlay_timer();
        //process_show_hide();
        enable_overlay();
        setTimeout(process_show_hide, 1);
        //$('#loading_overlay').hide();
    });
    
    //TODO: move this to attach_dynamic_events_ip_log() when user list is ready
    //-----hide output from all users except the selected user-----
    // all means show all
    // re-apply the hide() checkboxes from HTTP status codes after making changes here
    $(":radio[name=limit_by_user]").change(function() {
        //show_loading_overlay_timer();
        //process_show_hide();
        enable_overlay();
        setTimeout(process_show_hide, 1);
        //$('#loading_overlay').hide();
    });
    
    //-----toggle whether the selected country is hidden or shown-----
    $(":radio[name=country_display]").change(function() {
        //setTimeout(show_loading_overlay_timer, 1);
        //process_show_hide(true);
        enable_overlay();
        setTimeout(process_show_hide, 1);
        
        //$('#loading_overlay').hide();
    });
    
    //-----toggle whether the daily data or summary data is shown-----
    $("#checkbox_show_summary").change(function() {
        if ($("#checkbox_show_summary:checked").length>0)
        {
            $('#logdata').hide();
            $('#div_summary_data').show();
            console.log("show summary data");
        }
        else
        {
            $('#div_summary_data').hide();
            $('#logdata').show();
            console.log("show daily data");
        }
    });
    
    $('#ip_log_parse_now').click(function() {
        ip_log_parse_now();
    });
    
    $('#update_results').click(function() {
        //$('#log_options_lines').submit();
        
        // run on a delay or it won't run at all inside a "click" function
        enable_overlay();
        //setTimeout(show_loading_overlay_timer, 1);
        
        let max_age = $('#max_age>option:selected').val();
        let sort_by = $('#sort_by>option:selected').val();
        load_ip_log_data(max_age, sort_by);
        
        // run on a delay or it won't run at all inside a "click" function
        //hide_loading_overlay_timer();
        //setTimeout(hide_loading_overlay_timer, 1);
    });
    
    //--------------------------------------------------------------------------------
    
    //-----double-check if the user really wants to delete OLD IP log data-----
    attach_click_events_start_cancel_confirm('ip_delete_old', 'confirm_ip_delete_old', 'cancel_ip_delete_old', 'status_ip_delete_old', url_iptables_log, 'action=ip_delete_old');
    
    //-----double-check if the user really wants to delete ALL IP log data-----
    attach_click_events_start_cancel_confirm('ip_delete_all', 'confirm_ip_delete_all', 'cancel_ip_delete_all', 'status_ip_delete_all', url_iptables_log, 'action=ip_delete_all');
    
    console.log("ip_log Ready.");
    
    return true;
}

//--------------------------------------------------------------------------------

// elements replaced by AJAX need their click events re-attached
function attach_dynamic_events_ip_log()
{
    //-----hide output from all countries except the selected country-----
    // all means show all
    // re-apply the hide() checkboxes from HTTP status codes after making changes here
    $(":radio[name=limit_by_country]").change(function() {
        enable_overlay();
        setTimeout(process_show_hide, 1);
        //show_loading_overlay_timer();
        //process_show_hide();
        
        //$('#loading_overlay').hide();
    });
    
    //-----assumes the page loaded services.js-----
    attach_copy_to_clipboard();
    apply_onclick_events();
}

//--------------------------------------------------------------------------------

function clear_status_ip_log_parse_now()
{
    $('#status_ip_log_parse_now').html('');
}

function ip_log_parse_now()
{
    // url_iptables_log
    // https://services.zzz.zzz/z/iptables_log?
    let postdata = 'action=ip_log_parse_now';
    let status_field = $('#status_ip_log_parse_now');
    status_field.html('Submitting...');

    $.post(url_iptables_log, postdata)
    .done(function(data){
        status_field.html(data);
    })
    .fail(function(){
        status_field.html('ERROR');
    })
    .always(function(){
        //-----auto-clear the message after a short time-----
        status_ip_log_parse_now_timer = setTimeout(clear_status_ip_log_parse_now, 3000);
    });
}

//--------------------------------------------------------------------------------

//-----process all changes to the show/hide checkboxes and radio buttons-----
function process_show_hide(show_overlay=true){
    let start_time = performance.now();
    // hide the table for faster row changes
    $('#logdata').hide();

    if (show_overlay) { show_loading_overlay_timer(); }
    //setTimeout(show_loading_overlay_timer, 1);
    
    let selected_user = $(":radio[name=limit_by_user]:checked").val();
    console.log("selected_user=" + selected_user);
    
    let selected_country = $(":radio[name=limit_by_country]:checked").val();
    console.log("selected_country=" + selected_country);
    
    let selected_country_display = $(":radio[name=country_display]:checked").val();
    console.log("selected_country_display=" + selected_country_display);
    
    //-----show all rows-----
    $("#logdata>tbody>tr").show();
    
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
        //-----show all rows (above)-----
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
    
    if ($("#checkbox_private_ip:checked").length>0)
    {
        $('.private_ip').hide();
        console.log("hide private_ip");
    }
    
    //-----accepted class is only applied if there are zero blocked entries-----
    if ($("#checkbox_accepted:checked").length>0)
    {
        $('.accepted').hide();
        console.log("hide accepted");
    }
    
    //$('#loading_overlay').hide();
    hide_loading_overlay_timer();
    $('#logdata').show();
    
    let runtime = (performance.now() - start_time)/1000;
    console.log(`process_show_hide() - ${runtime.toFixed(2)} seconds`);
}

//--------------------------------------------------------------------------------

/* HTML table - #logdata
 * countries - #list_of_countries
 * IP list - var ip_list
 * Logs Last Parsed - #last_time_parsed
 * VPN users - #vpn_user_ips
 * IP-User Map - ip_user_map?
 * re-attach JS change actions to limit-by-country radio buttons
 */
function process_log_data(data)
{
    let start_time = performance.now();
    console.log('process_log_data() - START');
    
    // hide the table for faster row changes
    $('#logdata').hide();
    
    // HTML table - #logdata
    $('#logdata').html('<tbody>' + data.logdata + '</tbody>');
    
    // these also update in 30-second intervals
    $('#last_time_parsed').html(data.last_time_parsed);
    $('#last_time_parsed_seconds').html(data.last_time_parsed_seconds);
    
    // this only updates here
    let time_new = Math.round(Date.now()/1000);
    let minutes_ago = (time_new - data.last_time_parsed_seconds)/60;
    $('#parsed_data_age_minutes').html(minutes_ago);
    
    $('#list_of_countries').html(data.list_of_countries);
    
    // ip_list global JS variable initialized in the HTML template
    ip_list = data.ip_list;
    
    start_calc_minutes_ago();
    
    attach_dynamic_events_ip_log();
    
    $('#logdata').show();
    
    let runtime = (performance.now() - start_time)/1000;
    console.log(`process_log_data() - DONE - ${runtime.toFixed(2)} seconds`);
}

//--------------------------------------------------------------------------------

//-----load data with AJAX-----
function load_ip_log_data(load_max_age, load_sort_by)
{
    console.log('load_ip_log_data(' + load_max_age + ', ' + load_sort_by + ')');

    enable_overlay();
    show_loading_overlay_timer();
    
    let highlight_ips = '&highlight_ips=0';
    if ($("#checkbox_highlight_ips:checked").length>0) { highlight_ips = '&highlight_ips=1'; }
    
    let ip_log_post_start_time = performance.now();
    
    let postdata = 'action=ip_log_view&max_age=' + load_max_age + '&sort_by=' + load_sort_by + highlight_ips;

    $.post({
        'url': url_iptables_log,
        'data': postdata,
        'success': null,
        'dataType': 'json' // html, json, script, text, xml
    })
    .done(function(data){
        let runtime = (performance.now() - ip_log_post_start_time)/1000;
        console.log(`ip_log post time: ${runtime.toFixed(2)} seconds`);
        process_log_data(data);
        // hide_loading_overlay_timer();
        setTimeout(process_show_hide, 1, false);
    })
    .fail(function(){
        console.log('load_ip_log_data() - POST failed');
        $('#logdata').html('<tbody><tr><td><b>ERROR loading data</b></td></tr></tbody>');
        hide_loading_overlay_timer();
    });
}

//--------------------------------------------------------------------------------
