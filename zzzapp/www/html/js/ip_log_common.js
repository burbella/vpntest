var rdns_batches_started = 0;
var rdns_batches_done = 0;
var rdns_batch_timer = null;

//-----code here is used by both squid_log and ip_log-----
function load_js_ip_log_common()
{
    $('#clear_ip_updates').click(function() {
        //-----clear the list-----
        $('#ip_updates').val('');
        
        //-----clear previous status entries-----
        $('#status_ip_updates').html('');
        
        //-----turn the green items back to red-----
        $('.queued_ip').removeClass('update_success').addClass('clickable_red').removeClass('queued_ip');
    });
    
    $('#ip_commit_updates').click(function() {
        upload_ip_denylist();
    });
    
    console.log("ip_log_common Ready.");
    
    return true;
}

//--------------------------------------------------------------------------------

//-----POST new IP's to the server-----
function upload_ip_denylist()
{
    console.log('upload_ip_denylist(): start');
    
    //-----change/disable the button while processing the request-----
    $('#ip_commit_updates').prop('disabled', true);
    $('#ip_commit_updates').html('Uploading...');
    
    //-----clear previous status entries-----
    $('#status_ip_updates').html('');

    // do POST
    let postdata = 'action=add_ips&ip_list=' + encodeURIComponent($('#ip_updates').val());

    $.post(url_edit_ip, postdata)
    .done(function(data){
        //-----check the return value-----
        if (data == 'success') {
            //-----success - erase the list from the textarea-----
            $('#ip_updates').val('');
            
            //-----display status-----
            $('#status_ip_updates').html('Uploaded OK');
        } else {
            //-----fail - keep the list, display a note-----
            $('#status_ip_updates').html(data);
        }
    })
    .fail(function(){
        console.log('ERROR: upload_ip_denylist() POST failed')
        $('#status_ip_updates').html('ERROR: POST failed');
    })
    .always(function(){
        //-----reset the button value-----
        $('#ip_commit_updates').prop('disabled', false);
        $('#ip_commit_updates').html('Commit IP Updates');
    });
}

//--------------------------------------------------------------------------------

function block_ip(elem, ip)
{
    console.log('block_ip: ' + ip);
    
    //-----stop repeat queuing of the same domain-----
    if ($(elem).hasClass('update_success')) { return; }
    
    //-----change to yellow while processing the request-----
    $(elem).removeClass('clickable_red').addClass('queued_for_update').addClass('queued_ip');
    
    //-----append to top of textarea-----
    let current_list = $('#ip_updates').val();
    $('#ip_updates').val(ip + "\n" + current_list);
    
    //-----if the request succeeds, change the color to indicate it-----
    console.log('block_ip: remove/add classes');
    $(elem).removeClass('queued_for_update').addClass('update_success');
}

//--------------------------------------------------------------------------------

function ip_to_rdns_classname(ip)
{
    return 'rdns_' + ip.replace(/\./g, "_");
}

// recently-loaded RDNS lookups need links to google/location/whois
// duplicates functionality in LogParser.py
function make_rdns_links(host, include_dns_blocking_links=false)
{
    let show_rdns_html = host;
    
    if ((! is_ip_simple(host)) && (host != 'PRIVATE IP'))
    {
        let base64_host = btoa(host);
        show_rdns_html = '<span class="cursor_copy">' + host + '</span><br><a class="clickable search_google" data-onclick="' + base64_host + '">(G)</a><a class="clickable do_nslookup" data-onclick="' + base64_host + '">(N)</a><a class="clickable search_whois" data-onclick="' + base64_host + '">(W)</a>';
    }
    
    // only used on squid_log page?
    // need to move function(s) from squid_log.js to here?
    if (include_dns_blocking_links)
    {
        //TODO: finish this - add (D)(S) buttons
    }
    
    return show_rdns_html;
}

// one set of items gets the onclick events
function apply_onclick_events_one_class(class_rdns) {
    $('.'+class_rdns+' > .cursor_copy').click(function() {
        copy_to_clipboard($(this));
    });
    
    // (G)
    $('.'+class_rdns+' > .search_google').click(function() {
        // base64 decode
        search_google(atob($(this).attr("data-onclick")));
    });
    // (N)
    $('.'+class_rdns+' > .do_nslookup').click(function() {
        // base64 decode
        do_nslookup(atob($(this).attr("data-onclick")));
    });
    // (W)
    $('.'+class_rdns+' > .search_whois').click(function() {
        // base64 decode
        search_whois(atob($(this).attr("data-onclick")));
    });
}

//-----request Reverse-DNS lookup, print the output in the appropriate table cells-----
function reverse_dns(ip)
{
    //-----assemble the classname from the IP-----
    let class_rdns = ip_to_rdns_classname(ip);
    
    $('.' + class_rdns).html('Loading...');
    
    let ip_batch = [ip];
    rdns_batch_lookup(ip_batch, true);
}

