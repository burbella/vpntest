/* services.js - common features used on all pages
    loads in the header template
*/

console.log("services.js - START");

var clock_update_timer = null;
var minutes_ago_timer = null;
var loading_timer = null;

var loading_start_time = 0;
var overlay_enabled = false;

//-----global URL's-----
// the zzz_https_url JS var is set in zzz_config.js, which is loaded into every page by header.template
// header.template is populated by the template processor using zzz.conf domain data
// OLD format:
//   var url_edit_dns = location.protocol + '//' + app_domain + '/z/edit_dns';
var url_db_view = zzz_https_url + '/z/db_view';
var url_edit_dns = zzz_https_url + '/z/edit_dns';
var url_edit_ip = zzz_https_url + '/z/edit_ip';
var url_iptables_log = zzz_https_url + '/z/iptables_log';
var url_ip_log_raw_data = zzz_https_url + '/z/ip_log_raw_data';
var url_list_manager = zzz_https_url + '/z/list_manager';
var url_network_service = zzz_https_url + '/z/network_service';
var url_settings = zzz_https_url + '/z/settings';
var url_squid_log = zzz_https_url + '/z/squid_log';
var url_update_os = zzz_https_url + '/z/update_os';
var url_update_zzz = zzz_https_url + '/z/update_zzz';

//--------------------------------------------------------------------------------

function toggle_expand(css_row_id)
{
    if ($('#' + css_row_id).hasClass('content_collapsed')) {
        $('#' + css_row_id).removeClass('content_collapsed').addClass('content_expanded').addClass('border-green');
    }
    else {
        $('#' + css_row_id).removeClass('content_expanded').removeClass('border-green').addClass('content_collapsed');
    }
}

//--------------------------------------------------------------------------------

function pad_zeros(num)
{
    if (num < 10) { num = "0" + num; }
    return num;
}

function load_ip_last_parsed_time()
{
    let postdata = 'action=ip_log_last_parsed_time';

    $.post({
        'url': url_iptables_log,
        'data': postdata,
        'success': null,
        'dataType': 'json' // html, json, script, text, xml
    })
    .done(function(data){
        // console.log('load_ip_last_parsed_time() - POST done');
        //-----check the return value-----
        if (data.status=='success') {
            //-----success - update the HTML page-----
            if (data.last_time_parsed_seconds>0)
            {
                $('#last_time_parsed').html(data.last_time_parsed);
                $('#last_time_parsed_seconds').html(data.last_time_parsed_seconds);
                
                let time_new = Math.round(Date.now()/1000);
                let time_old = data.last_time_parsed_seconds;
                let minutes_ago_rounded = Math.round((time_new - time_old)/60);
                $('#minutes_ago').html(pluralize_minutes(minutes_ago_rounded));
            }
        } else {
            console.log(data.error_msg);
        }
    })
    .fail(function(){
        console.log('load_ip_last_parsed_time() - POST failed');
    })
    .always(function(){
    });
}

function pluralize_minutes(minutes)
{
    let plural = ' minutes ago';
    if (minutes==1) { plural = ' minute ago'; }
    
    // use days when minutes>4320
    if (minutes>(1440*3)) {
        let days = Math.round(minutes/(60*24));
        if (days==1) { plural = ' day ago'; }
        else { plural = ' days ago'; }
        return days + plural;
    }
    
    // use hours when minutes>180
    if (minutes>180) {
        let hours = Math.round(minutes/60);
        if (hours==1) { plural = ' hour ago'; }
        else { plural = ' hours ago'; }
        return hours + plural;
    }
    
    return minutes + plural;
}

function get_num_or_zero(num)
{
    if (isNaN(num)) { return 0; }
    return parseFloat(num);
}

