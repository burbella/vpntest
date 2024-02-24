var unsaved_blocked_country_menu = false;
var unsaved_blocked_tld_menu = false;

//-----load the relevant jQuery code for the page-----
function load_js_settings()
{
    attach_copy_to_clipboard();
    
    //-----highlight already-selected countries-----
    //TODO: make this more efficient
    $("#blocked_country_menu>option").each(function(){
        let blocked_country = $(this).val();
        $("#country_menu>option").each(function(){
            let country = $(this).val();
            if (country == blocked_country)
            {
                $(this).addClass('selected_option');
                return;
            }
        });
    });
    
    //-----highlight already-selected TLDs-----
    //TODO: make this more efficient
    $("#blocked_tld_menu>option").each(function(){
        let blocked_tld = $(this).val();
        $("#tld_menu>option").each(function(){
            let tld = $(this).val();
            if (tld == blocked_tld)
            {
                $(this).addClass('selected_option');
                return;
            }
        });
    });
    
    $('#set_autoplay').change(function() {
        show_unsaved_status('status_set_autoplay');
    });

    $('#set_social').change(function() {
        show_unsaved_status('status_set_social');
    });

    $('#set_telemetry').change(function() {
        show_unsaved_status('status_set_telemetry');
    });
    
    //-----START System Updates-----
    $('#set_check_zzz_update').change(function() {
        show_unsaved_status('status_set_check_zzz_update');
        
        // when unchecking this, uncheck set_auto_install_zzz_update also
        // if this is unchecked and set_auto_install_zzz_update is checked, click set_auto_install_zzz_update
        let zzz_update_checkbox = $('#set_check_zzz_update').is(':checked');
        let auto_install_checkbox = $('#set_auto_install_zzz_update').is(':checked');
        if (auto_install_checkbox && !zzz_update_checkbox) {
            $('#set_auto_install_zzz_update').click();
        }
    });
    $('#set_auto_install_zzz_update').change(function() {
        show_unsaved_status('status_set_auto_install_zzz_update');
        
        // when checking this, check set_check_zzz_update also
        // if this is checked and set_check_zzz_update is unchecked, click set_check_zzz_update
        let zzz_update_checkbox = $('#set_check_zzz_update').is(':checked');
        let auto_install_checkbox = $('#set_auto_install_zzz_update').is(':checked');
        if (auto_install_checkbox && !zzz_update_checkbox) {
            $('#set_check_zzz_update').click();
        }
    });
    //-----END System Updates-----
    
    $('#set_show_dev_tools').change(function() {
        show_unsaved_status('status_set_show_dev_tools');
    });

    $('#set_restart_openvpn_weekly').change(function() {
        show_unsaved_status('status_set_restart_openvpn_weekly');
    });

    $('#set_test_server_dns_block').change(function() {
        show_unsaved_status('status_set_test_server_dns_block');
    });

    $('#set_test_server_squid').change(function() {
        show_unsaved_status('status_set_test_server_squid');
    });

    $('#set_duplicate_domain').change(function() {
        show_unsaved_status('status_set_duplicate_domain');
    });
    
    $('#set_links_by_function').change(function() {
        show_unsaved_status('status_set_links_by_function');
    });
    
    $('#set_icap_condensed').change(function() {
        show_unsaved_status('status_set_icap_condensed');
    });
    
    //-----START block country TLD-----
    // inter-connect 2 checkboxes
    $('#set_block_country_tld').change(function() {
        show_unsaved_status('status_set_block_country_tld');
        
        // when unchecking this, make sure set_block_country_tld_always is uncheck also
        // auto-click set_block_country_tld_always if it needs to be changed
        let tld_checkbox = $('#set_block_country_tld').is(':checked');
        let tld_always_checkbox = $('#set_block_country_tld_always').is(':checked');
        if (tld_always_checkbox && !tld_checkbox) {
            $('#set_block_country_tld_always').click();
        }
    });
    $('#set_block_country_tld_always').change(function() {
        show_unsaved_status('status_set_block_country_tld_always');
        
        // when checking this, make sure set_block_country_tld is checked also
        // auto-click set_block_country_tld if it needs to be changed
        let tld_checkbox = $('#set_block_country_tld').is(':checked');
        let tld_always_checkbox = $('#set_block_country_tld_always').is(':checked');
        if (tld_always_checkbox && !tld_checkbox) {
            $('#set_block_country_tld').click();
        }
    });
    //-----END block country TLD-----
    
    $('#set_block_country_ip_always').change(function() {
        show_unsaved_status('status_set_block_country_ip_always');
    });
    
    $('#set_block_tld_always').change(function() {
        show_unsaved_status('status_set_block_tld_always');
    });
    
    $('#set_dark_mode').change(function() {
        // clear_upload_status();
        
        let dark_mode_checkbox = $('#set_dark_mode').is(':checked');
        if (dark_mode_checkbox) {
            $('#link_colors').attr('href', '/css/colors-dark.css');
        }
        else {
            $('#link_colors').attr('href', '/css/colors.css');
        }
        
        show_unsaved_status('status_set_dark_mode');
    });
    
    $('#allow_ips').change(function() {
        show_unsaved_status('status_allow_ips');
    });
    
    $('#squid_hide_domains').change(function() {
        show_unsaved_status('status_squid_hide_domains');
    });
    
    $('#hide_ips').change(function() {
        show_unsaved_status('status_hide_ips');
    });
    
    $('#squid_nobumpsites').change(function() {
        show_unsaved_status('status_squid_nobumpsites');
    });
    
    //-----show/hide lists-----
    $('#show_hide_autoplay').click(function() {
        show_hide_object('autoplay_list', 'show_hide_autoplay', 'Show List', 'Hide List');
    });
    
    $('#show_hide_social').click(function() {
        show_hide_object('social_list', 'show_hide_social', 'Show List', 'Hide List');
    });
    
    $('#show_hide_telemetry').click(function() {
        show_hide_object('telemetry_list', 'show_hide_telemetry', 'Show List', 'Hide List');
    });
    
    //-----block/unblock all countries-----
    $('#block_all_countries').click(function() {
        block_all_countries();
    });
    
    $('#unblock_all_countries').click(function() {
        unblock_all_countries();
    });
    
    //-----block/unblock all TLDs-----
    $('#block_all_tlds').click(function() {
        block_all_tlds();
    });
    
    $('#block_unicode_tlds').click(function() {
        block_unicode_tlds();
    });
    
    $('#unblock_all_tlds').click(function() {
        unblock_all_tlds();
    });
    
    //-----bundle all the settings into a JSON and send it-----
    $('#save_settings').click(function() {
        do_save_settings();
    });
    $('#save_settings2').click(function() {
        do_save_settings();
    });

    $('#country_scroll').keyup(function(event) {
        do_country_scroll(event);
    });

    $('#country_menu').click(function() {
        clear_upload_status();
        block_one_country($("#country_menu>option:selected"));
    });
    
    $('#blocked_country_menu').click(function() {
        // clear_upload_status();
        
        unblock_one_country($('#blocked_country_menu>option:selected'));
        
        // show unsaved settings warning
        unsaved_blocked_country_menu = true;
        show_unsaved_status('status_blocked_country_menu');
    });
    
    $('#tld_menu').click(function() {
        clear_upload_status();
        block_one_tld($("#tld_menu>option:selected"));
    });
    
    $('#blocked_tld_menu').click(function() {
        // clear_upload_status();
        
        unblock_one_tld($('#blocked_tld_menu>option:selected'));
        
        // show unsaved settings warning
        unsaved_blocked_tld_menu = true;
        show_unsaved_status('status_blocked_tld_menu');
    });
    
    console.log("Settings Ready.");
    
    return true;
}