//TODO: not used anymore? remove this?
//-----load all reverse DNS entries on the page------
// show running total (EX: Loading 17/100)
// include a stop button in case it takes too long
function reverse_dns_load_all()
{
    console.log("reverse_dns_load_all");
    
    /* Count the number of all/unhidden clickable RDNS links
     * Figure out which ones have no data currently loaded in the RDNS output column
     * Trigger a click on each link
     * Avoid duplicate clicks on the same IP
     */
    // <div id='rdns_load_all'><a id='rdns_load_all_start'>(Load ALL)</a></div>
    //$('#myDiv').is(':visible');
    //$("td[class*=' rdns_']");
    //$("div[class^='apple-'],div[class*=' apple-']")
    //<a class="clickable" onclick="reverse_dns('104.16.58.249');">(R)</a>
    //<td class=" rdns_104_16_58_249">104.16.58.249</td>
    
    //-----extract the IP from the classname, store in list-----
    //rdns_104_16_58_249
    /*
    let str="test\n";
    $("td[class*=' rdns_']").each(function() {
        str = $('#test_output').val() + $(this).attr("class") + "\n";
        $('#test_output').val(str);
        
    });
    */
    
    // ip_list needs to be a JS var in the page template, populated by python
    $.each(ip_list, function( index, value ) {
        let class_rdns = ip_to_rdns_classname(value);
        if ($('.' + class_rdns).first().html() == '')
        {
            //-----load reverse DNS only for empty table cells-----
            reverse_dns(value);
        }
    });
}

function rdns_batch_lookup(ip_batch, individual_lookup=false)
{
    rdns_batches_started++;
    let postdata = 'action=reverse_dns&ip=' + ip_batch.join(',');

    $.post({
        'url': url_network_service, // url_network_service is defined in services.js
        'data': postdata,
        'success': null,
        'dataType': 'json' // html, json, script, text, xml
    })
    .done(function(data){
        // process JSON full of IP-RDNS pairs
        $.each(data, function( index, value ) {
            let class_rdns = ip_to_rdns_classname(index);
            $('.' + class_rdns).html(make_rdns_links(value));
            //-----after make_rdns_links() output is put in the page, apply_onclick_events_one_class()-----
            apply_onclick_events_one_class(class_rdns);
        });
    })
    .fail(function(){
        // class_rdns is undefined here, need to loop thru the ip_batch array, or retry?
        // there are currently no success or fail status updates for batch lookups
        // $('.' + class_rdns).html('POST ERROR');

        if (individual_lookup) {
            let class_rdns = ip_to_rdns_classname(ip_batch[0]);
            $('.' + class_rdns).html('POST ERROR');
        }
    })
    .always(function(){
        rdns_batches_done++;
    });

}

function rdns_disable_button() {
    $('.reverse_dns_load_batch').removeClass('clickable').addClass('warning_text').html('Loading...');
}

function rdns_enable_button(items_sent) {
    if (items_sent>0) {
        if ((rdns_batches_started==0) || (rdns_batches_started > rdns_batches_done)) {
            return;
        }
    }
    $('.reverse_dns_load_batch').removeClass('warning_text').addClass('clickable').html('(Load ALL)');
    clearInterval(rdns_batch_timer);
}

//-----load all reverse DNS entries on the page, multiple IP's at a time to reduce AJAX requests------
//TODO: load batch size from config into hidden HTML field, then load from HTML into jquery
function reverse_dns_load_batch()
{
    console.log("reverse_dns_load_batch");

    //-----change/disable the button while processing the request-----
    setTimeout(rdns_disable_button, 1);

    let items_sent = 0;
    let ip_batch = [];
    let batch_size = 10; //TODO: load from HTML element
    $.each(ip_list, function( index, value ) {
        // check if the IP's element is visible
        // for multiple elements with the same IP, just check the first element
        let class_rdns = ip_to_rdns_classname(value);
        let found_items = $('.' + class_rdns).filter(':visible');
        if (found_items!=undefined && found_items!=null && found_items.length>0)
        {
            if (ip_batch.length >= batch_size) {
                rdns_batch_lookup(ip_batch);
                ip_batch = [value];
                items_sent++;
            }
            else {
                ip_batch.push(value);
                items_sent++;
            }
        }
    });
    
    //-----final lookup, if any-----
    if (ip_batch.length > 0) {
        rdns_batch_lookup(ip_batch);
    }

    //-----reset the button value when all downloads are done-----
    rdns_batch_timer = setInterval(rdns_enable_button, 200, items_sent);
}

//--------------------------------------------------------------------------------

