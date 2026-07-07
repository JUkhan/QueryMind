import os
import re
import json


def seed_default_user():
    """Create an initial login user if the users table is empty.

    Runs on startup so a fresh deployment (e.g. a new Coolify volume with an
    empty database) has working credentials immediately. Configure via the
    SEED_USERNAME / SEED_EMAIL environment variables. Set SEED_DEFAULT_USER=0
    to disable seeding.
    """
    if os.getenv('SEED_DEFAULT_USER', '1') == '0':
        return

    from database import db
    from models.sample_model import User

    username = os.getenv('SEED_USERNAME', 'testuser')
    email = os.getenv('SEED_EMAIL', 'testuser@gmail.com')

    try:
        if db.session.query(User).count() > 0:
            return
        db.session.add(User(username=username, email=email))
        db.session.commit()
        print(f"Seeded initial user: {username} / {email}")
    except Exception as exc:  # pragma: no cover - best-effort seeding
        db.session.rollback()
        print(f"Skipped seeding default user: {exc}")


def _extract_insert_statements(sql_text, exclude_tables=()):
    """Return the INSERT statements from a .sql file, skipping DROP/CREATE.

    The sample file is MySQL-flavoured; its CREATE TABLE statements clash with
    the SQLAlchemy-managed tables, so only the dialect-neutral INSERTs are used.
    Inline `-- ...` comments are stripped (no `--` appears inside string
    literals in this file).
    """
    lines = []
    for line in sql_text.splitlines():
        if '--' in line:
            line = line[:line.index('--')]
        lines.append(line)

    statements = [s.strip() for s in '\n'.join(lines).split(';')]
    inserts = []
    for stmt in statements:
        if not stmt.upper().startswith('INSERT'):
            continue
        if any(t.lower() in stmt.lower() for t in exclude_tables):
            continue
        inserts.append(stmt)
    return inserts


def seed_sample_data():
    """Load the demo dataset from sample_data.sql on first boot.

    Populates customers/products/orders/order_items so the AI chatbot has data
    to query. Runs only when those tables are empty. The user_gen_core insert is
    skipped here because seed_default_user() owns login users. Disable with
    SEED_SAMPLE_DATA=0.
    """
    if os.getenv('SEED_SAMPLE_DATA', '1') == '0':
        return

    from database import db
    from models.sample_model import Customer

    sql_path = os.path.join(os.path.dirname(__file__), 'sample_data.sql')
    if not os.path.exists(sql_path):
        print("sample_data.sql not found; skipping sample data seeding")
        return

    try:
        if db.session.query(Customer).count() > 0:
            return
        with open(sql_path, 'r', encoding='utf-8') as handle:
            statements = _extract_insert_statements(
                handle.read(), exclude_tables=('user_gen_core',))
        with db.engine.begin() as conn:
            for stmt in statements:
                conn.exec_driver_sql(stmt)
        print(f"Seeded sample data ({len(statements)} insert statements)")
    except Exception as exc:  # pragma: no cover - best-effort seeding
        db.session.rollback()
        print(f"Skipped seeding sample data: {exc}")

def extract_json(text):
    """
    Extract JSON with more detailed error reporting.
    
    Args:
        text (str): The input text containing JSON code blocks
        
    Returns:
        tuple: (success: bool, data: dict/list/None, error: str/None)
    """
    json_regex = r'```json\s*([\s\S]*?)\s*```'
    match = re.search(json_regex, text)
    
    if not match:
        return False, None, 'No JSON content found within ```json ``` delimiters.'
    
    if not match.group(1):
        return False, None, 'Empty JSON block found.'
    
    json_string = match.group(1).strip()
    
    try:
        json_data = json.loads(json_string)
        return True, json_data, None
    except json.JSONDecodeError as error:
        return False, None, f'Error parsing JSON: {error}'

def extract_sql(text):
    """
    Extract SQL with more detailed error reporting.
    
    Args:
        text (str): The input text containing JSON code blocks
        
    Returns:
        tuple: (success: bool, data: dict/list/None, error: str/None)
    """
    json_regex = r'```(?:sqlite|sql|postgresql)\s*([\s\S]*?)\s*```'
    match = re.search(json_regex, text)
    
    if not match:
        return False, text
    
    if not match.group(1):
        return False, text
    
    json_string = match.group(1).strip()
    
    
    return True, json_string
    
if __name__ == '__main__':
    arr=['Here is the sqlite query to find all system user:', '```sqlite\nSELECT * FROM user_gen_core\n```']
    if(isinstance(arr, list)):
        print("".join(arr))
        print(extract_sql("".join(arr)))
    print(extract_sql("""gdgdgdg
                      hjhkh
                      dgdgg: ```sql select *from user;```"""))