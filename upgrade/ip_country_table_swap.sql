-- ip-country table swaps
-- load this into a separate ip-country DB file: ip-country.sqlite3

-- assume: new table exists, is already filled with data, needs to replace the old table

BEGIN TRANSACTION;

-- old indexes
drop index if exists country_code_idx;
drop index if exists cidr_idx;
drop index if exists ip_min;
drop index if exists ip_max;

-- swap table names
ALTER TABLE ip_country_map RENAME TO ip_country_map_old;
ALTER TABLE ip_country_map_new RENAME TO ip_country_map;

-- rebuild indexes
create index if not exists country_code_idx on ip_country_map(country_code);
create index if not exists cidr_idx on ip_country_map(cidr);
create index if not exists ip_min_idx on ip_country_map(ip_min);
create index if not exists ip_max_idx on ip_country_map(ip_max);

-- drop old table
drop table ip_country_map_old;

COMMIT;

