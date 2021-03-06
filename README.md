# Giveawaynesses

A free/open-source/easy/verbosive giveaway bot for discord.

## Features

- Condition (still not implemented multiple conditions)
- Fully customizable giveaway embed
- PostgreSQL (for fast database)
- Get giveaway info from their ID (still not implemented)
- Tracking end time

## Status

- [x] Database
- [x] Embed
- [x] Condition
- [ ] Conditions
- [x] Get giveaway info
- [ ] Stable

## How to setup

REMINDER: You need to have a postgresql database running and you need poetry installed. Also you need to use git to clone this repository only downloading the zip file will likely break the version checking since it use git to check it commit is out of dated or updated.

1. Install poetry

```bash
pip install poetry
```

2. Install dependencies

```bash
poetry install
```

3. Configure .env file

```bash
DB_HOST=postgresql database hostname (ip address or hostname)
DB_PASS=postgresql database password
DISCORD_TOKEN=discord bot token
JISHAKU_HIDE=1 # hide jishaku
```  

4. Setup [postgresql database](#postgresql-setup)

5. Run the bot

```bash
poetry shell
python3 bot.py
```

## PostgreSQL setup

1. Install PostgreSQL

2. Execute this command using `psql` tool

```sql
CREATE ROLE giveaway_bot WITH LOGIN PASSWORD 'giveaway_bot';
CREATE DATABASE giveaways OWNER giveaway_bot;
COMMIT

```

3. You're likely done(?)
