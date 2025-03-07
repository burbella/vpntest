-- DB test data for pytest

-- start a transaction
BEGIN TRANSACTION;

insert into countries(country_code, country, blocked)
values('AQ', 'Antarctica', 1),
('IO', 'British Indian Ocean Territory', 0),
('CA', 'Canada', 0),
('TO', 'Tonga', 1),
('TV', 'Tuvalu', 1),
('US', 'USA', 0);

insert into tlds(tld, blocked)
values('COM', 0),
('GOV', 0),
('NET', 0),
('ORG', 0),
('TOP', 1);

update settings set json='{"autoplay": "true", "social": "true", "telemetry": "false", "duplicate_domain": "false", "block_country_tld": "true", "block_country_tld_always": "true", "block_country_ip_always": "false", "block_custom_ip_always": "false", "block_tld_always": "true", "dark_mode": "true", "check_zzz_update": "true", "auto_install_zzz_update": "false", "show_dev_tools": "true", "blocked_country": ["AQ", "TG"], "blocked_tld": ["XXX", "XYZ"]}',
    squid_nobumpsites='google.com',
    squid_hide_domains='microsoft.com',
    hide_ips='1.2.3.4',
    allow_ips='8.8.8.8',
    last_updated=datetime('2022-01-02 03:04:05');

update zzz_system set webserver_domain='services.pytest.zzz';

insert into ip_log_daily(ip, country_code, num_accepted, num_blocked, is_ipv4, is_cidr, is_private, log_date, last_updated)
values('8.8.8.8', 'US', 123, 0, 1, 0, 0, datetime('2022-01-02 03:04:05'), '2022-01-02');

-- commit the transaction
COMMIT;
