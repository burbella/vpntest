-- DB upgrade from zzz_system version 24 to 25
-- Changes: added ip_log_raw_data_view to settings table

-- start a transaction
BEGIN TRANSACTION;

-- IP Log Raw Data view settings
alter table settings add column ip_log_raw_data_view text;
alter table settings add column raw_data_view_last_updated integer;

-- update the system version number
update zzz_system set version=25, last_updated=datetime('now');

-- commit the transaction
COMMIT;