//--------------------------------------------------------------------------------

//-----assemble the settings into a big JSON-----
function do_save_settings() {
    clear_upload_status();
    show_saving_in_progress();
    upload_settings();
}

//--------------------------------------------------------------------------------

// show unsaved status in 3 places:
//   top Save button
//   bottom Save button
//   tag for the given status_id
function show_unsaved_status(status_id='') {
    let unsaved_html = '<span class="update_fail">Not Saved</span>';
    $('#status_save_settings').html(unsaved_html);
    $('#status_save_settings2').html(unsaved_html);
    if (status_id=='') { return; }
    $('#'+status_id).html(unsaved_html);
}

//--------------------------------------------------------------------------------

//-----assemble the settings into a big JSON-----
function make_json_settings() {
    let settings_object = {};
    settings_object.autoplay = String($('#set_autoplay').is(':checked'));
    settings_object.social = String($('#set_social').is(':checked'));
    settings_object.telemetry = String($('#set_telemetry').is(':checked'));
    settings_object.duplicate_domain = String($('#set_duplicate_domain').is(':checked'));
    settings_object.links_by_function = String($('#set_links_by_function').is(':checked'));
    settings_object.icap_condensed = String($('#set_icap_condensed').is(':checked'));
    settings_object.block_country_tld = String($('#set_block_country_tld').is(':checked'));
    settings_object.block_country_tld_always = String($('#set_block_country_tld_always').is(':checked'));
    settings_object.block_country_ip_always = String($('#set_block_country_ip_always').is(':checked'));
    settings_object.block_tld_always = String($('#set_block_tld_always').is(':checked'));
    settings_object.dark_mode = String($('#set_dark_mode').is(':checked'));
    
    //-----system updates-----
    settings_object.check_zzz_update = String($('#set_check_zzz_update').is(':checked'));
    settings_object.auto_install_zzz_update = String($('#set_auto_install_zzz_update').is(':checked'));
    settings_object.show_dev_tools = String($('#set_show_dev_tools').is(':checked'));
    settings_object.restart_openvpn_weekly = String($('#set_restart_openvpn_weekly').is(':checked'));

    settings_object.test_server_dns_block = String($('#set_test_server_dns_block').is(':checked'));
    settings_object.test_server_squid = String($('#set_test_server_squid').is(':checked'));

    settings_object.blocked_country = $("#blocked_country_menu>option").map(function() { return $(this).val(); }).get();
    settings_object.blocked_tld = $("#blocked_tld_menu>option").map(function() { return $(this).val(); }).get();
    
    settings_object.allow_ips = $('#allow_ips').val();
    settings_object.squid_hide_domains = $('#squid_hide_domains').val();
    settings_object.hide_ips = $('#hide_ips').val();
    settings_object.squid_nobumpsites = $('#squid_nobumpsites').val();
    
    let settings_data = JSON.stringify(settings_object);
    
    return settings_data;
}

