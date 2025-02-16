from pydantic import BaseModel
from typing import List, Optional


class FormatOut(BaseModel):
    mime_type: str
    url: str


class AuthorOut(BaseModel):
    name: str
    birth_year: Optional[int] = None
    death_year: Optional[int] = None


class BookOut(BaseModel):
    title: str
    authors: List[AuthorOut] = []
    languages: List[str] = []
    subjects: List[str] = []
    bookshelves: List[str] = []
    formats: List[FormatOut] = []


class BooksResponse(BaseModel):
    total_count: int
    books: List[BookOut]
