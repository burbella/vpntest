-- DB upgrade from zzz_system version 12 to 13
-- Changes: incremented version number

-- start a transaction
BEGIN TRANSACTION;

-- update the system version number
update zzz_system set version=13, last_updated=datetime('now');

-- commit the transaction
COMMIT;