//--------------------------------------------------------------------------------

//-----upload all settings in one big JSON-----
function upload_settings() {
    let settings_data = make_json_settings();
    
    let postdata = 'json=' + encodeURIComponent(settings_data);
    let success_html = '<span class="update_success">Settings Saved</span>';
    let error_html = '<span class="text_red">ERROR</span>';

    $.post({
        'url': url_settings,
        'data': postdata,
        'success': null,
        'dataType': 'json'
    })
    .done(function(data){
        console.log('POST done');
        //-----check the return value-----
        if (data.status=='success') {
            //-----success - update the HTML page-----
            clear_settings_status();
            $('#status_save_settings').html(success_html);
            $('#status_save_settings2').html(success_html);
            unsaved_blocked_country_menu = false;
            unsaved_blocked_tld_menu = false;
        } else {
            console.log(data.error_msg);
            error_html = `<span class="text_red">${data.error_msg}</span>`;
            $('#status_save_settings').html(error_html);
            $('#status_save_settings2').html(error_html);
        }
    })
    .fail(function(){
        console.log('POST fail');
        $('#status_save_settings').html(error_html);
        $('#status_save_settings2').html(error_html);
    })
    .always(function(){
    });
}

//--------------------------------------------------------------------------------

//-----clears all status messages-----
function clear_settings_status() {
    $('#status_set_autoplay').html('');
    $('#status_set_social').html('');
    $('#status_set_telemetry').html('');
    $('#status_set_duplicate_domain').html('');
    $('#status_set_links_by_function').html('');
    $('#status_set_icap_condensed').html('');
    $('#status_set_block_country_tld').html('');
    $('#status_set_block_country_tld_always').html('');
    $('#status_set_block_country_ip_always').html('');
    $('#status_set_block_tld_always').html('');
    $('#status_set_dark_mode').html('');
    
    //-----system updates-----
    $('#status_set_check_zzz_update').html('');
    $('#status_set_auto_install_zzz_update').html('');
    $('#status_set_show_dev_tools').html('');
    $('#status_set_restart_openvpn_weekly').html('');

    $('#status_set_test_server_dns_block').html('');
    $('#status_set_test_server_squid').html('');

    $('#status_country_menu').html('');
    $('#status_blocked_country_menu').html('');
    $('#status_blocked_tld_menu').html('');
    
    $('#status_allow_ips').html('');
    $('#status_squid_hide_domains').html('');
    $('#status_hide_ips').html('');
    $('#status_squid_nobumpsites').html('');
}

