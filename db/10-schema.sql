CREATE EXTENSION fuzzystrmatch;

CREATE TABLE uri_scheme(
  uri_scheme varchar(255) PRIMARY KEY NOT NULL
);

CREATE TABLE uri(
  uri_scheme varchar(255) NOT NULL REFERENCES uri_scheme(uri_scheme),
  uri_value varchar(255) NOT NULL,
  PRIMARY KEY(uri_scheme, uri_value)
);

CREATE TABLE title(
  title varchar(255) PRIMARY KEY NOT NULL
);

CREATE TABLE work_type(
  work_type varchar(255) PRIMARY KEY NOT NULL
);

CREATE TABLE work(
  work_id uuid PRIMARY KEY NOT NULL,
  work_type varchar(255) NOT NULL REFERENCES work_type(work_type) ON UPDATE CASCADE
);

CREATE TABLE work_relation(
  parent_work_id uuid NOT NULL REFERENCES work (work_id) ON DELETE CASCADE,
  child_work_id uuid NOT NULL REFERENCES work (work_id) ON DELETE CASCADE,
  PRIMARY KEY(parent_work_id, child_work_id),
  CONSTRAINT self_referencing_forbidden CHECK (parent_work_id <> child_work_id)
);

CREATE TABLE work_title(
  work_id uuid NOT NULL REFERENCES work(work_id) ON DELETE CASCADE,
  title varchar(255) NOT NULL REFERENCES title ON UPDATE CASCADE,
  PRIMARY KEY(work_id, title)
);

CREATE TABLE work_uri(
  work_id uuid NOT NULL REFERENCES work(work_id) ON DELETE CASCADE,
  uri_scheme varchar(255) NOT NULL,
  uri_value varchar(255) NOT NULL,
  canonical boolean NOT NULL DEFAULT FALSE,
  PRIMARY KEY(work_id, uri_scheme, uri_value),
  CONSTRAINT work_uri_uri_fkey FOREIGN KEY (uri_scheme, uri_value) REFERENCES uri (uri_scheme, uri_value) ON UPDATE CASCADE
);
CREATE UNIQUE INDEX canonical_uri ON work_uri(work_id, uri_scheme) WHERE canonical = TRUE;
