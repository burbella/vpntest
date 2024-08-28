-- DB setup for Zzz system

PRAGMA foreign_keys=off;

drop table if exists countries;
drop table if exists icap_settings;
drop table if exists ip_log_summary;
drop table if exists ip_log_daily;
drop table if exists ipwhois_cache;
drop table if exists known_org;
drop table if exists known_org_ip;
drop table if exists known_org_domain;
drop table if exists service_request;
drop table if exists settings;
drop table if exists squid_log;
drop table if exists tlds;
drop table if exists update_file;
drop table if exists whois_cache;
drop table if exists work_available;
drop table if exists zzz_list;
drop table if exists zzz_list_entries;
drop table if exists zzz_system;

PRAGMA foreign_keys=on;

-- Create tables and indexes

-- list of countries
create table if not exists countries(
    country_code text not null,
    country text not null,
    blocked boolean not null
);
create unique index if not exists country_code_idx on countries(country_code);
create index if not exists country_idx on countries(country);
create index if not exists blocked_idx on countries(blocked);

-- list of TLDs
create table if not exists tlds(
    tld text not null,
    blocked boolean not null
);
create unique index if not exists tld_idx on tlds(tld);
create index if not exists blocked_tld_idx on tlds(blocked);

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

-- count IP's over time
-- this is a summary table of all entries in ip_log_daily
-- a cron will update it daily
-- last_updated is the unprocessed text string from the ip log file with high-resolution datetime
create table ip_log_summary(
    ip text not null,
    country_code text,
    num_accepted integer not null,
    num_blocked integer not null,
    is_ipv4 boolean not null,
    is_cidr boolean not null,
    is_private boolean not null,
    last_updated text not null
);
create unique index if not exists ip_log_summary_ip_idx on ip_log_summary(ip);
create index if not exists ip_log_summary_country_code_idx on ip_log_summary(country_code);
create index if not exists ip_log_summary_updated_idx on ip_log_summary(last_updated);

-- count IP's by day
-- last_updated is the unprocessed text string from the ip log file with high-resolution datetime
-- log_date is year/month/day in SQLite datetime format
-- a cron will auto-remove old data
create table ip_log_daily(
    ip text not null,
    country_code text,
    num_accepted integer not null,
    num_blocked integer not null,
    is_ipv4 boolean not null,
    is_cidr boolean not null,
    is_private boolean not null,
    log_date integer not null,
    last_updated text not null
);
create index if not exists ip_log_daily_ip_idx on ip_log_daily(ip);
create index if not exists ip_log_daily_country_code_idx on ip_log_daily(country_code);
create index if not exists ip_log_daily_log_date_idx on ip_log_daily(log_date);
create index if not exists ip_log_daily_updated_idx on ip_log_daily(last_updated);
create unique index if not exists ip_log_daily_two_col_idx ON ip_log_daily (ip, log_date);


-- squid log view
-- host is not always available
-- domain is extracted from host
-- reverse_dns may not be available, or may not match host
-- time_elapsed is in milliseconds
-- log_start_date + time_elapsed = log_date
-- text type is required for millisecond resolution on datetimes
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


-- main daemon table
create table if not exists service_request(
    id integer primary key,
    req_date integer not null,
    service_name text not null,
    action text not null,
    status text not null,
    details text,
    status_msg text,
    start_date integer,
    wait_time integer,
    end_date integer,
    work_time integer
);
create index if not exists req_date_idx on service_request(req_date);
create index if not exists service_name_idx on service_request(service_name);
create index if not exists status_idx on service_request(status);
create index if not exists action_idx on service_request(action);


-- no indexes because only one table row ever exists
create table work_available(
    check_requests_table boolean not null
);


-- no indexes because only one table row ever exists
-- JSON data fields: json, ip_log_raw_data_view, ip_auto_block, icap
create table settings(
    json text not null,
    squid_nobumpsites text,
    squid_hide_domains text,
    hide_ips text,
    allow_ips text,
    ip_log_raw_data_view text,
    ip_auto_block text,
    icap text,
    last_updated integer not null,
    raw_data_view_last_updated integer
);


create table update_file(
    id integer primary key,
    service_request_id integer not null,
    file_data text not null,
    src_filepath text,
    FOREIGN KEY(service_request_id) REFERENCES service_request(id)
);
create index if not exists update_file_idx on update_file(service_request_id);


