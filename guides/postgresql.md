# PostgreSQL setup

1. Install PostgreSQL

2. Execute this command using `psql` tool

```sql
CREATE ROLE giveaway_bot WITH LOGIN PASSWORD 'giveaway_bot';
CREATE DATABASE giveaways OWNER giveaway_bot;
COMMIT
```

3. You're likely done(?)