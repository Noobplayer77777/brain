import sqlite3
import contextlib
from config import DB_PATH

@contextlib.contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("INSERT OR IGNORE INTO schema_version (version) VALUES (1)")
        
        # Subjects lookup
        conn.execute("""
            CREATE TABLE IF NOT EXISTS subjects (
                name TEXT PRIMARY KEY
            )
        """)
        for sub in ["DBMS", "DMGT", "Compiler Design", "Cloud Architecture Design"]:
            conn.execute("INSERT OR IGNORE INTO subjects (name) VALUES (?)", (sub,))

        # Resources
        conn.execute("""
            CREATE TABLE IF NOT EXISTS resources (
                id TEXT PRIMARY KEY,
                path TEXT UNIQUE,
                filename TEXT,
                filetype TEXT,
                subject TEXT,
                sha256 TEXT,
                num_pages INTEGER,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT,
                error_msg TEXT,
                FOREIGN KEY(subject) REFERENCES subjects(name)
            )
        """)

        # Chunks
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chunk_id TEXT UNIQUE,
                resource_id TEXT,
                chunk_index INTEGER,
                text TEXT,
                page_start INTEGER,
                page_end INTEGER,
                slide_no INTEGER,
                token_count INTEGER,
                char_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(resource_id) REFERENCES resources(id) ON DELETE CASCADE
            )
        """)

        # FTS5
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                text,
                content='chunks',
                content_rowid='id'
            )
        """)

        # Syllabus Tree Tables
        conn.execute("""
            CREATE TABLE IF NOT EXISTS modules (
                id TEXT PRIMARY KEY,
                subject TEXT,
                code TEXT,
                title TEXT,
                order_index INTEGER,
                marks_weight INTEGER,
                description TEXT,
                FOREIGN KEY(subject) REFERENCES subjects(name)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS topics (
                id TEXT PRIMARY KEY,
                module_id TEXT,
                code TEXT,
                title TEXT,
                order_index INTEGER,
                description TEXT,
                learning_outcomes TEXT,
                FOREIGN KEY(module_id) REFERENCES modules(id) ON DELETE CASCADE
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS subtopics (
                id TEXT PRIMARY KEY,
                topic_id TEXT,
                title TEXT,
                order_index INTEGER,
                FOREIGN KEY(topic_id) REFERENCES topics(id) ON DELETE CASCADE
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS topic_resources (
                topic_id TEXT,
                resource_id TEXT,
                relevance REAL DEFAULT 0.5,
                PRIMARY KEY(topic_id, resource_id),
                FOREIGN KEY(topic_id) REFERENCES topics(id) ON DELETE CASCADE,
                FOREIGN KEY(resource_id) REFERENCES resources(id) ON DELETE CASCADE
            )
        """)

        # Concepts
        conn.execute("""
            CREATE TABLE IF NOT EXISTS concepts (
                id TEXT PRIMARY KEY,
                subject TEXT,
                name TEXT,
                canonical_name TEXT,
                type TEXT,
                definition TEXT,
                difficulty INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(subject) REFERENCES subjects(name)
            )
        """)

        # Concept Links (to Topics)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS concept_links (
                concept_id TEXT,
                topic_id TEXT,
                weight REAL DEFAULT 1.0,
                PRIMARY KEY(concept_id, topic_id),
                FOREIGN KEY(concept_id) REFERENCES concepts(id) ON DELETE CASCADE,
                FOREIGN KEY(topic_id) REFERENCES topics(id) ON DELETE CASCADE
            )
        """)

        # Concept Resources
        conn.execute("""
            CREATE TABLE IF NOT EXISTS concept_resources (
                concept_id TEXT,
                resource_id TEXT,
                chunk_id TEXT,
                relation TEXT,
                confidence REAL,
                PRIMARY KEY(concept_id, chunk_id),
                FOREIGN KEY(concept_id) REFERENCES concepts(id) ON DELETE CASCADE,
                FOREIGN KEY(resource_id) REFERENCES resources(id) ON DELETE CASCADE
            )
        """)

        # Prerequisites
        conn.execute("""
            CREATE TABLE IF NOT EXISTS prerequisites (
                concept_id TEXT,
                prereq_concept_id TEXT,
                source TEXT,
                confidence REAL,
                PRIMARY KEY(concept_id, prereq_concept_id),
                FOREIGN KEY(concept_id) REFERENCES concepts(id) ON DELETE CASCADE,
                FOREIGN KEY(prereq_concept_id) REFERENCES concepts(id) ON DELETE CASCADE
            )
        """)

        # Questions
        conn.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id TEXT PRIMARY KEY,
                subject TEXT,
                source_type TEXT,
                source_name TEXT,
                year INTEGER,
                exam_type TEXT,
                question_number TEXT,
                text TEXT,
                marks INTEGER,
                question_type TEXT,
                archetype TEXT,
                difficulty INTEGER,
                model_answer TEXT,
                rubric TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Question Concepts
        conn.execute("""
            CREATE TABLE IF NOT EXISTS question_concepts (
                question_id TEXT,
                concept_id TEXT,
                confidence REAL,
                PRIMARY KEY(question_id, concept_id),
                FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE,
                FOREIGN KEY(concept_id) REFERENCES concepts(id) ON DELETE CASCADE
            )
        """)

        # Question Topics
        conn.execute("""
            CREATE TABLE IF NOT EXISTS question_topics (
                question_id TEXT,
                topic_id TEXT,
                confidence REAL,
                PRIMARY KEY(question_id, topic_id),
                FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE,
                FOREIGN KEY(topic_id) REFERENCES topics(id) ON DELETE CASCADE
            )
        """)

        # Study Phase Tables
        conn.execute("""
            CREATE TABLE IF NOT EXISTS attempts (
                id TEXT PRIMARY KEY,
                question_id TEXT,
                user_answer TEXT,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                time_spent_sec INTEGER,
                score REAL,
                max_score REAL,
                graded_by TEXT,
                feedback TEXT,
                missing_points TEXT,
                FOREIGN KEY(question_id) REFERENCES questions(id)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS mistakes (
                id TEXT PRIMARY KEY,
                attempt_id TEXT,
                concept_id TEXT,
                error_type TEXT,
                note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(attempt_id) REFERENCES attempts(id),
                FOREIGN KEY(concept_id) REFERENCES concepts(id)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS mastery (
                concept_id TEXT PRIMARY KEY,
                score REAL DEFAULT 0.0,
                confidence REAL DEFAULT 0.0,
                attempts_count INTEGER DEFAULT 0,
                correct_count INTEGER DEFAULT 0,
                last_reviewed TIMESTAMP,
                next_review TIMESTAMP,
                interval_days REAL DEFAULT 0.0,
                ease REAL DEFAULT 2.5,
                FOREIGN KEY(concept_id) REFERENCES concepts(id)
            )
        """)

        # Review Logs
        conn.execute("""
            CREATE TABLE IF NOT EXISTS review_log (
                id TEXT PRIMARY KEY,
                concept_id TEXT,
                reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                quality INTEGER,
                mastery_before REAL,
                mastery_after REAL,
                FOREIGN KEY(concept_id) REFERENCES concepts(id)
            )
        """)

        # Phase 7: Sessions, Mocks, Settings
        conn.execute("""
            CREATE TABLE IF NOT EXISTS study_sessions (
                id TEXT PRIMARY KEY,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                task_type TEXT,
                concept_id TEXT,
                question_id TEXT,
                minutes INTEGER,
                notes TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS mock_exams (
                id TEXT PRIMARY KEY,
                subject TEXT,
                taken_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                duration_min INTEGER,
                total_score REAL,
                max_score REAL,
                report_json TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # Triggers for syncing FTS
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
                INSERT INTO chunks_fts(rowid, text) VALUES (new.id, new.text);
            END;
        """)
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
                INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES ('delete', old.id, old.text);
            END;
        """)
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
                INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES ('delete', old.id, old.text);
                INSERT INTO chunks_fts(rowid, text) VALUES (new.id, new.text);
            END;
        """)
