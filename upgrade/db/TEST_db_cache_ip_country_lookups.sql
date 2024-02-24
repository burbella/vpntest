-- DB upgrade from zzz_system version CURRENT to NEW
-- Changes: added country cache to ip log tables

-- start a transaction
BEGIN TRANSACTION;

alter table ip_log_daily country_code text;
alter table ip_log_daily country_updated integer;

alter table ip_log_summary country_code text;
alter table ip_log_summary country_updated integer;

-- commit the transaction
COMMIT;
