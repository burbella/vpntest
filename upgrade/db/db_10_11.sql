-- DB upgrade from zzz_system version 10 to 11
-- Changes: incremented version number

-- start a transaction
BEGIN TRANSACTION;

alter table zzz_system add column ip_log_last_time_parsed text;

-- update the system version number
update zzz_system set version=11, last_updated=datetime('now');

-- commit the transaction
COMMIT;
