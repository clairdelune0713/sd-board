import psycopg2
import psycopg2.extras
from src.config import config

def inspect_db():
    db_url = config.DATABASE_URL.replace("?pgbouncer=true", "")
    with psycopg2.connect(db_url) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT * FROM cinedual_projects WHERE user_email = 'clairdelune0713@gmail.com' AND session_timestamp = '20260504-1254-A'")
            proj = cur.fetchone()
            if proj:
                print("Project found:", dict(proj))
            else:
                print("Project not found")
                
            cur.execute("SELECT * FROM scenes_content WHERE user_email = 'clairdelune0713@gmail.com' AND project_id = '20260504-1254-A' ORDER BY scene, panel LIMIT 10")
            panels = cur.fetchall()
            print("Panels found:", len(panels))
            for p in panels:
                print(dict(p))
                
if __name__ == '__main__':
    inspect_db()
