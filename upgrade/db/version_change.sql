-- one-time upgrade of versioning system 10/24/2020

PRAGMA foreign_keys=off;
BEGIN TRANSACTION;

-- rename old table to temporary name
ALTER TABLE zzz_system RENAME TO zzz_system_old;

create table zzz_system(
    version text not null,
    available_version text not null,
    json text not null,
    ip_log_last_time_parsed text,
    last_updated integer not null
);

-- copy data, replace version numbers with new versions
INSERT INTO zzz_system (version, available_version, json, ip_log_last_time_parsed, last_updated)
  SELECT '10.00', '10.00', json, ip_log_last_time_parsed, last_updated
  FROM zzz_system_old;

-- do the table drop manually
--drop table zzz_system_old;

COMMIT;
PRAGMA foreign_keys=on;
