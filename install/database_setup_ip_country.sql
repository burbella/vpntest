-- load this into a separate ip-country DB file: ip-country.sqlite3
-- source files: /opt/zzz/data/ipdeny-ipv4/*

drop table if exists countries;
drop table if exists ip_country_map;

-- duplicate this from the main DB for efficient joins
create table if not exists countries(
    country_code text not null,
    country text not null
);
create unique index if not exists country_code2_idx on countries(country_code);
create index if not exists country2_idx on countries(country);

-- populate the DB with data from ipdeny files
-- lookup the country for a given IP: IP=ip1.ip2.ip3.ip4
create table if not exists ip_country_map(
    cidr text not null,
    ip_min integer not null,
    ip_max integer not null,
    country_code text not null,
    FOREIGN KEY(country_code) REFERENCES countries(country_code)
);
create index if not exists country_code_idx on ip_country_map(country_code);
create index if not exists cidr_idx on ip_country_map(cidr);
create index if not exists ip_min_idx on ip_country_map(ip_min);
create index if not exists ip_max_idx on ip_country_map(ip_max);
