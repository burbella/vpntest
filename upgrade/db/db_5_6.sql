-- DB upgrade from zzz_system version 5 to 6
-- Changes: incremented version number (new icap server didn't need additional DB changes)

-- start a transaction
BEGIN TRANSACTION;

-- update the system version number
update zzz_system set version=6, last_updated=datetime('now');

-- commit the transaction
COMMIT;
