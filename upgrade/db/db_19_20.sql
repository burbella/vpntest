-- DB upgrade from zzz_system version 19 to 20
-- Changes: added dev version tag

-- start a transaction
BEGIN TRANSACTION;

-- update the system version number
alter table zzz_system add column dev_version text;
update zzz_system set version=20, last_updated=datetime('now');

-- commit the transaction
COMMIT;
