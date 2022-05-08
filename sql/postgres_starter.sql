DROP TABLE IF EXISTS giveaways;
CREATE TABLE IF NOT EXISTS giveaways(
    id BIGSERIAL,
    owner_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    message_id BIGINT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    started_at FLOAT NOT NULL,
    duration BIGINT NOT NULL,
    ended_at FLOAT NOT NULL,
    winner_id BIGINT,
    conditions TEXT,
    prize TEXT NOT NULL,
    PRIMARY KEY (id)
)