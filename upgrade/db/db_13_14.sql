-- DB upgrade from zzz_system version 13 to 14
-- Changes: incremented version number

-- start a transaction
BEGIN TRANSACTION;

-- update the system version number
update zzz_system set version=14, last_updated=datetime('now');

-- commit the transaction
COMMIT;
