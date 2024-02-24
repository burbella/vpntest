let allowed_paths = {
    '/z/edit_dns': 1,
    '/z/edit_ip': 1,
};

function do_redirect(internal_path) {
    // prevent redirects to other servers
    if (internal_path.startsWith('/z/')) {
        if (allowed_paths[internal_path]) {
            window.location.replace(zzz_https_url + internal_path);
        } else {
            $('#redirect_error').text('ERROR: internal path not on the allowed_paths list');
        }
    } else {
        $('#redirect_error').text('ERROR: not an internal path redirect');
    }
}