//-----given 2 times, calculate the minutes difference-----
// minutes_ago = current_time_seconds - last_time_parsed_seconds
function calc_minutes_ago()
{
    load_ip_last_parsed_time();
    
    let time_new = Math.round(Date.now()/1000);
    let time_old = get_num_or_zero($('#last_time_view_updated_seconds').text());
    let minutes_ago = (time_new - time_old)/60;
    let parsed_data_age_minutes = get_num_or_zero($('#parsed_data_age_minutes').text());
    
    let minutes_ago_rounded = Math.round(minutes_ago);
    $('#view_updated_minutes_ago').html(pluralize_minutes(minutes_ago_rounded));
    
    let view_data_minutes_ago_rounded = Math.round(parsed_data_age_minutes + minutes_ago);
    $('#view_data_minutes_ago').html(pluralize_minutes(view_data_minutes_ago_rounded));
}

function start_calc_minutes_ago()
{
    // reset a previous timer
    if (minutes_ago_timer!=null) { clearInterval(minutes_ago_timer); }
    
    let time_now = Math.round(Date.now()/1000);
    $('#last_time_view_updated_seconds').html(time_now);
    let d = new Date();
    let yyyy = d.getUTCFullYear();
    let mm = pad_zeros(d.getUTCMonth()+1);
    let dd = pad_zeros(d.getUTCDate());
    let h = pad_zeros(d.getUTCHours());
    let m = pad_zeros(d.getUTCMinutes());
    let s = pad_zeros(d.getUTCSeconds());
    let show_date_updated = yyyy + '-' + mm + '-' + dd + ' ' + h + ":" + m + ":" + s;
    
    $('#last_time_view_updated').html(show_date_updated);
    
    calc_minutes_ago();
    minutes_ago_timer = setInterval(calc_minutes_ago, 1000*30);
}

function update_clock()
{
    let today = new Date();
    let h = today.getHours();
    let m = pad_zeros(today.getMinutes());
    let s = pad_zeros(today.getSeconds());
    
    let utc_h = today.getUTCHours();
    let utc_m = pad_zeros(today.getUTCMinutes());
    let utc_s = pad_zeros(today.getUTCSeconds());
    
    $('#show_clock').html("Local: " + h + ":" + m + ":" + s + " | UTC: " + utc_h + ":" + utc_m + ":" + utc_s);
}

function start_clock()
{
    update_clock();
    clock_update_timer = setInterval(update_clock, 1000);
}

//--------------------------------------------------------------------------------

function show_with_block(dom_obj)
{
    dom_obj.css('display', 'block');
}

function update_loading_timer()
{
    if (!overlay_enabled)
    {
        hide_loading_overlay_timer();
        return;
    }
    
    let time_new = Math.round(Date.now()/1000);
    let seconds_ago = time_new - loading_start_time;
    $('#loading_timer').text(seconds_ago);
}

function enable_overlay() { overlay_enabled = true; }
function disable_overlay() { overlay_enabled = false; }

function show_loading_overlay_timer()
{
    $('#loading_overlay').show();
    $('#loading_timer').text('0');
    loading_start_time = Math.round(Date.now()/1000);
    update_loading_timer();
    if (loading_timer) { clearInterval(loading_timer); }
    loading_timer = setInterval(update_loading_timer, 500);
    
    //TEST
    // current_time=Date.now()/1000;
    // console.log('show_overlay time: ' + current_time);
}

function hide_loading_overlay_timer()
{
    disable_overlay();
    clearInterval(loading_timer);
    $('#loading_overlay').hide();
    $('#loading_timer').text('');
    
    //TEST
    // current_time=Date.now()/1000;
    // console.log('hide_overlay time: ' + current_time);
}

//--------------------------------------------------------------------------------

//-----check if we have an IP-----
// the only things that call this function would only be generating valid IP's, so no need for a fancy check
function is_ip_simple(host)
{
    if (/^(\d{1,3}\.){3}\d{1,3}$/.test(host))
    {
        return true;
    }
    return false;
}

//--------------------------------------------------------------------------------

//-----load a given URL in a new window-----
function search_google(str)
{
    window.open('https://www.google.com/search?q=' + str);
}

function external_whois(domain)
{
    window.open('https://www.whois.com/whois/' + domain);
}

function search_whois(host)
{
    //window.open('https://www.whois.com/whois/' + str);
    // window.open('https://' + app_domain + '/z/whois?host=' + host);
    window.open('https://' + app_domain + '/z/network_service?action=whois&host=' + host);
}

