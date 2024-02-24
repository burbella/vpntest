-- DB setup for Zzz RDAP TEST

drop table if exists rdap_cache;

-- RDAP is the new Whois
-- data types: domain, ip, asn
-- the raw query data goes in the json field
create table rdap_cache(
    rdap_query text not null,
    query_type text not null,
    json text not null,
    zzz_last_updated integer not null,
    registrar text,
    registrar_url text,
    org text,
    country_code text,
    creation_date integer,
    expiration_date integer,
    updated_date integer
);
create unique index if not exists rdap_query_idx on rdap_cache(rdap_query);
create unique index if not exists rdap_query_type_idx on rdap_cache(query_type);
create index if not exists rdap_zzz_last_updated_idx on rdap_cache(zzz_last_updated);


