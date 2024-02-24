-- one-time dev fix 9/12/2020 - fix foreign key

-- BEFORE UPDATE: stop apps, cron

-- select uf.id, uf.service_request_id, sr.req_date from update_file uf, service_request sr where uf.service_request_id=sr.id and sr.req_date>'2020-05-01';
-- select * from service_request where id=3738;
-- select * from update_file where id=219;
--
-- select id, service_request_id from update_file;

PRAGMA foreign_keys=off;
BEGIN TRANSACTION;

drop index if exists update_req_date_idx;

-- rename old table to temporary name
ALTER TABLE update_file RENAME TO update_file_old;

-- make new table
create table update_file(
    id integer primary key,
    service_request_id integer not null,
    file_data text not null,
    src_filepath text,
    FOREIGN KEY(service_request_id) REFERENCES service_request(id)
);
create index if not exists update_req_date_idx on update_file(service_request_id);

-- copy data
INSERT INTO update_file (id, service_request_id, file_data, src_filepath)
  SELECT id, service_request_id, file_data, src_filepath
  FROM update_file_old;

COMMIT;
PRAGMA foreign_keys=on;

-- AFTER UPDATE: start apps, cron
--               manually drop old table after verifying the new table
--                 drop table update_file_old
