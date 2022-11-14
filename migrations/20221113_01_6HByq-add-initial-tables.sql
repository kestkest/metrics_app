-- add initial tables
-- depends: 

create table assets(
    id int generated by default as identity primary key,
    name text not null
);

ALTER TABLE assets ADD CONSTRAINT asset_name UNIQUE (name);

create table metrics(
    asset_id int not null references assets,
    value decimal not null,
    time int not null
);

create index asset_value_time_idx on metrics(asset_id, time);