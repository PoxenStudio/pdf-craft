#!/bin/python

import sys
from pdf_craft import transform_epub, BookMeta

if len(sys.argv) < 3:
    print("Invalid parameters")
    sys.exit(0)

print(f"Convert {sys.argv[1]} to {sys.argv[2]}")

transform_epub(
    pdf_path=sys.argv[1],
    epub_path=sys.argv[2],
    book_meta=BookMeta(
        title="如何提高文言文的阅读水平",
        authors=["佚名"],
    ),
)
