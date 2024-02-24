console.log("edit_dns.js - START");

function load_js_edit_dns() {
    $('#submit_added_domains').click(function() {
        $('#status_submit_added_domains').html('<p class="text_green">Uploading...</p>');
        
        upload_list_to_server('add_domains', $('#status_submit_added_domains'), encodeURIComponent($('#domains_to_add').val()));
    });
    
    $('#submit_new_list').click(function() {
        $('#status_submit_new_list').html('<p class="text_green">Uploading...</p>');
        
        upload_list_to_server('replace_domains', $('#status_submit_new_list'), encodeURIComponent($('#replace_domain_list').val()));
    });
    
    $('#copy_to_replace').click(function() {
        $('#replace_domain_list').val($('#show_file').val());
    });

    attach_content_collapsed_toggle();
    attach_get_dns_backup_file();
}

//-----upload either a new list or added domains-----
// actions: add_domains, replace_domains
//TODO: make this similar to the code in squid_log.js
function upload_list_to_server(action, status_field, domain_list) {
    let postdata = 'action=' + action + '&domain_list=' + domain_list;
    
    if (domain_list.length==0)
    {
        status_field.html('<p class="text_red">ERROR: empty list</p>');
        return;
    }
    
    // option for silent drop of bad domains
    let handle_invalid_domains = $(":radio[name=handle_invalid_domains]:checked").val();
    postdata += '&handle_invalid_domains=' + handle_invalid_domains;
    
    // empty & hide the rejected list
    $('#rejected_domains_display').hide();
    $('#rejected_domains').val('');

    let success_html = '<span class="update_success">Success</span>';
    let error_html = '<span class="text_red">ERROR</span>';

    $.post({
        'url': url_edit_dns,
        'data': postdata,
        'success': null,
        'dataType': 'json' // html, json, script, text, xml
    })
    .done(function(data){
        if (data.status=='success') {
            success_html = `<p class="text_green">${data.status}</p>`;
            status_field.html(success_html);
        } else {
            error_html = `<span class="text_red">${data.error_msg}</span>`;
            status_field.html(error_html);
        }
        // NOTE: rejected_domains are no longer displayed
        //       the option to report without saving the list was removed
        /*
        let rejected_domains = data.rejected_domains;
        if (rejected_domains!=undefined && rejected_domains!=null && rejected_domains.length>0) {
            //-----only show if the radio button says to show-----
            if (handle_invalid_domains=='report') {
                $('#rejected_domains').val(rejected_domains.join('\n'));
                $('#rejected_domains_display').show();
                status_field.html(`<p class="text_red">${data.status}</p>`);
            } else {
                status_field.html(success_html);
            }
        }
        else {
            status_field.html(success_html);
        }
        */
    })
    .fail(function(){
        status_field.html(error_html);
    })
    .always(function(){
    });
}

function get_dns_backup_file(filename) {
    let postdata = 'action=get_dns_file&filename=' + filename;

    $.post({
        'url': url_edit_dns,
        'data': postdata,
        'success': null,
        'dataType': 'text' // html, json, script, text, xml
    })
    .done(function(data){
        //-----success - update the HTML page-----
        $('#show_file').val(data);
    })
    .fail(function(){
        console.log('ERROR loading file');
    })
    .always(function(){
    });
}

function attach_get_dns_backup_file() {
    $('.get_dns_backup_file').click(function() {
        get_dns_backup_file($(this).attr("data-onclick"));
    });
}

console.log("edit_dns.js - LOADED");
