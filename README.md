# Identifier Translation Service
[![Build Status](https://travis-ci.org/hirmeos/identifier_translation_service.svg?branch=master)](https://travis-ci.org/hirmeos/identifier_translation_service) ![Code Climate maintainability](https://img.shields.io/codeclimate/maintainability/hirmeos/identifier_translation_service) [![Release](https://img.shields.io/github/release/hirmeos/identifier_translation_service.svg?colorB=58839b)](https://github.com/hirmeos/identifier_translation_service/releases) [![License](https://img.shields.io/github/license/hirmeos/identifier_translation_service.svg?colorB=ff0000)](https://github.com/hirmeos/identifier_translation_service/blob/master/LICENSE)

The Identifier Translation Service is a JSON REST API to a [database of publication URIs][1]. The translation service maps works (publications) to URIs (e.g. info:doi:10.11647/obp.0001, urn:isbn:9781906924010, https://www.openbookpublishers.com/product/3) to allow converting from one identifier to another.


## Setup

### Authentication
If you are planning to expose the API to the internet you may protect it using JWT. You must set up a tokens API such as [hirmeos/tokens_api][2] and share the secret key with this service via the `SECRET_KEY` env variable, the translation service will then expect a token in the `Authorization` header of each request it receives and will check whether it was generated with the secret key.

### Environment variables
The following environment variables may be set. If you're running the service using docker-compose, you may use different files to separate API-specific variables from database's. All variables must be set.

| Variable             | Description                                                                                                                  |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `API_DEBUG`          | Boolean flag to output debugging lines to the console.                                                                       |
| `JWT_DISABLED`       | Boolean flag to toggle using JWT authentication. Should only be set to `False` in a local network or developing environment. |
| `SECRET_KEY`         | An up to 255 bytes random key, shared with a [JWT API][2].                                                                   |
| `IDENTIFIERSDB_HOST` | The address of the host where the identifiers database runs.                                                                 |
| `IDENTIFIERSDB_DB`   | The name of the identifiers database.                                                                                        |
| `IDENTIFIERSDB_USER` | The user name of the identifiers database.                                                                                   |
| `IDENTIFIERSDB_PASS` | The password of the identifiers database.                                                                                    |
| `ALLOW_ORIGIN`       | String with a domain name to be included in CORS headers.                                                                    |

### Running with docker-compose
The easiest way to get a fully featured and functional setup is using a docker-compose file, since the API depends on the [hirmeos/identifiers_db][1] database.

```
version: "3.5"

services:
  identifiertranslatorservice_db:
    image: openbookpublishers/identifiers_db:1
    container_name: "identifiertranslatorservice_db"
    restart: unless-stopped
    volumes:
      - db:/var/lib/postgresql/data
    env_file:
      - ./config/db.env

  identifiertranslatorservice_api:
    image: openbookpublishers/identifier_translation_service:1
    container_name: "identifiertranslatorservice_api"
    restart: unless-stopped
    ports:
      - 8080:8080
    environment:
      - IDENTIFIERSDB_HOST=identifiertranslatorservice_db
    env_file:
      - ./config/api.env
      - ./config/db.env
    depends_on:
      - identifiertranslatorservice_db

volumes:
  db:
```
Notes:
- The example uses the docker images already built and used by Open Book Publishers. You may use the provded docker files to build your own, instead.
- You may of course use whatever port you like, and/or use a proxy server (e.g. nginx) to handle the API endpoint.
- The `db` volume ensure the contents of the database persist when restarting/deleting the container.
- In this example we use two sets of configuration files, one with database credentials shared with both containers, the other one with API configuration only available to the API container. You may use a single file with all environment variables.

## API Structure

### Publication identifiers as URIs
The translation service stores all work (publication) identifiers as URIs, therefore when querying/populating the database you must use the relevant [URI scheme][7].

| Identifier | URI Scheme | Example                                       |
| ---------- | ---------- | --------------------------------------------- |
| ISBN       | urn:isbn   | urn:isbn:9781906924003                        |
| DOI        | info:doi   | info:doi:10.11647/obp.0001                    |
| ISSN       | urn:issn   | urn:issn:20542445                             |
| UUID       | urn:uuid   | urn:uuid:463b4279-4e8d-47f8-a133-ad8ce7c4f86c |
| Handle     | info:hdl   | info:hdl:10670/1.di2dtn                       |
| URL        | http       | http://www.openbookpublishers.com/product/3   |
| URL        | https      | https://www.openbookpublishers.com/product/3  |

#### The canonical flag
When multiple identifiers of the same scheme are associated with the same work, **you may set one and only one canonical URI per URI scheme and work**, which will be the returned value when the `strict` flag is used.

The `/translate` path attempts to retrieve a unique identifier of the chosen URI scheme (e.g. translating from a urn:isbn to a info:doi), if more than one identifier of the same URI scheme is found the API will complain that it is not able to translate properly. The canonical flag makes sure that in such a case the API is able to translate to the desired canonical URI of that particular scheme.

A work can have at most one canonical URI of each URI scheme (e.g. one canonical URL, one canonical ISBN, one canonical DOI, etc.).

### API routes
The following methods are allowed:

| Method   | Route             | Description                                                                |
| -------- | ----------------- | -------------------------------------------------------------------------- |
| `GET`    | `/translate`      | Takes a `uri` as parameter and returns all identifiers associated with it. |
| `GET`    | `/works`          | Return information about stored publications.                              |
| `POST`   | `/works`          | Store a publication and associated URIs in the database.                   |
| `DELETE` | `/works`          | Delete a publication from the database.                                    |
| `POST`   | `/titles`         | Add a new title to an existing publication.                                |
| `DELETE` | `/titles`         | Remove a title from its publication.                                       |
| `POST`   | `/uris`           | Add a new URI to an existing publication.                                  |
| `DELETE` | `/uris`           | Remove a URI from its publication.                                         |
| `GET`    | `/work_types`     | Retrieve the full list of publication types.                               |
| `POST`   | `/work_relations` | Store a relationship between two publications (e.g. book -> chapter)       |

### `/translate` Queries

This is the most important method in the API since it serves the purpose of translating a given identifier to the desired match (e.g. translate an ISBN or a URL to a DOI).

#### Translation by URI
Translation by URI (identifier) will query the database searching for other URIs associated with the input. To translate from one uri_scheme to another (e.g. input ISBN to retrieve a DOI) you will need to set a filter of type `uri_scheme` (see below).

#### Translation by title
Translation by title uses the Levenshtein distance between the input and the stored titles in the database, and outputs a list of candidates matching the given title along with a score (where 0 is a perfect match). When the `strict` flag is set, the API will attempt to return only the fittest candidate for the query.

#### Translation parameters

You may use this method to either translate a `uri` or a `title`, hence one and only one of either parameters is compulsory.

| Parameter | Description                                                                                          |
| --------- | ---------------------------------------------------------------------------------------------------- |
| uri       | The URI you want to translate                                                                        |
| title     | A URL-encoded title to search for.                                                                   |
| filter    | A concatenation of filters of type `work_type`, `uri_scheme`, `canonical` allows refining the query. |
| strict    | Defaults to `false`. When set to `true` it enforces the return of a single identifier.               |

#### Translation example
`/translate?uri=urn:isbn:9781906924652&strict=true&filter=work_type:monograph,work_type:book,uri_scheme:info:doi` will retrieve a unique book DOI for the given ISBN; if the `work_type` wasn't specified, the query would fail to retrieve a single DOI, since it would also include chapter DOIs which are associated with that same ISBN.

```
{
  "code": 200,
  "status": "ok",
  "data": [
    {
      "URI": "info:doi:10.11647/obp.0001",
      "URI_parts": {
        "scheme": "info:doi",
        "value": "10.11647/obp.0001"
      },
      "canonical": true,
      "score": 0,
      "work": {
        "type": "monograph",
        "URI": [],
        "UUID": "463b4279-4e8d-47f8-a133-ad8ce7c4f86c",
        "title": [
          "That Greece Might Still Be Free: The Philhellenes in the War of Independence"
        ]
      }
    }
  ],
  "count": 1
}
```
### `/works` Queries
This route is used to either retrieve full work records, or to populate the database with new works.

#### `GET /works` parameters

You may use this method to either translate a `uri` or a `title`, hence one and only one of either parameters is compulsory.

| Parameter | Description                                                                                                                               |
| --------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| uuid      | The `work_id` UUID of a particular work. If provided it will retrieve a single publication, if not set it will retrieve all publications. |
| filter    | A concatenation of filters of type `work_type`, `uri_scheme`, `canonical` allows refining the query.                                      |


#### `GET /works` example

`/works?filter=work_type:monograph,work_type:book,uri_scheme:info:doi,canonical:true` will retrieve the canonical DOI of all books and monographs.

```
{
  "code": 200,
  "status": "ok",
  "count": 145,
  "data": [
    {
      "type": "monograph",
      "URI": [
        {
          "URI": "info:doi:10.11647/obp.0033",
          "URI_parts": {
            "scheme": "info:doi",
            "value": "10.11647/obp.0033"
          },
          "canonical": true,
          "score": 0
        }
      ],
      "UUID": "0034efd8-be0b-4527-b0e0-bad1faff3c2f",
      "title": [
        "Storytelling in Northern Zambia: Theory, Method, Practice and Other Necessary Fictions",
        "Storytelling in Northern Zambia. Theory, Method, Practice and Other Necessary Fictions"
      ]
    },
    ...
  ]
}
```
#### `POST /works` data

| Attribute | Type                       | Description                                                                          |
| --------- | -------------------------- | ------------------------------------------------------------------------------------ |
| title     | string or array of strings | One or more titles that represent the publication.                                   |
| type      | string                     | The publication type of the work (e.g. 'book', 'book-chapter').                      |
| uri       | object or array of objects | Each URI object must have a `uri` (string) and a `canonical` (boolean) attributes.   |
| parent    | string or array of strings | Optional. You may provide the UUID of an existing work that is a parent of this one. |
| child     | string or array of strings | Optional. You may provide the UUID of an existing work that is a child of this one.  |


#### `POST /works` example
In this example we use a fictional parent UUID, which could be one of a book series for example - and two child UUIDs, which could represent two chapters in the book.
```
{
  "type": "monograph",
  "title": [
    "That Greece Might Still Be Free: The Philhellenes in the War of Independence",
    "That Greece Might Still Be Free"
  ],
  "uri": [
    {
      "uri": "info:doi:10.11647/obp.0001",
      "canonical": true
    }, {
      "uri": "urn:isbn:9781906924003",
      "canonical": true
    }, {
      "uri": "urn:isbn:9781906924027",
      "canonical": false
    }, {
      "uri": "https://www.openbookpublishers.com/product/3",
      "canonical": false
    }
  }],
  "parent": "0a0f1877-d3da-4a84-bce6-e388b5e722d5",
  "child": [
    "b23bfb0f-dc1b-45bd-9f31-2955dcae9b0d",
    "a5175483-8d03-4d82-9522-a039fb8873aa"
  ]
}
```

#### `DELETE /works` data

| Attribute | Type   | Description                        |
| --------- | ------ | ---------------------------------- |
| UUID      | string | The work_id of the work to delete. |


### More
Check some more [example queries][6].

## Crosref extension
The main purpose of this service was to store as many URIs per publication as possible, and it's unlikely that the user of this software will be aware of all of them. For this reason you may set up [hirmeos/crossref_uri_import][3] to periodically query Crossref's API with your DOIs and populate the translation service with potential new data (e.g. multiple DOIs assigned to the same publication, multiple resolution URLs).

## Populating the database
You may write your own version of [OpenBookPublishers/obp_product_import][4] to populate the translation service with your existing data. Or you can use this script to add individual URIs to an existing publication: [OpenBookPublishers/obp_uri_import][5]

[1]: https://github.com/hirmeos/identifiers_db "Identifiers database"
[2]: https://github.com/hirmeos/tokens_api "Tokens API"
[3]: https://github.com/hirmeos/crossref_uri_import "Crossref URI import"
[4]: https://github.com/OpenBookPublishers/obp_product_import "OBP Book import"
[5]: https://github.com/OpenBookPublishers/obp_uri_import "OBP URI import"
[6]: https://docs.google.com/document/d/1aEwV_6CF8ha5M5yRu6FsYWQBDbTMeazWDIj1h3kLSec/edit "Example queries"
[7]: https://www.iana.org/assignments/uri-schemes/uri-schemes.xhtml "URI Schemes"
