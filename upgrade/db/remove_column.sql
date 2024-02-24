-- one-time dev fix 5/26/2020 - remove column from table

PRAGMA foreign_keys=off;
BEGIN TRANSACTION;

-- rename old table to temporary name
ALTER TABLE zzz_system RENAME TO zzz_system_old;

-- make new table
create table zzz_system(
    version integer not null,
    available_version integer,
    json text not null,
    ip_log_last_time_parsed text,
    last_updated integer not null
);

-- copy data
INSERT INTO zzz_system (version, available_version, json, ip_log_last_time_parsed, last_updated)
  SELECT version, available_version, json, ip_log_last_time_parsed, last_updated
  FROM zzz_system_old;

COMMIT;
PRAGMA foreign_keys=on;
