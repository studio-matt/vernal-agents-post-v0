-- Create topic modeling tables for system model
-- For MySQL; adjust types as needed

CREATE TABLE IF NOT EXISTS topic_models (
  model_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  created_at DATETIME NOT NULL,
  algo VARCHAR(50) NOT NULL,
  tfidf_min_df INT NOT NULL,
  tfidf_max_df FLOAT NOT NULL,
  phrases_min_count INT NOT NULL,
  phrases_threshold FLOAT NOT NULL,
  k INT NOT NULL,
  coherence FLOAT NOT NULL,
  INDEX idx_created_at (created_at)
);

CREATE TABLE IF NOT EXISTS topics (
  topic_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  model_id BIGINT NOT NULL,
  label VARCHAR(128) NOT NULL,
  top_terms JSON NOT NULL,
  coverage FLOAT NOT NULL,
  rank INT NOT NULL,
  INDEX idx_topics_model (model_id),
  INDEX idx_topics_rank (rank),
  FOREIGN KEY (model_id) REFERENCES topic_models(model_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS topic_docs (
  model_id BIGINT NOT NULL,
  doc_id BIGINT NOT NULL,
  topic_id BIGINT NOT NULL,
  weight FLOAT NOT NULL,
  INDEX idx_td_model (model_id),
  INDEX idx_td_doc (doc_id),
  INDEX idx_td_topic (topic_id),
  FOREIGN KEY (model_id) REFERENCES topic_models(model_id) ON DELETE CASCADE,
  FOREIGN KEY (topic_id) REFERENCES topics(topic_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS topic_snippets (
  snippet_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  model_id BIGINT NOT NULL,
  topic_id BIGINT NOT NULL,
  url TEXT NOT NULL,
  domain VARCHAR(255),
  title TEXT,
  snippet TEXT NOT NULL,
  score FLOAT NOT NULL,
  INDEX idx_ts_model (model_id),
  INDEX idx_ts_topic (topic_id),
  FOREIGN KEY (model_id) REFERENCES topic_models(model_id) ON DELETE CASCADE,
  FOREIGN KEY (topic_id) REFERENCES topics(topic_id) ON DELETE CASCADE
);