function clear_upload_status() {
    $('#status_save_settings').html('');
    $('#status_save_settings2').html('');
}

function show_saving_in_progress() {
    let saving_html = '<span>Saving Settings...</span>';
    $('#status_save_settings').html(saving_html);
    $('#status_save_settings2').html(saving_html);
}

//--------------------------------------------------------------------------------

// when entering text in the country_scroll box, scroll the country menu to that country
function do_country_scroll(event) {
    let country_scroll = $('#country_scroll').val();
    if (country_scroll == '') { return; }

    // remove characters that are not letters, spaces, apostrophes, commas, periods, or dashes
    country_scroll = country_scroll.replace(/[^a-zA-Z\s',.-]/g, '').toLowerCase();

    // find the country option in the menu that starts with the scroll text
    let country_obj_found = $('#country_menu').find('option').filter(function() {
        return $(this).text().toLowerCase().includes(country_scroll);
    })
    if (country_obj_found.length > 0) {
        let country_name = country_obj_found[0];

        // scroll the country_menu option to the country_name
        $('#country_menu > option').each(function() {
            if ($(this).text() == country_name.text) {
                this.scrollIntoView({behavior: "instant", block: "nearest", inline: "nearest"});
                return false;
            }
        });
    }
}

//--------------------------------------------------------------------------------

function block_one_country(option_obj, skip_status_update=false) {
    //-----no action if Protected-----
    if (option_obj.hasClass('protected_option')) { return; }
    
    // check if already in the blocked menu --> do not duplicate
    let selected_country = option_obj.val();
    console.log('block country: ' + selected_country);
    let already_blocked = false;
    $("#blocked_country_menu>option").each(function(){
        if ($(this).val() == selected_country)
        {
            already_blocked = true;
        }
    });
    
    let country_name = option_obj.text();
    if (!already_blocked)
    {
        let option = '<option value="' + selected_country + '">' + country_name + '</option>';
        $('#blocked_country_menu').append(option);
        option_obj.addClass('selected_option');

        // show unsaved settings warning
        unsaved_blocked_country_menu = true;
    }
    
    if (unsaved_blocked_country_menu && !skip_status_update) {
        show_unsaved_status('status_blocked_country_menu');
        print_html_delay_clear('action_blocked_country_menu', `blocked ${country_name}`, html_clear='&nbsp;');
    }
}

//--------------------------------------------------------------------------------

function block_all_countries() {
    clear_upload_status();
    
    $('#country_menu>option').each(function() {
        $(this).prop("selected");
        block_one_country($(this), skip_status_update=true);
    });
    show_unsaved_status('status_blocked_country_menu');
    print_html_delay_clear('action_blocked_country_menu', 'blocked all countries', html_clear='&nbsp;');
}

//--------------------------------------------------------------------------------

function unblock_one_country(option_obj) {
    // remove country from menu
    let country_code = option_obj.val();
    console.log('unblock country: ' + country_code);
    $('#country_menu>option[value="' + country_code + '"]').removeClass('selected_option');
    option_obj.remove();
}

//--------------------------------------------------------------------------------

function unblock_all_countries() {
    clear_upload_status();
    
    // remove all countries from menu
    $('#blocked_country_menu>option').each(function() {
        unblock_one_country($(this));
    });
    
    // show unsaved settings warning
    unsaved_blocked_country_menu = true;
    show_unsaved_status('status_blocked_country_menu');
}

//--------------------------------------------------------------------------------

//TODO: generalize these functions since the country and TLD functions do the same thing with different objects/variables/text
// TLD menu processing
function block_one_tld(option_obj, skip_status_update=false) {
    //-----no action if Protected-----
    if (option_obj.hasClass('protected_option')) { return; }
    
    // check if already in the blocked menu --> do not duplicate
    let selected_tld = option_obj.val();
    console.log('block TLD: ' + selected_tld);
    let already_blocked = false;
    $("#blocked_tld_menu>option").each(function(){
        if ($(this).val() == selected_tld)
        {
            already_blocked = true;
        }
    });
    
    if (!already_blocked)
    {
        let option = '<option value="' + selected_tld + '">' + selected_tld + '</option>';
        $('#blocked_tld_menu').append(option);
        option_obj.addClass('selected_option');
        
        // show unsaved settings warning
        unsaved_blocked_tld_menu = true;
    }
    
    if (unsaved_blocked_tld_menu && !skip_status_update) {
        show_unsaved_status('status_blocked_tld_menu');
    }
}

function block_all_tlds() {
    clear_upload_status();
    
    $('#tld_menu').hide();
    $('#blocked_tld_menu').hide();
    $('#tld_menu>option').each(function() {
        $(this).prop("selected");
        block_one_tld($(this), skip_status_update=true);
    });
    $('#tld_menu').show();
    $('#blocked_tld_menu').show();
    show_unsaved_status('status_blocked_tld_menu');
}

// unicode TLD's start with "xn--"
function block_unicode_tlds() {
    clear_upload_status();
    
    $('#tld_menu').hide();
    $('#blocked_tld_menu').hide();
    $('#tld_menu>option').each(function() {
        let tld = $(this).val();
        if (/^XN\-\-/.test(tld))
        {
            $(this).prop("selected");
            block_one_tld($(this));
        }
    });
    $('#tld_menu').show();
    $('#blocked_tld_menu').show();
}

function unblock_one_tld(option_obj) {
    // remove TLD from menu
    let tld = option_obj.val();
    console.log('unblock TLD: ' + tld);
    $('#tld_menu>option[value="' + tld + '"]').removeClass('selected_option');
    option_obj.remove();
}

function unblock_all_tlds() {
    clear_upload_status();
    
    // remove all TLDs from menu
    $('#tld_menu').hide();
    $('#blocked_tld_menu').hide();
    $('#blocked_tld_menu>option').each(function() {
        unblock_one_tld($(this));
    });
    $('#tld_menu').show();
    $('#blocked_tld_menu').show();
    
    // show unsaved settings warning
    unsaved_blocked_tld_menu = true;
    show_unsaved_status('status_blocked_tld_menu');
}

//--------------------------------------------------------------------------------

