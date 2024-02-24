-- DB upgrade from zzz_system version 2 to 3
-- Changes: added squid_nobumpsites field to settings table

-- start a transaction
BEGIN TRANSACTION;

-- rename the new table to the old table
ALTER TABLE settings add column squid_nobumpsites text; 

-- update the system version number
update zzz_system set version=3, last_updated=datetime('now');

-- commit the transaction
COMMIT;