function do_nslookup(host)
{
    // window.open('https://' + app_domain + '/z/nslookup?host=' + host);
    window.open('https://' + app_domain + '/z/network_service?action=nslookup&host=' + host);
}

function reverse_dns_popup(host)
{
    // window.open('https://' + app_domain + '/z/nslookup?host=' + host);
    window.open('https://' + app_domain + '/z/network_service?action=reverse_dns&host=' + host);
}

function search_ipinfo(ip) {
    window.open('https://ipinfo.io/' + ip);
}

function search_ip_rep(ip) {
    window.open(`https://viz.greynoise.io/ip/${ip}`);
}

//--------------------------------------------------------------------------------

function clipboard_html_reset(item, original_text)
{
    item.removeClass('warning_text');
    item.text(original_text);
}

// pass in jquery object - should be an HTML tag containing text
// text goes into clipboard
// prep the text's parent html tag with class="cursor_copy"
// then run attach_copy_to_clipboard();
function copy_to_clipboard(item)
{
    let original_text = item.text();
    navigator.clipboard.writeText(original_text);
    item.addClass('warning_text');
    item.text('Copied');
    setTimeout(clipboard_html_reset, 1000, item, original_text);
}

//--------------------------------------------------------------------------------

//-----general function to implement the 3-button start-confirm-cancel for a task-----

//-----switch back to start section-----
// pass in ID values for the relevant tags
function switch_confirm_to_start(id_start, id_confirm, id_cancel, hide_on_confirm)
{
    if (!hide_on_confirm) {
        $('#' + id_start).removeClass('hide_item');
        $('#' + id_start).addClass('clickable');
    }
    
    $('#' + id_confirm).removeClass('clickable');
    $('#' + id_confirm).addClass('hide_item');
    
    $('#' + id_cancel).removeClass('clickable_red');
    $('#' + id_cancel).addClass('hide_item');
}

//-----used by attach_click_events_start_cancel_confirm() below-----
// also used by functions that need custom confirm() code
function attach_click_events_start_cancel(id_start, id_confirm, id_cancel)
{
    $('#' + id_start).click(function() {
        $('#' + id_confirm).removeClass('hide_item');
        $('#' + id_confirm).addClass('clickable');
        
        $('#' + id_cancel).removeClass('hide_item');
        $('#' + id_cancel).addClass('clickable_red');
        
        $('#' + id_start).removeClass('clickable');
        $('#' + id_start).addClass('hide_item');
    });
    // switch confirm back to start
    $('#' + id_cancel).click(function() {
        switch_confirm_to_start(id_start, id_confirm, id_cancel);
    });
}

//-----attach given click event function to a given webpage object (usually an <a> tag)-----
/* usage example in: ip_log.js
 *   this function should be called inside the load_js_PAGENAME() function
 *   attach_click_events_start_cancel_confirm('ip_delete_all', 'confirm_ip_delete_all', 'cancel_ip_delete_all', 'status_ip_delete_all', url_iptables_log, 'action=ip_delete_all');
 * double-check if the user really wants to do the action
 * switch start to confirm
 * buttons: id_start, id_confirm, id_cancel
 * URL generally looks like:
 *   var url_iptables_log = location.protocol + '//' + app_domain + '/z/iptables_log';
 *   app_domain is auto-defined in the headers of all pages
 *   NEW URL 2021:
 *     var url_iptables_log = zzz_https_url + '/z/iptables_log';
 * postdata generally looks like:
 *   var postdata = 'action=ip_delete_all';
 * id_status is a <div> or other tag where status text from the server will be inserted
 * hide_on_confirm=true if you want the Confirm button to stay hidden after it is clicked (currently only used for OS Reboot)
 */
