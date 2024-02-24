-- DB upgrade from zzz_system version 7 to 8
-- Changes: incremented version number

-- start a transaction
BEGIN TRANSACTION;

-- update the system version number
update zzz_system set version=8, last_updated=datetime('now');

-- commit the transaction
COMMIT;
