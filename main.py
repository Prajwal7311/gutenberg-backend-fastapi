from fastapi import FastAPI, Query, HTTPException
from typing import Optional
import mysql.connector
from database import connection_pool
import schemas

app = FastAPI(title="Books API")


@app.get("/books", response_model=schemas.BooksResponse)
def get_books(
    gutenberg_id: Optional[str] = Query(
        None, description="Comma separated Gutenberg ID numbers"
    ),
    language: Optional[str] = Query(None, description="Comma separated language codes"),
    mime_type: Optional[str] = Query(None, description="Comma separated MIME types"),
    topic: Optional[str] = Query(
        None,
        description=(
            "Comma separated topic filters (applies to subjects and bookshelves). "
            "Case-insensitive partial matches are supported."
        ),
    ),
    author: Optional[str] = Query(
        None, description="Partial match for author name (case-insensitive)"
    ),
    title: Optional[str] = Query(
        None, description="Partial match for book title (case-insensitive)"
    ),
    page: int = Query(1, ge=1, description="Page number (25 books per page)"),
):
    # Build SQL filter conditions and parameters
    conditions = []
    params = []

    # --- Gutenberg ID Filter ---
    if gutenberg_id:
        id_list = [
            int(x.strip()) for x in gutenberg_id.split(",") if x.strip().isdigit()
        ]
        if id_list:
            placeholders = ",".join(["%s"] * len(id_list))
            conditions.append(f"b.gutenberg_id IN ({placeholders})")
            params.extend(id_list)

    # --- Title Filter ---
    if title:
        conditions.append("LOWER(b.title) LIKE %s")
        params.append(f"%{title.lower()}%")

    # --- Author Filter ---
    if author:
        author_values = [a.strip().lower() for a in author.split(",") if a.strip()]
        if author_values:
            sub_conditions = " OR ".join(
                ["LOWER(a.name) LIKE %s" for _ in author_values]
            )
            conditions.append(
                f"EXISTS (SELECT 1 FROM books_book_authors ba JOIN books_author a ON ba.author_id = a.id WHERE ba.book_id = b.id AND ({sub_conditions}))"
            )
            params.extend([f"%{a}%" for a in author_values])

    # --- Language Filter ---
    if language:
        language_values = [l.strip().lower() for l in language.split(",") if l.strip()]
        if language_values:
            placeholders = ",".join(["%s"] * len(language_values))
            conditions.append(
                f"EXISTS (SELECT 1 FROM books_book_languages bl JOIN books_language l ON bl.language_id = l.id WHERE bl.book_id = b.id AND LOWER(l.code) IN ({placeholders}))"
            )
            params.extend(language_values)

    # --- MIME-Type Filter ---
    if mime_type:
        mime_values = [m.strip() for m in mime_type.split(",") if m.strip()]
        if mime_values:
            placeholders = ",".join(["%s"] * len(mime_values))
            conditions.append(
                f"EXISTS (SELECT 1 FROM books_format f WHERE f.book_id = b.id AND f.mime_type IN ({placeholders}))"
            )
            params.extend(mime_values)

    # --- Topic Filter (subjects OR bookshelves) ---
    if topic:
        topic_values = [t.strip().lower() for t in topic.split(",") if t.strip()]
        if topic_values:
            sub_conditions_subject = " OR ".join(
                ["LOWER(s.name) LIKE %s" for _ in topic_values]
            )
            sub_conditions_bookshelf = " OR ".join(
                ["LOWER(bs.name) LIKE %s" for _ in topic_values]
            )
            conditions.append(
                f"(EXISTS (SELECT 1 FROM books_book_subjects bs JOIN books_subject s ON bs.subject_id = s.id WHERE bs.book_id = b.id AND ({sub_conditions_subject})) "
                f"OR EXISTS (SELECT 1 FROM books_book_bookshelves bb JOIN books_bookshelf bs ON bb.bookshelf_id = bs.id WHERE bb.book_id = b.id AND ({sub_conditions_bookshelf})))"
            )
            params.extend([f"%{t}%" for t in topic_values])
            params.extend([f"%{t}%" for t in topic_values])

    # Combine all conditions into a WHERE clause.
    where_clause = " AND ".join(conditions)
    if where_clause:
        where_clause = "WHERE " + where_clause

    # --- Build the Count and Main Queries ---
    count_query = f"SELECT COUNT(*) AS total FROM books_book b {where_clause}"
    main_query = (
        f"SELECT b.id, b.title, b.download_count, b.gutenberg_id, b.media_type "
        f"FROM books_book b {where_clause} "
        f"ORDER BY b.download_count DESC "
        f"LIMIT %s OFFSET %s"
    )
    limit = 25
    offset = (page - 1) * limit

    # --- Execute the Count and Main Queries ---
    try:
        conn = connection_pool.get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(count_query, params)
        count_row = cursor.fetchone()
        total_count = count_row["total"] if count_row else 0

        # Append pagination parameters
        query_params = params.copy()
        query_params.extend([limit, offset])
        cursor.execute(main_query, query_params)
        books = cursor.fetchall()
        book_ids = [book["id"] for book in books]
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=str(err))
    finally:
        cursor.close()
        conn.close()

    # If no books match the criteria, return an empty result.
    if not book_ids:
        return schemas.BooksResponse(total_count=total_count, books=[])

    # --- Retrieve Related Data in Batch ---
    authors_dict = {}
    languages_dict = {}
    subjects_dict = {}
    bookshelves_dict = {}
    formats_dict = {}

    try:
        conn = connection_pool.get_connection()
        cursor = conn.cursor(dictionary=True)
        # Prepare a comma-separated list of placeholders for IN clause.
        placeholders = ",".join(["%s"] * len(book_ids))

        # Authors
        author_query = (
            f"SELECT ba.book_id, a.name, a.birth_year, a.death_year "
            f"FROM books_book_authors ba "
            f"JOIN books_author a ON ba.author_id = a.id "
            f"WHERE ba.book_id IN ({placeholders})"
        )
        cursor.execute(author_query, book_ids)
        for row in cursor.fetchall():
            authors_dict.setdefault(row["book_id"], []).append(
                {
                    "name": row["name"],
                    "birth_year": row["birth_year"],
                    "death_year": row["death_year"],
                }
            )

        # Languages
        language_query = (
            f"SELECT bl.book_id, l.code "
            f"FROM books_book_languages bl "
            f"JOIN books_language l ON bl.language_id = l.id "
            f"WHERE bl.book_id IN ({placeholders})"
        )
        cursor.execute(language_query, book_ids)
        for row in cursor.fetchall():
            languages_dict.setdefault(row["book_id"], []).append(row["code"])

        # Subjects
        subject_query = (
            f"SELECT bs.book_id, s.name "
            f"FROM books_book_subjects bs "
            f"JOIN books_subject s ON bs.subject_id = s.id "
            f"WHERE bs.book_id IN ({placeholders})"
        )
        cursor.execute(subject_query, book_ids)
        for row in cursor.fetchall():
            subjects_dict.setdefault(row["book_id"], []).append(row["name"])

        # Bookshelves
        bookshelf_query = (
            f"SELECT bb.book_id, bsh.name "
            f"FROM books_book_bookshelves bb "
            f"JOIN books_bookshelf bsh ON bb.bookshelf_id = bsh.id "
            f"WHERE bb.book_id IN ({placeholders})"
        )
        cursor.execute(bookshelf_query, book_ids)
        for row in cursor.fetchall():
            bookshelves_dict.setdefault(row["book_id"], []).append(row["name"])

        # Formats
        format_query = (
            f"SELECT f.book_id, f.mime_type, f.url "
            f"FROM books_format f "
            f"WHERE f.book_id IN ({placeholders})"
        )
        cursor.execute(format_query, book_ids)
        for row in cursor.fetchall():
            formats_dict.setdefault(row["book_id"], []).append(
                {
                    "mime_type": row["mime_type"],
                    "url": row["url"],
                }
            )
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=str(err))
    finally:
        cursor.close()
        conn.close()

    # --- Assemble the Response ---
    books_out = []
    for book in books:
        book_id = book["id"]
        books_out.append(
            schemas.BookOut(
                title=book["title"],
                genre=book["media_type"],
                authors=[schemas.AuthorOut(**a) for a in authors_dict.get(book_id, [])],
                languages=languages_dict.get(book_id, []),
                subjects=subjects_dict.get(book_id, []),
                bookshelves=bookshelves_dict.get(book_id, []),
                formats=[schemas.FormatOut(**f) for f in formats_dict.get(book_id, [])],
            )
        )

    return schemas.BooksResponse(total_count=total_count, books=books_out)
