DROP TABLE IF EXISTS giveaways;
CREATE TABLE IF NOT EXISTS giveaways(
    id SERIAL,
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    message_id BIGINT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    started_at BIGINT NOT NULL,
    duration BIGINT NOT NULL,
    ended_at BIGINT NOT NULL,
    winner_id BIGINT,
    conditions TEXT NOT NULL,
    prize TEXT NOT NULL,
    PRIMARY KEY (id)
)