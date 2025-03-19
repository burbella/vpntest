//-----code here is used by AI forms on various pages-----
function load_js_ai()
{
    $('#ip_commit_updates').click(function() {
        upload_ip_denylist();
    });

    //-----AI buttons-----
    // ai_submit, ai_reset_estimate, ai_reset_query, ai_get_estimate
    $('#ai_submit').click(function() {
        ai_submit();
    });

    $('#ai_reset_query').click(function() {
        ai_reset_query();
    });

    $('#ai_get_estimate').click(function() {
        ai_get_estimate();
    });

    $('#ai_reset_estimate').click(function() {
        ai_reset_estimate_actual();
    });

    console.log("AI Ready.");

    return true;
}

//--------------------------------------------------------------------------------

// ai_reset_estimate_actual: clear the data from the estimate table
function ai_reset_estimate_actual()
{
    $('#ai_estimate_prompt_tokens').html('');
    $('#ai_estimate_completion_tokens').html('');
    $('#ai_estimate_prompt_cost').html('');
    $('#ai_estimate_completion_cost').html('');
    $('#ai_estimate_total_cost').html('');

    $('#ai_actual_prompt_tokens').html('');
    $('#ai_actual_completion_tokens').html('');
    $('#ai_actual_prompt_cost').html('');
    $('#ai_actual_completion_cost').html('');
    $('#ai_actual_total_cost').html('');

    $('#ai_estimate_runtime').html('');
}

//--------------------------------------------------------------------------------

// ai_reset_query: clear the html from id=ai_instructions
function ai_reset_query()
{
    $('#ai_instructions').val('');
    $('#ai_response').val('');
}

//--------------------------------------------------------------------------------

function swap_submit_button() {
    // show/hide: ai_show_submit, ai_show_submitting
    $('#ai_submit').toggle();
    $('#ai_show_submitting').toggle();

    // don't want users clicking other AI buttons while a query is running
    $('#ai_get_estimate').toggle();
    $('#ai_reset_query').toggle();
    $('#ai_reset_estimate').toggle();
}

function swap_estimate_button() {
    // show/hide: ai_get_estimate, ai_show_getting_estimate
    $('#ai_get_estimate').toggle();
    $('#ai_show_getting_estimate').toggle();
}

//--------------------------------------------------------------------------------

function insert_estimated_costs_into_dom(data)
{
    // vars in data.estimated_costs: prompt_tokens, completion_tokens, prompt_cost, completion_cost, total_cost
    prompt_tokens = data.estimated_costs['prompt_tokens']
    completion_tokens = data.estimated_costs['completion_tokens']
    prompt_cost = data.estimated_costs['prompt_cost']
    completion_cost = data.estimated_costs['completion_cost']
    total_cost = data.estimated_costs['total_cost']
    $('#ai_estimate_prompt_tokens').html(prompt_tokens);
    $('#ai_estimate_completion_tokens').html(completion_tokens);
    $('#ai_estimate_prompt_cost').html(prompt_cost);
    $('#ai_estimate_completion_cost').html(completion_cost);
    $('#ai_estimate_total_cost').html(total_cost);
}

//--------------------------------------------------------------------------------

// vars in data.actual_costs: prompt_tokens, completion_tokens, prompt_cost, completion_cost, total_cost
function insert_actual_costs_into_dom(data) {
    prompt_tokens = data.actual_costs['prompt_tokens']
    completion_tokens = data.actual_costs['completion_tokens']
    prompt_cost = data.actual_costs['prompt_cost']
    completion_cost = data.actual_costs['completion_cost']
    total_cost = data.actual_costs['total_cost']
    $('#ai_actual_prompt_tokens').html(prompt_tokens);
    $('#ai_actual_completion_tokens').html(completion_tokens);
    $('#ai_actual_prompt_cost').html(prompt_cost);
    $('#ai_actual_completion_cost').html(completion_cost);
    $('#ai_actual_total_cost').html(total_cost);
}

function clear_ai_response() {
    $('#ai_response').val('');
}

//--------------------------------------------------------------------------------

// ai_submit: submit the AI form using AJAX, similar to the way get_logfile_menu works
// data fields: action=ai_submit, ai_instructions
function ai_submit()
{
    // hide the submit button
    setTimeout(swap_submit_button, 1);
    setTimeout(clear_ai_response, 1);
    setTimeout(ai_reset_estimate_actual, 1);

    // get data from textarea
    let ai_instructions = $('#ai_instructions').val();

    let postdata = `action=ai_submit&ai_instructions=` + encodeURIComponent(ai_instructions);
    $.post({
        'url': url_ai,
        'data': postdata,
        'success': null,
        'dataType': 'json' // html, json, script, text, xml
    })
    .done(function(data){
        if (data.status == 'error') {
            err_msg = `ERROR: ${data.error_msg}`;
            console.log(err_msg);
            $('#ai_response').val(err_msg);
            return;
        }

        //-----replace the contents of the cost_estimate-----
        $('#ai_response').val(data.ai_response_text);
        $('#ai_estimate_runtime').html(data.runtime);
        insert_estimated_costs_into_dom(data);
        insert_actual_costs_into_dom(data);

        console.log('AI prompt submitted');
    })
    .fail(function(){
        // status_field.html('ERROR');
    })
    .always(function(){
        // $('#view_log').show();
        // $('#loading_msg').hide();

        // show the submit button
        swap_submit_button();
    });
}

//--------------------------------------------------------------------------------

// ai_get_estimate: submit the AI form using AJAX, similar to the way get_logfile_menu works
// data fields: action=ai_get_estimate, ai_instructions
function ai_get_estimate()
{
    // hide the Get button
    setTimeout(swap_estimate_button, 1);
    setTimeout(ai_reset_estimate_actual, 1);

    // get data from textarea
    let ai_instructions = $('#ai_instructions').val();

    let postdata = `action=ai_get_estimate&ai_instructions=` + encodeURIComponent(ai_instructions);
    $.post({
        'url': url_ai,
        'data': postdata,
        'success': null,
        'dataType': 'json' // html, json, script, text, xml
    })
    .done(function(data){
        if (data.status == 'error') {
            console.log(`ERROR: ${data.error_msg}`);
            return;
        }

        //-----replace the contents of the cost_estimate-----
        // vars in data.estimated_costs: prompt_tokens, completion_tokens, prompt_cost, completion_cost, total_cost
        insert_estimated_costs_into_dom(data);

        console.log('AI cost estimate requested');
    })
    .fail(function(){
        // status_field.html('ERROR');
    })
    .always(function(){
        // $('#view_log').show();
        // $('#loading_msg').hide();

        // show the Get button
        swap_estimate_button();
    });
}
