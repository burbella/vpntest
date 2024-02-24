-- DB upgrade from zzz_system version 3 to 4
-- Changes: added countries table

-- start a transaction
BEGIN TRANSACTION;

-- list of countries
create table if not exists countries(
    country_code text not null,
    country text not null,
    blocked boolean not null
);
create index if not exists country_code_idx on countries(country_code);
create index if not exists country_idx on countries(country);
create index if not exists blocked_idx on countries(blocked);

-- cache whois IP/CIDR lookups
create table ipwhois_cache(
    ip text not null,
    json text not null,
    zzz_last_updated integer not null,
    
    asn text not null,
    asn_cidr text not null,
    asn_country_code text,
    asn_date text,
    asn_date_int integer,
    asn_description text not null,
    
    network_cidr text not null,
    network_country_code text,
    ip_version text not null,
    
    org text,
    
    raw_whois text
);
create index if not exists ipwhois_ip_idx on ipwhois_cache(ip);
create index if not exists zzz_last_updated_ip_idx on ipwhois_cache(zzz_last_updated);


-- update the system version number
update zzz_system set version=4, last_updated=datetime('now');

-- commit the transaction
COMMIT;
