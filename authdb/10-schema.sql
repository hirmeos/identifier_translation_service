CREATE TABLE account(
  account_id varchar(255) PRIMARY KEY NOT NULL,
  email varchar(255) UNIQUE NOT NULL,
  password varchar(255) NOT NULL
);

CREATE TABLE token (
  token varchar(255) PRIMARY KEY NOT NULL,
  timestamp timestamp with time zone NOT NULL,
  expiry timestamp with time zone NOT NULL
);

CREATE TABLE account_token (
  account_id varchar(255) PRIMARY KEY NOT NULL REFERENCES account(account_id) ON DELETE CASCADE ON UPDATE CASCADE,
  token varchar(255) UNIQUE NOT NULL REFERENCES token(token) ON DELETE CASCADE ON UPDATE RESTRICT
);
