var url_test = zzz_https_url + '/z/test';

function load_js_zzz_test()
{

}

function show_event_handlers(dom_object) {
    let bound_events = $._data(dom_object[0], 'events');
    console.log('bound_events:');
    if (bound_events === undefined) {
        console.log('no events found');
        return;
    }

    $.each(bound_events, function(index, bound_event) {
        $.each(bound_event, function(index, event_handler) {
            console.log(event_handler);
        });
    });
}

/* JSON minimum return data expected:
    data = {
        'status': '',
        'error_msg': '',
    }
*/
function do_post() {
    console.log('do_post()');
    
    let postdata = 'action=test';
    let status_field = $('#status_field');
    let success_html = '<span class="update_success">Success</span>';
    let error_html = '<span class="text_red">ERROR</span>';

    status_field.html('');

    $.post({
        'url': url_test,
        'data': postdata,
        'success': null,
        'dataType': 'json' // html, json, script, text, xml
    })
    .done(function(data){
        console.log('POST done');
        //-----check the return value-----
        if (data.status=='success') {
            //-----success - update the HTML page-----


            //-----display status-----
            status_field.html(success_html);
        } else {
            console.log(data.error_msg);
            error_html = `<span class="text_red">${data.error_msg}</span>`;
            status_field.html(error_html);
        }
    })
    .fail(function(){
        console.log('POST fail');
        status_field.html(error_html);
    })
    .always(function(){
        console.log('POST end');
    });
}

// short version
function do_post_short() {
    let postdata = `action=test`;
    let status_field = $('#status_field');
    let error_html = '<span class="text_red">ERROR</span>';

    $.post({
        'url': url_test,
        'data': postdata,
        'success': null,
        'dataType': 'json' // html, json, script, text, xml
    })
    .done(function(data){
        status_field.html(data);
    })
    .fail(function(){
        status_field.html(error_html);
    });
}

// shorter version
function do_post_shorter() {
    $.post(url_test, postdata)
    .done(function(data){
        $('#status_field').html(data);
    })
    .fail(function(){
        $('#status_field').html('ERROR');
    });
}
