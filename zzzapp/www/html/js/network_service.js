//-----load the relevant jQuery code for the page-----
function load_js_network_service(show_header=true, set_domain='', action='')
{
    //-----attach click triggers to clickable page elements-----
    $('#lookup_whois').click(function(){
        // function in services.js
        do_lookup($('#domain').val(), 'whois');
    });
    
    $('#do_nslookup').click(function(){
        do_lookup($('#domain').val(), 'nslookup');
    });
    
    $('#do_reverse_dns').click(function(){
        do_lookup($('#domain').val(), 'reverse_dns');
    });
    
    $('#do_external_whois').click(function(){
        let domain = $('#domain').val();
        if (domain == "") { alert("Enter a domain in the textbox"); }
        else { external_whois(domain); }
    });

    $('#do_search_ipinfo').click(function(){
        let domain = $('#domain').val();
        if (domain == "") { alert("Enter a domain in the textbox"); }
        else { search_ipinfo(domain); }
    });

    $('#do_search_ip_rep').click(function(){
        let domain = $('#domain').val();
        if (domain == "") { alert("Enter a domain in the textbox"); }
        else { search_ip_rep(domain); }
    });

    //-----press enter to submit a search-----
    $('#domain').keydown(function(event){
        if (event.which == 13)
        {
            $('#lookup_whois').click();
            event.preventDefault();
            return false;
        }
    });
    
    //-----from services.js-----
    apply_onclick_events();

    should_show_header(show_header);
    should_set_domain(set_domain, action);

    console.log("load_js_network_service Ready.");
    
    return true;
}

//--------------------------------------------------------------------------------

function show_loading_whois() {
    $('#network_service_output').html('<span class="warning_text">Loading...</span>');
}

//-----load data based on whether the app wants it-----
function should_show_header(show_header=true) {
    if (show_header) {
        $('#network_service_header').removeClass('hide_item');
    }
}

function should_set_domain(set_domain='', action='') {
    if (set_domain != '') {
        $('#domain').val(set_domain);
        if (action == 'whois') { $('#lookup_whois').click(); return; }
        if (action == 'nslookup') { $('#do_nslookup').click(); return; }
    }
}

//-----request lookup, print the output in the html-----
function do_lookup(host, lookup_path)
{
    // lookup_path = whois, nslookup
    let postdata = `action=${lookup_path}`;
    if (lookup_path == 'reverse_dns') { postdata += `&ip=${host}`; }
    else { postdata += `&host=${host}`; }
    
    setTimeout(show_loading_whois, 1);
    
    //-----process nslookup-----
    if (lookup_path == 'nslookup')
    {
        if ($('#nslookup_dns_blocked').is(':checked')) { postdata += '&nslookup_dns_blocked=1'; }

        $.post({
            'url': url_network_service,
            'data': postdata,
            'success': null,
            'dataType': 'json' // html, json, script, text, xml
        })
        .done(function(data){
            let result = '<p><b>nslookup results:</b></p>';
            if (data.status=='success') {
                result += '<pre>' + data.details + '</pre>';
            } else {
                result += '<p><b>ERROR:</b></p><pre>' + data.details + '</pre>';
            }
            $('#network_service_output').html(result);
        })
        .fail(function(){
            $('#network_service_output').html('ERROR posting nslookup request');
        })
        .always(function(){
        });

        return;
    }
    
    //-----process whois lookup-----
    if ($('#whois_server_only').is(':checked')) { postdata += '&whois_server_only=1'; }

    $.post({
        'url': url_network_service,
        'data': postdata,
        'success': null,
        'dataType': 'json' // html, json, script, text, xml
    })
    .done(function(data){
        let display_html = '';
        if (lookup_path == 'reverse_dns') {
            // parsed_data = JSON.parse(data);
            display_html = `Reverse DNS for ${host}: ${data[host]}`;
        } else {
            display_html = data['html_data'];
        }

        $('#network_service_output').html(display_html);
        //-----from services.js-----
        apply_onclick_events();
    })
    .fail(function(){
        $('#network_service_output').html(`ERROR posting ${lookup_path} request`);
    })
    .always(function(){
    });
}

//--------------------------------------------------------------------------------

function whois_delete(row_id, host)
{
    let postdata = `action=whois_cache&do_delete=1&host=${host}`;

    $.post({
        'url': url_network_service,
        'data': postdata,
        // 'success': null,
        // 'dataType': 'json' // html, json, script, text, xml
    })
    .done(function(data){
        $(`#${row_id}`).remove();
    })
    .fail(function(){
        //TODO: indicate an error
        alert('ERROR deleting cache entry');
    })
    .always(function(){
    });
}

//--------------------------------------------------------------------------------

function ipwhois_delete(row_id, ip)
{
    let postdata = `action=ipwhois_cache&do_delete=1&ip=${ip}`;

    $.post({
        'url': url_network_service,
        'data': postdata,
        // 'success': null,
        // 'dataType': 'json' // html, json, script, text, xml
    })
    .done(function(data){
        $(`#${row_id}`).remove();
    })
    .fail(function(){
        //TODO: indicate an error
        alert('ERROR deleting cache entry');
    })
    .always(function(){
    });
}

//--------------------------------------------------------------------------------