function attach_click_events_start_cancel_confirm(id_start, id_confirm, id_cancel, id_status, url_click_event, postdata_click_event, hide_on_confirm=false)
{
    attach_click_events_start_cancel(id_start, id_confirm, id_cancel);
    
    //-----do the requested action on confirm-----
    $('#' + id_confirm).click(function() {
        let status_field = $(`#${id_status}`);
        let error_html = '<span class="text_red">ERROR</span>';

        status_field.html('Submitting...');

        switch_confirm_to_start(id_start, id_confirm, id_cancel, hide_on_confirm);

        $.post({
            'url': url_click_event,
            'data': postdata_click_event
            //-----for now, rely on auto-detect for dataType-----
            // 'success': null,
            //'dataType': 'json' // html, json, script, text, xml
        })
        .done(function(data){
            status_field.html(data);
        })
        .fail(function(){
            status_field.html(error_html);
        })
        .always(function(){
        });
    });
}

//--------------------------------------------------------------------------------

function attach_content_collapsed_toggle() {
    $('.content_collapsed').click(function() {
        let row_id = $(this).attr('id');
        toggle_expand(row_id);
    });
}

//--------------------------------------------------------------------------------

function attach_copy_to_clipboard() {
    $('.cursor_copy').click(function() {
        copy_to_clipboard($(this));
    });
}

//--------------------------------------------------------------------------------

function apply_onclick_events() {
    // (G)
    $(".search_google").click(function() {
        // base64 decode
        search_google(atob($(this).attr("data-onclick")));
    });
    // External Whois
    $(".external_whois").click(function() {
        // base64 decode
        external_whois(atob($(this).attr("data-onclick")));
    });
    // (L) - location
    $(".search_ipinfo").click(function() {
        // base64 decode
        search_ipinfo(atob($(this).attr("data-onclick")));
    });
    // (R) - reputation
    $(".search_ip_rep").click(function() {
        // base64 decode
        search_ip_rep(atob($(this).attr("data-onclick")));
    });
    
    // only ip_log and squid_log need these?
    // (D) (S) - domain, subdomain
    $(".block_dns").click(function() {
        block_dns(this, $(this).attr("data-onclick"));
    });
    // (I)
    $(".block_ip").click(function() {
        block_ip(this, $(this).attr("data-onclick"));
    });
    // (N)
    $(".do_nslookup").click(function() {
        // base64 decode
        do_nslookup(atob($(this).attr("data-onclick")));
    });
    // (R)
    $(".reverse_dns").click(function() {
        reverse_dns($(this).attr("data-onclick"));
    });
    // (R) - with popup
    $(".reverse_dns_popup").click(function() {
        reverse_dns_popup($(this).attr("data-onclick"));
    });
    $(".reverse_dns_load_batch").click(function() {
        reverse_dns_load_batch();
    });
    // (W)
    $(".search_whois").click(function() {
        // base64 decode
        search_whois(atob($(this).attr("data-onclick")));
    });
    
    // only network_service.js need these
    // (D)
    $(".whois_delete").click(function() {
        // base64 decode
        whois_delete($(this).attr("data-onclick-tr-id"), atob($(this).attr("data-onclick-domain")));
    });
    // (D)
    $(".ipwhois_delete").click(function() {
        ipwhois_delete($(this).attr("data-onclick-tr-id"), $(this).attr("data-onclick-ip"));
    });
}

//--------------------------------------------------------------------------------

function show_hide_object(obj_name, anchor_name, anchor_text_show, anchor_text_hide) {
    $('#' + obj_name).toggle();
    if ($('#' + obj_name).is(":visible")) { $('#' + anchor_name).html(anchor_text_hide); }
    else { $('#' + anchor_name).html(anchor_text_show); }
}

// set the HTML for a given object, wait a given amount of time, then clear the HTML
function print_html_delay_clear(obj_name, html_set, html_clear='', milliseconds=1000) {
    $(`#${obj_name}`).html(html_set);
    setTimeout(function() {
        $(`#${obj_name}`).html(html_clear);
    }, milliseconds);
}

//--------------------------------------------------------------------------------

/* Color-Changing Click-Submit-Status for clickable objects
 * start out red
 * turn yellow after click
 * if successful, turn green
 * otherwise, turn back to red
 */
function click_color_change(args) {
    //TEST
}

//--------------------------------------------------------------------------------

console.log("services.js - LOADED");
