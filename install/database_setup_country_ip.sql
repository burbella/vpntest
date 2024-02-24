-- load IP-deny files into a DB: country-ip.sqlite3
-- source files: /opt/zzz/data/ipdeny-ipv4/*

drop table if exists countries;
drop table if exists country_ip_map;

create table if not exists countries(
    country_code text not null,
    country text not null,
    blocked boolean not null
);
create index if not exists country_code2_idx on countries(country_code);
create index if not exists country_idx on countries(country);
create index if not exists blocked_idx on countries(blocked);

create table if not exists country_ip_map(
    country_code text not null,
    ip_cidr text not null
);
create index if not exists country_code_idx on country_ip_map(country_code);
