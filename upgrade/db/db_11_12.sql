-- DB upgrade from zzz_system version 11 to 12
-- Changes: added column available_version in zzz_system

-- start a transaction
BEGIN TRANSACTION;

alter table zzz_system add column available_version integer;

-- update the system version number
update zzz_system set version=12, available_version=12, last_updated=datetime('now');

-- commit the transaction
COMMIT;
