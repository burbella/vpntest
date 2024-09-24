-- DB upgrade from zzz_system version 24 to 25
-- Changes:
--   added to settings table: ip_log_raw_data_view, raw_data_view_last_updated, iptables_rules, icap
--   added to zzz_list_entries table: notes, last_updated

-- start a transaction
BEGIN TRANSACTION;

-- IP Log Raw Data view settings
alter table settings add column ip_log_raw_data_view text;
alter table settings add column raw_data_view_last_updated integer;
alter table settings add column iptables_rules text;
alter table settings add column iptables_rules_last_updated integer;
alter table settings add column icap text;
alter table settings add column icap_last_updated integer;

-- list entries
alter table zzz_list_entries add column notes text;
alter table zzz_list_entries add column last_updated integer;
create index if not exists zzz_list_entries_last_updated_idx on zzz_list_entries(last_updated);

-- update the system version number
update zzz_system set version=25, last_updated=datetime('now');

-- commit the transaction
COMMIT;
