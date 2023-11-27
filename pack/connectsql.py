import pymysql
import logging
from pack.read_config import cfg

logger = logging.getLogger(__name__)


def connect_to_database():
    db_conn = pymysql.connect(
        host=cfg.MySQL.host,
        port=cfg.MySQL.port,
        user=cfg.MySQL.user,
        password=cfg.MySQL.password,
        database=cfg.MySQL.name
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

        create_album_cover_table = """
        CREATE TABLE api_img (
            id INT AUTO_INCREMENT PRIMARY KEY,
            music TEXT,
            artist TEXT,
            album TEXT,
            hash VARCHAR(255) UNIQUE,
            mu_id TEXT,
            mu_url TEXT,
            al_id TEXT,
            al_url TEXT,
            ar_id TEXT,
            ar_url TEXT
        )
        """

        cursor.execute(create_api_key_table)
        cursor.execute(create_album_cover_table)
        checking_conn.commit()

        logging.info("成功创建数据库表结构")
    else:
        logging.info("数据库已存在，跳过创建表结构")

    cursor.close()


if __name__ == "__main__":
    conn = connect_to_database()
