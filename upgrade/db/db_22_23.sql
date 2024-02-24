-- DB upgrade from zzz_system version 22 to 23
-- Changes: added tlds table

-- start a transaction
BEGIN TRANSACTION;

-- list of TLDs
create table if not exists tlds(
    tld text not null,
    blocked boolean not null
);
create unique index if not exists tld_idx on tlds(tld);
create index if not exists blocked_tld_idx on tlds(blocked);

-- store country codes in log tables
alter table ip_log_daily add column country_code text;
create index if not exists ip_log_daily_country_code_idx on ip_log_daily(country_code);

alter table ip_log_summary add column country_code text;
create index if not exists ip_log_summary_country_code_idx on ip_log_summary(country_code);

alter table zzz_system add column webserver_domain text;

-- update the system version number
update zzz_system set version=23, last_updated=datetime('now');

-- commit the transaction
COMMIT;
