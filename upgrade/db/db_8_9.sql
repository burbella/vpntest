-- DB upgrade from zzz_system version 8 to 9
-- Changes: incremented version number

-- start a transaction
BEGIN TRANSACTION;

-- update the system version number
update zzz_system set version=9, last_updated=datetime('now');

-- commit the transaction
COMMIT;
