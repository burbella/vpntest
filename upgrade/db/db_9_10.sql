-- DB upgrade from zzz_system version 9 to 10
-- Changes: incremented version number
--          settings table has a new column: hide_ips
--          added tables: ip_log_summary, ip_log_daily

-- start a transaction
BEGIN TRANSACTION;

alter table settings add column hide_ips text;

-- count IP's over time
-- this is a summary table of all entries in ip_log_daily
-- a cron will update it daily
-- last_updated is the unprocessed text string from the ip log file with high-resolution datetime
create table ip_log_summary(
    ip text not null,
    num_accepted integer not null,
    num_blocked integer not null,
    is_ipv4 boolean not null,
    is_cidr boolean not null,
    is_private boolean not null,
    last_updated text not null
);
create index if not exists ip_log_summary_ip_idx on ip_log_summary(ip);
create index if not exists ip_log_summary_updated_idx on ip_log_summary(last_updated);

-- count IP's by day
-- last_updated is the unprocessed text string from the ip log file with high-resolution datetime
-- log_date is year/month/day in SQLite datetime format
-- a cron will auto-remove old data
create table ip_log_daily(
    ip text not null,
    num_accepted integer not null,
    num_blocked integer not null,
    is_ipv4 boolean not null,
    is_cidr boolean not null,
    is_private boolean not null,
    log_date integer not null,
    last_updated text not null
);
create index if not exists ip_log_daily_ip_idx on ip_log_daily(ip);
create index if not exists ip_log_daily_log_date_idx on ip_log_daily(log_date);
create index if not exists ip_log_daily_updated_idx on ip_log_daily(last_updated);

-- update the system version number
update zzz_system set version=10, last_updated=datetime('now');

-- commit the transaction
COMMIT;
