-- Free My ID home-page A/B/C test totals (docs/AB_TEST.md). One row per day, arm, event and page with a running
-- count. Nothing about a visitor: no IP address, user agent, referrer, location, cookie or time finer than the day.
CREATE TABLE IF NOT EXISTS totals (
  day   TEXT    NOT NULL,            -- YYYY-MM-DD (UTC)
  arm   TEXT    NOT NULL,            -- control | heritage | frontier | glory
  event TEXT    NOT NULL,            -- assign | view | download
  page  TEXT    NOT NULL,            -- site path inside the arm, e.g. "/" or "/how-it-works/"
  n     INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (day, arm, event, page)
);
