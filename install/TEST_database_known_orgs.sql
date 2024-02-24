-- DB setup for Zzz system - TESTING known orgs

PRAGMA foreign_keys=off;

drop table if exists known_org;
drop table if exists known_org_ip;
drop table if exists known_org_domain;

PRAGMA foreign_keys=on;

-- Create tables and indexes

-- --------------------------------------------------

-- known orgs - by IP/CIDR or domain
-- populate on install from a data file
create table known_org (
    id integer primary key,
    org_name text not null
)
create unique index if not exists org_name_idx on known_org(org_name);

create table known_org_ip (
    known_org_id integer not null,
    cidr text not null,
    FOREIGN KEY(known_org_id) REFERENCES known_org(id)
)
create unique index if not exists known_cidr_idx on known_org_ip(cidr);

create table known_org_domain (
    known_org_id integer not null,
    domain_name text not null,
    FOREIGN KEY(known_org_id) REFERENCES known_org(id)
)
create unique index if not exists known_domain_name_idx on known_org_domain(domain_name);

-- --------------------------------------------------

