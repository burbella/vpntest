-- DB upgrade from zzz_system version 4 to 5
-- Changes: added countries table

-- start a transaction
BEGIN TRANSACTION;

alter table settings add column squid_hide_domains text;

-- update the system version number
update zzz_system set version=5, last_updated=datetime('now');

-- commit the transaction
COMMIT;
