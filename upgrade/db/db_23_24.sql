-- DB upgrade from zzz_system version 23 to 24
-- Changes: added icap_settings table

-- start a transaction
BEGIN TRANSACTION;

-- ICAP settings
create table if not exists icap_settings(
    id integer primary key,
    compiled_ok boolean not null,
    enabled boolean not null,
    domain_name text,
    regex_json text not null,
    replacement_str text,
    notes text,
    compile_message text
);
create index if not exists icap_settings_domain_idx on icap_settings(domain_name);
create index if not exists icap_settings_enabled_idx on icap_settings(enabled);
create index if not exists icap_settings_compiled_idx on icap_settings(compiled_ok);

-- squid log view
create table squid_log(
    ip text not null,
    log_date text not null,
    time_elapsed int not null,
    log_start_date text not null,
    host text,
    domain text,
    reverse_dns text,
    url_str text,
    country_code text not null,
    client_ip text not null,
    http_code text,
    http_status int,
    xfer_bytes int,
    method text
);
create index if not exists squid_ip_idx on squid_log(ip);
create index if not exists squid_log_date_idx on squid_log(log_date);
create index if not exists squid_log_start_date_idx on squid_log(log_start_date);
create index if not exists squid_host_idx on squid_log(host);

-- update the system version number
update zzz_system set version=24, last_updated=datetime('now');

-- commit the transaction
COMMIT;
