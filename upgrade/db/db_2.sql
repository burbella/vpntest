-- DB upgrade from zzz_system version 1 to 2
-- Changes: status field changed from integer to text

-- disable foreign key constraint check
PRAGMA foreign_keys=off;

-- start a transaction
BEGIN TRANSACTION;

-- make new table
CREATE TABLE IF NOT EXISTS new_service_request( 
    id integer primary key,
    req_date integer not null,
    service_name text not null,
    action text not null,
    status text not null,
    details text,
    start_date integer,
    wait_time integer,
    end_date integer,
    work_time integer
);

-- copy data from the table to the new_table
INSERT INTO new_service_request(id, req_date, service_name, action, status, details, start_date, wait_time, end_date, work_time)
    SELECT id, req_date, service_name, action, status, details, start_date, wait_time, end_date, work_time
    FROM service_request;

-- convert status field data to new format
update new_service_request set status='Requested' where status='1';
update new_service_request set status='Working' where status='2';
update new_service_request set status='Done' where status='3';
update new_service_request set status='Error' where status='4';

-- drop the old table
DROP TABLE service_request;

-- rename the new table to the old table
ALTER TABLE new_service_request RENAME TO service_request; 

-- commit the transaction
COMMIT;

-- enable foreign key constraint check
PRAGMA foreign_keys=on;

-- update the system version number
update zzz_system set version=2, last_updated=datetime('now');
