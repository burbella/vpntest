-- ip-country new table
-- load this into a separate ip-country DB file: ip-country.sqlite3

-- create a new table to put new data into, will be swapped with the old table later

BEGIN TRANSACTION;

create table if not exists ip_country_map_new(
    cidr text not null,
    ip_min integer not null,
    ip_max integer not null,
    country_code text not null,
    FOREIGN KEY(country_code) REFERENCES countries(country_code)
);

COMMIT;
