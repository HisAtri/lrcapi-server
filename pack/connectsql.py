import mysql.connector


def connect_to_database():
    conn = mysql.connector.connect(
        host='45.145.228.219',
        user='lylrc',
        password='xTEYwMtrK4GR5pCe',
        database='lylrc'
    )
    return conn


def check_database_structure(conn):
    cursor = conn.cursor()

    # 检查数据库是否为空
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()

    if not tables:
        # 数据库为空，创建表结构
        create_api_key_table = """
        CREATE TABLE api_key (
            song_name TEXT,
            singer_name TEXT,
            album_name TEXT,
            hash VARCHAR(255) UNIQUE,
            lyrics LONGTEXT
        )
        """

        create_search_table = """
        CREATE TABLE search (
            song_name TEXT,
            singer_name TEXT,
            album_name TEXT,
            hash TEXT
        )
        """

        cursor.execute(create_api_key_table)
        cursor.execute(create_search_table)
        conn.commit()

        print("成功创建数据库表结构。")
    else:
        print("数据库已存在，跳过创建表结构。")

    cursor.close()


if __name__ == "__main__":
    conn = connect_to_database()
    check_database_structure(conn)
