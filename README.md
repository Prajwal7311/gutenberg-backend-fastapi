# Backend Books API

Goal of the project is to design and build a RESTful service built with [FastAPI](https://fastapi.tiangolo.com/) that allows users to query and access book data stored in a MySQL database. It uses [`mysql-connector-python`](https://pypi.org/project/mysql-connector-python/) for direct database interactions and supports various filtering options, pagination, and ordering by popularity.

## Features

- **Dynamic Filtering**: Filter books by:
  - Project Gutenberg IDs
  - Language codes
  - MIME types
  - Topics (subjects and bookshelves; case-insensitive, partial matches)
  - Author names (case-insensitive, partial matches)
  - Book titles (case-insensitive, partial matches)
- **Pagination**: Returns 25 books per page with support for retrieving subsequent pages.
- **Popularity Sorting**: Books are ordered by their download count in descending order.
- **JSON Responses**: All data is returned in JSON format.
- **Public Access**: Designed to be publicly accessible with proper security and deployment practices.


## Prerequisites

- **Python 3.12**
- Required Python packages:
  - `fastapi`
  - `uvicorn`
  - `mysql-connector-python`

Install dependencies using pip:

```bash
pip install -r requirements.txt
```

## Test The Api
```bash
uvicorn main:app --reload
```
### Testing With Swagger UI

Once the api link is generated in the terminal, append the link with /docs to open the Swagger UI page.
Test the routes by entering the input manually.



