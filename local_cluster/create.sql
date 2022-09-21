CREATE TABLE IF NOT EXISTS table1 ON CLUSTER mycluster
(
    number UInt64
) ENGINE = ReplicatedMergeTree('/clickhouse/tables/table1', '{replica}')
ORDER BY tuple();


insert into table1 select * from system.numbers limit 100000000;

select count(*) from table1;