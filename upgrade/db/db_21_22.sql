-- DB upgrade from zzz_system version 21 to 22
-- Changes: added dev version tag

-- start a transaction
BEGIN TRANSACTION;

alter table settings add column allow_ips text;

-- update the system version number
update zzz_system set version=22, last_updated=datetime('now');

-- commit the transaction
COMMIT;
