import os
import fitz

os.makedirs("data/raw/pyq", exist_ok=True)

# Paper 1: DBMS 2023 EndSem
doc = fitz.open()
page = doc.new_page()
page.insert_text((50, 50), "DBMS End Semester Exam 2023")
page.insert_text((50, 80), "1. Define First Normal Form (1NF). (2 marks)")
page.insert_text((50, 100), "2. Explain BCNF with an example. (5 marks)")
doc.save("data/raw/pyq/dbms_2023_endsem.pdf")

# Paper 2: DBMS 2022 EndSem
doc = fitz.open()
page = doc.new_page()
page.insert_text((50, 50), "DBMS End Semester Exam 2022")
page.insert_text((50, 80), "1. What is First Normal Form? (2 marks)")
page.insert_text((50, 100), "2. Draw an ER diagram for a hospital management system. (10 marks)")
doc.save("data/raw/pyq/dbms_2022_endsem.pdf")

# Paper 3: DMGT 2023 CAT
doc = fitz.open()
page = doc.new_page()
page.insert_text((50, 50), "DMGT CAT Exam 2023")
page.insert_text((50, 80), "1. State Euler's Formula for planar graphs. (2 marks)")
page.insert_text((50, 100), "2. Define a complete bipartite graph. (3 marks)")
doc.save("data/raw/pyq/dmgt_2023_cat.pdf")

print("Created 3 PYQ test PDFs.")
