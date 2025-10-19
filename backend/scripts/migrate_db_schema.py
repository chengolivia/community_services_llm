import psycopg
import os

CONNECTION_STRING = os.getenv("DATABASE_URL")

def migrate_schema():
    conn = psycopg.connect(CONNECTION_STRING)
    cursor = conn.cursor()
    
    try:
        # Remove UNIQUE from service_user_name
        cursor.execute('ALTER TABLE profiles DROP CONSTRAINT IF EXISTS profiles_service_user_name_key')
        
        # Add UNIQUE to outreach_details.user_name (skip if exists)
        cursor.execute('''
            DO $$ 
            BEGIN
                ALTER TABLE outreach_details ADD CONSTRAINT outreach_details_user_name_key UNIQUE (user_name);
            EXCEPTION
                WHEN duplicate_table THEN NULL;
            END $$;
        ''')
        
        conn.commit()
        print("✅ Schema migration successful")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_schema()