-- cache whois domain lookups
create table whois_cache(
    domain text not null,
    json text not null,
    zzz_last_updated integer not null,
    registrar text,
    org text,
    country_code text,
    creation_date integer,
    expiration_date integer,
    updated_date integer,
    raw_whois text
);
create unique index if not exists domain_idx on whois_cache(domain);
create index if not exists zzz_last_updated_idx on whois_cache(zzz_last_updated);


-- cache whois IP/CIDR lookups
create table ipwhois_cache(
    ip text not null,
    json text not null,
    zzz_last_updated integer not null,
    
    asn text not null,
    asn_cidr text not null,
    asn_country_code text,
    asn_date text,
    asn_date_int integer,
    asn_description text not null,
    
    network_cidr text not null,
    network_country_code text,
    ip_version text not null,
    
    org text,
    
    raw_whois text
);
create unique index if not exists ipwhois_ip_idx on ipwhois_cache(ip);
create index if not exists zzz_last_updated_ip_idx on ipwhois_cache(zzz_last_updated);

-- store DNS/IP lists from different sources separately
-- built-in lists: zzz-dns-deny, zzz-dns-allow, zzz-ip-deny, zzz-ip-allow
--   "allow" entries prevent an item from the "deny" list from ending up in the zzz_list_entries table
-- list type: dns-deny, dns-allow, ip-deny, ip-allow, both-deny, both-allow
--   (mixed lists get auto-split into 2 lists)
-- list_data_source: url, entries, combined (for lists that are assembled from other lists)
-- rejected entries result from post-download validity checks
-- list_length does not include rejected entries
-- keep the previous successful download in case of failures
create table zzz_list(
    id integer primary key,
    list_name text not null,
    list_type text not null,
    list_data_source text not null,
    allow_delete boolean not null,
    allow_edit boolean not null,
    --auto_generated boolean not null,
    builtin boolean not null,
    always_active boolean not null,
    is_active boolean not null,
    auto_update boolean not null,
    list_url text,
    list_length integer not null,
    zzz_last_updated integer not null,
    download_status text,
    last_valid_date_updated integer,
    -- download_data --> accepted_data, rejected_data
    download_data text,
    accepted_entries text,
    rejected_entries text
);
-- allows auto-generated dns/ip lists from a given "both" list
create unique index if not exists zzz_list_name_type_idx on zzz_list(list_name, list_type);
create index if not exists zzz_list_name_idx on zzz_list(list_name);
create index if not exists zzz_list_is_active_idx on zzz_list(is_active);
create index if not exists zzz_list_auto_update_idx on zzz_list(auto_update);
create index if not exists zzz_list_last_updated_idx on zzz_list(zzz_last_updated);

-- individual DNS/IP list entries for blocking, minus items on the allowed lists
-- entries should be auto-updated immediately after download
create table zzz_list_entries(
    id integer primary key,
    zzz_list_id integer not null,
    entry_data text not null,
    notes text,
    last_updated integer,
    FOREIGN KEY(zzz_list_id) REFERENCES zzz_list(id)
);
create index if not exists zzz_list_entries_list_id_idx on zzz_list_entries(zzz_list_id);
create index if not exists zzz_list_entries_data_idx on zzz_list_entries(entry_data);
create index if not exists zzz_list_entries_last_updated_idx on zzz_list_entries(last_updated);
-- prevent duplicate entries within a list
create unique index if not exists zzz_list_entries_idx on zzz_list_entries(zzz_list_id, entry_data);

-- --------------------------------------------------

-- known orgs - by IP/CIDR or domain
-- populate on install from a data file

-- --------------------------------------------------

-- store all Zzz system info in one row
-- no indexes because only one table row ever exists
-- dev_version is null unless a dev version has been installed for testing
create table zzz_system(
    version integer not null,
    available_version integer,
    dev_version text,
    json text not null,
    ip_log_last_time_parsed text,
    webserver_domain text,
    last_updated integer not null
);


-- Init DB values
insert into settings (json, last_updated) values ('', datetime('now'));
insert into zzz_system (version, available_version, json, ip_log_last_time_parsed, last_updated)
    values (25, 25, '', '2020-01-01T00:00:00.000000', datetime('now'));
insert into work_available (check_requests_table) values (1);

