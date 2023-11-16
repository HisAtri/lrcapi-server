import pymysql
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def connect_to_database():
    db_conn = pymysql.connect(
        host='45.145.228.219',
        user='lrc',
        password='tCTWRiJm7MhSf6JB',
        database='lrc'
    )
    return db_conn


def check_database_structure(checking_conn):
    cursor = checking_conn.cursor()

    # 检查数据库是否为空
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()

    if not tables:
        # 数据库为空，创建表结构
        create_api_key_table = """
        CREATE TABLE api_key (
            id INT AUTO_INCREMENT PRIMARY KEY,
            song_name TEXT,
            singer_name TEXT,
            album_name TEXT,
            hash VARCHAR(255) UNIQUE,
            lyrics LONGTEXT
        )
        """
        cursor.execute(create_api_key_table)
        checking_conn.commit()

        logging.info("成功创建数据库表结构")
    else:
        logging.info("数据库已存在，跳过创建表结构")

    cursor.close()


if __name__ == "__main__":
    conn = connect_to_database()
    check_database_structure(conn)
