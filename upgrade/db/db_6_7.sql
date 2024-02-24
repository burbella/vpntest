-- DB upgrade from zzz_system version 6 to 7
-- Changes: incremented version number (new icap server didn't need additional DB changes)

-- start a transaction
BEGIN TRANSACTION;

-- update the system version number
update zzz_system set version=7, last_updated=datetime('now');

-- commit the transaction
COMMIT;
